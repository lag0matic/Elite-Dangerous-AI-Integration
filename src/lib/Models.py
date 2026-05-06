from abc import ABC, abstractmethod
from typing import Any, List, Optional, Generator, Iterable
import io
import base64
import hashlib
import json
import site
import speech_recognition as sr
import soundfile as sf
import numpy as np
import sys
import threading
import traceback
from time import sleep, time
from uuid import uuid4
import edge_tts
import miniaudio
from openai.types.audio.speech_create_params import SpeechCreateParams
from openai import OpenAI, APIStatusError
from openai.types.chat import ChatCompletion, ChatCompletionMessageFunctionToolCall, ChatCompletionMessageToolCall
from openai.types import CreateEmbeddingResponse
from .Logger import log, ModelUsageStats

class LLMError(Exception):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error

class LLMModel(ABC):
    model_name: str
    provider_name: str | None

    def __init__(self, model_name: str, provider_name: str | None = None):
        self.model_name = model_name
        self.provider_name = provider_name

    @abstractmethod
    def generate(self, messages: List[dict], tools: Optional[List[dict]] = None, tool_choice: Optional[Any] = None) -> tuple[str | None, List[Any] | None, ModelUsageStats]:
        pass

class EmbeddingModel(ABC):
    model_name: str

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def create_embedding(self, input_text: str) -> tuple[str, List[float]]:
        pass

def _model_dump_compatible(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value

def _get_reasoning_tokens(usage: Any) -> int | None:
    for details_name in ("output_tokens_details", "completion_tokens_details"):
        details = getattr(usage, details_name, None)
        if details is None:
            continue

        reasoning_tokens = getattr(details, "reasoning_tokens", None)
        if reasoning_tokens is not None:
            return int(reasoning_tokens)

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    if (
        prompt_tokens is not None
        and completion_tokens is not None
        and total_tokens is not None
    ):
        fallback_reasoning_tokens = (
            int(total_tokens) - int(prompt_tokens) - int(completion_tokens)
        )
        if fallback_reasoning_tokens >= 0:
            return fallback_reasoning_tokens

    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if (
        input_tokens is not None
        and output_tokens is not None
        and total_tokens is not None
    ):
        fallback_reasoning_tokens = (
            int(total_tokens) - int(input_tokens) - int(output_tokens)
        )
        if fallback_reasoning_tokens >= 0:
            return fallback_reasoning_tokens

    return None

class OpenAILLMModel(LLMModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, temperature: float, reasoning_effort: Optional[str] = None, extra_body: Optional[dict] = None, extra_headers: Optional[dict] = None, provider_name: str | None = None):
        super().__init__(model_name, provider_name=provider_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.base_url = base_url
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body or {}
        self.extra_headers = extra_headers or {}

    def generate(self, messages: List[dict], tools: Optional[List[dict]] = None, tool_choice: Optional[Any] = None) -> tuple[str | None, List[Any] | None, ModelUsageStats]:
        kwargs = {}
        # Special handling for specific models or providers if needed
        if self.model_name in ['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-5.1']:
            kwargs["verbosity"] = "low"
                    
        if 'google' in self.base_url or 'google' in self.model_name or 'gemini' in self.model_name:
            for m in messages:
                if 'tool_calls' in m and m.get('tool_calls', None):
                    calls = m.get('tool_calls', [])
                    if calls:
                        for i in range(len(calls)):
                            if not isinstance(calls[i], dict):
                                if hasattr(calls[i], 'model_dump'):
                                    calls[i] = calls[i].model_dump()
                                elif hasattr(calls[i], 'dict'):
                                    calls[i] = calls[i].dict()
                            
                            if isinstance(calls[i], dict):
                                thought_sig = calls[i].get('extra_content',{}).get('google', {}).get('thought_signature')
                                if not thought_sig:
                                    calls[i]['extra_content'] = {"google": {
                                        "thought_signature": "skip_thought_signature_validator"
                                    }}
        
        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            **self.extra_body,
            **kwargs
        }
        if tools:
            params["tools"] = tools
            if tool_choice:
                params["tool_choice"] = tool_choice
        
        if self.reasoning_effort and self.reasoning_effort not in ["disabled", "default", None, ""]:
             params["reasoning_effort"] = self.reasoning_effort

        if self.extra_body:
            params["extra_body"] = self.extra_body
            
        if self.extra_headers:
            params["extra_headers"] = self.extra_headers

        try:
            completion = self.client.chat.completions.create(**params) # pyright: ignore[reportCallIssue]
        except APIStatusError as e:
            log("debug", "LLM error request:", e.request.method, e.request.url, e.request.headers, e.request.read().decode('utf-8', errors='replace'))
            log("debug", "LLM error response:", e.response.status_code, e.response.headers, e.response.read().decode('utf-8', errors='replace'))
            
            try:
                error: dict = e.body[0] if hasattr(e, 'body') and e.body and isinstance(e.body, list) else e.body # pyright: ignore[reportAssignmentType]
                message = error.get('error', {}).get('message', e.body if e.body else 'Unknown error')
            except:
                message = e.message
            
            raise LLMError(f'LLM {e.response.reason_phrase}: {message}', e)
        except Exception as e:
            raise LLMError(f'LLM Error: {str(e)}', e)

        if not isinstance(completion, ChatCompletion) or hasattr(completion, 'error'):
            log("debug", "LLM completion error:", completion)
            raise LLMError("LLM error: No valid completion received")
        
        if not completion.choices:
            log("debug", "LLM completion has no choices:", completion)
            return (None, None, ModelUsageStats(provider=self.provider_name, model_name=self.model_name)) # Treated as "..."

        if not hasattr(completion.choices[0], 'message') or not completion.choices[0].message:
            log("debug", "LLM completion choice has no message:", completion)
            return (None, None, ModelUsageStats(provider=self.provider_name, model_name=self.model_name)) # Treated as "..."
        
        usage_metadata = ModelUsageStats(provider=self.provider_name, model_name=self.model_name)
        if hasattr(completion, 'usage') and completion.usage:
            log("debug", f'LLM completion usage', completion.usage)
            usage_metadata.input_tokens = completion.usage.prompt_tokens
            usage_metadata.output_tokens = completion.usage.completion_tokens
            usage_metadata.total_tokens = completion.usage.total_tokens
            if hasattr(completion.usage, 'prompt_tokens_details') and completion.usage.prompt_tokens_details:
                usage_metadata.cached_tokens = getattr(completion.usage.prompt_tokens_details, 'cached_tokens', 0)
            usage_metadata.reasoning_tokens = _get_reasoning_tokens(completion.usage)
        
        response_text = None
        if hasattr(completion.choices[0].message, 'content'):
            response_text = completion.choices[0].message.content
            if completion.choices[0].message.content is None or completion.choices[0].message.content == "":
                log("debug", "LLM completion no content:", completion)
                response_text = None
        else:
            log("debug", f'LLM completion without text')
            response_text = None

        response_actions = None
        if hasattr(completion.choices[0].message, 'tool_calls'):
            response_actions = completion.choices[0].message.tool_calls

        if response_text is None and response_actions is None:
             return (None, None, usage_metadata)

        return (response_text, response_actions, usage_metadata)

    def list_models(self) -> List[str]:
        try:
            models = self.client.models.list()
            return [model.id for model in models]
        except Exception as e:
            raise e

class OpenAIResponsesLLMModel(LLMModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, temperature: float, reasoning_effort: Optional[str] = None, extra_body: Optional[dict] = None, extra_headers: Optional[dict] = None, provider_name: str | None = None):
        super().__init__(model_name, provider_name=provider_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.base_url = base_url
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body or {}
        self.extra_headers = extra_headers or {}

    def _has_message_content(self, content: Any) -> bool:
        if content is None:
            return False
        if isinstance(content, str):
            return content != ""
        if isinstance(content, list):
            return len(content) > 0
        return True

    def _stringify_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content)
        except TypeError:
            return str(content)

    def _convert_content_part(self, part: Any) -> dict[str, Any]:
        part = _model_dump_compatible(part)
        if not isinstance(part, dict):
            return {"type": "input_text", "text": str(part)}

        part_type = part.get("type")
        if part_type in {"input_text", "input_image", "input_audio", "input_file"}:
            return part

        if part_type == "text":
            return {
                "type": "input_text",
                "text": str(part.get("text", "")),
            }

        if part_type == "image_url":
            image_value = part.get("image_url")
            image_url: str | None = None
            detail = "auto"
            if isinstance(image_value, dict):
                image_url = image_value.get("url")
                detail = image_value.get("detail", detail)
            elif isinstance(image_value, str):
                image_url = image_value

            if image_url:
                return {
                    "type": "input_image",
                    "image_url": image_url,
                    "detail": detail,
                }

        if part_type == "input_audio":
            return part

        return {
            "type": "input_text",
            "text": self._stringify_content(part),
        }

    def _convert_message_content(self, content: Any) -> str | list[dict[str, Any]]:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return [self._convert_content_part(part) for part in content]
        if isinstance(content, dict):
            return [self._convert_content_part(content)]
        return self._stringify_content(content)

    def _convert_assistant_tool_calls(self, tool_calls: Any) -> list[dict[str, Any]]:
        converted_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls or []:
            tool_call = _model_dump_compatible(tool_call)
            if not isinstance(tool_call, dict):
                continue

            function_data = _model_dump_compatible(tool_call.get("function"))
            if not isinstance(function_data, dict):
                continue

            raw_call_id = tool_call.get("call_id") or tool_call.get("id") or f"call_{uuid4().hex}"
            raw_response_item_id = tool_call.get("id")
            converted_call = {
                "type": "function_call",
                "call_id": str(raw_call_id),
                "name": str(function_data.get("name", "")),
                "arguments": str(function_data.get("arguments") or "{}"),
            }

            # Chat-completions tool calls only provide a call ID like "call_xxx".
            # Responses API item IDs are separate and typically start with "fc_".
            if isinstance(raw_response_item_id, str) and raw_response_item_id.startswith("fc"):
                converted_call["id"] = raw_response_item_id

            converted_calls.append(converted_call)
        return converted_calls

    def _convert_tool_output_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        call_id = message.get("tool_call_id") or message.get("call_id")
        if not call_id:
            return None

        return {
            "type": "function_call_output",
            "call_id": str(call_id),
            "output": self._stringify_content(message.get("content", "")),
        }

    def _convert_messages(self, messages: List[dict]) -> list[dict[str, Any]]:
        converted_messages: list[dict[str, Any]] = []

        for raw_message in messages:
            message = _model_dump_compatible(raw_message)
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")
            tool_calls = message.get("tool_calls")

            if role == "tool":
                tool_output = self._convert_tool_output_message(message)
                if tool_output:
                    converted_messages.append(tool_output)
                continue

            if role in {"system", "developer", "user", "assistant"} and self._has_message_content(content):
                converted_messages.append({
                    "type": "message",
                    "role": role,
                    "content": self._convert_message_content(content),
                })

            if role == "assistant" and tool_calls:
                converted_messages.extend(self._convert_assistant_tool_calls(tool_calls))

        return converted_messages

    def _convert_tools(self, tools: List[dict]) -> list[dict[str, Any]]:
        converted_tools: list[dict[str, Any]] = []

        for raw_tool in tools:
            tool = _model_dump_compatible(raw_tool)
            if not isinstance(tool, dict):
                continue

            if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
                function_data = _model_dump_compatible(tool["function"])
                converted_tool = {
                    "type": "function",
                    "name": function_data.get("name"),
                    "description": function_data.get("description"),
                    "parameters": function_data.get("parameters"),
                }
                strict = function_data.get("strict")
                if strict is not None:
                    converted_tool["strict"] = strict
                converted_tools.append({k: v for k, v in converted_tool.items() if v is not None})
                continue

            converted_tools.append(tool)

        return converted_tools

    def _convert_tool_choice(self, tool_choice: Any) -> Any:
        tool_choice = _model_dump_compatible(tool_choice)
        if isinstance(tool_choice, str):
            return tool_choice

        if isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
            function_data = _model_dump_compatible(tool_choice.get("function"))
            if isinstance(function_data, dict):
                return {
                    "type": "function",
                    "name": function_data.get("name"),
                }

        return tool_choice

    def _extract_tool_calls(self, response: Any) -> list[ChatCompletionMessageFunctionToolCall] | None:
        tool_calls: list[ChatCompletionMessageFunctionToolCall] = []

        for output_item in getattr(response, "output", []) or []:
            item = _model_dump_compatible(output_item)
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue

            call_id = str(item.get("call_id") or item.get("id") or f"call_{uuid4().hex}")
            tool_calls.append(ChatCompletionMessageFunctionToolCall.model_validate({
                "type": "function",
                "id": call_id,
                "function": {
                    "name": str(item.get("name", "")),
                    "arguments": str(item.get("arguments") or "{}"),
                },
            }))

        return tool_calls or None

    def generate(self, messages: List[dict], tools: Optional[List[dict]] = None, tool_choice: Optional[Any] = None) -> tuple[str | None, List[Any] | None, ModelUsageStats]:
        params: dict[str, Any] = {
            "model": self.model_name,
            "input": self._convert_messages(messages),
            "temperature": self.temperature,
        }

        if self.model_name in ['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-5.4-mini', 'gpt-5.4-nano', 'gpt-5.4', 'gpt-5.1']:
            params["text"] = {"verbosity": "low"}

        if tools:
            params["tools"] = self._convert_tools(tools)
            if tool_choice:
                params["tool_choice"] = self._convert_tool_choice(tool_choice)

        if self.reasoning_effort and self.reasoning_effort not in ["disabled", "default", "none", None, ""]:
            params["reasoning"] = {"effort": self.reasoning_effort}

        if self.extra_body:
            params["extra_body"] = self.extra_body

        if self.extra_headers:
            params["extra_headers"] = self.extra_headers

        try:
            response = self.client.responses.create(**params)
        except APIStatusError as e:
            log("debug", "LLM error request:", e.request.method, e.request.url, e.request.headers, e.request.read().decode('utf-8', errors='replace'))
            log("debug", "LLM error response:", e.response.status_code, e.response.headers, e.response.read().decode('utf-8', errors='replace'))

            try:
                error: dict = e.body[0] if hasattr(e, 'body') and e.body and isinstance(e.body, list) else e.body # pyright: ignore[reportAssignmentType]
                message = error.get('error', {}).get('message', e.body if e.body else 'Unknown error')
            except:
                message = e.message

            raise LLMError(f'LLM {e.response.reason_phrase}: {message}', e)
        except Exception as e:
            raise LLMError(f'LLM Error: {str(e)}', e)

        if getattr(response, "error", None):
            log("debug", "LLM response error:", response)
            raise LLMError("LLM error: No valid response received")

        usage_metadata = ModelUsageStats(provider=self.provider_name, model_name=self.model_name)
        if hasattr(response, 'usage') and response.usage:
            log("debug", "LLM response usage", response.usage)
            usage_metadata.input_tokens = getattr(response.usage, "input_tokens", 0)
            usage_metadata.output_tokens = getattr(response.usage, "output_tokens", 0)
            usage_metadata.total_tokens = getattr(response.usage, "total_tokens", 0)
            if hasattr(response.usage, "input_tokens_details") and response.usage.input_tokens_details:
                usage_metadata.cached_tokens = getattr(response.usage.input_tokens_details, "cached_tokens", 0)
            usage_metadata.reasoning_tokens = _get_reasoning_tokens(response.usage)

        response_text = getattr(response, "output_text", None) or None
        response_actions = self._extract_tool_calls(response)

        if response_text is None and response_actions is None:
            return (None, None, usage_metadata)

        return (response_text, response_actions, usage_metadata)

    def list_models(self) -> List[str]:
        try:
            models = self.client.models.list()
            return [model.id for model in models]
        except Exception as e:
            raise e

class GeminiCachedLLMModel(LLMModel):
    """Gemini-native LLM transport with explicit context caching.

    The rest of the app still speaks the OpenAI-compatible LLMModel interface.
    This class keeps the static foundation (system instruction + tools) in a
    Gemini cached content object and sends changing status/history/events as
    normal request contents.
    """

    CACHE_SCHEMA_VERSION = "gemini-explicit-cache-v1"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        temperature: float,
        reasoning_effort: Optional[str] = None,
        extra_body: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
        provider_name: str | None = None,
        fallback_model: LLMModel | None = None,
    ):
        super().__init__(model_name, provider_name=provider_name)
        self.base_url = base_url
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body or {}
        self.extra_headers = extra_headers or {}
        self.cache_ttl = str(self.extra_body.get("gemini_cache_ttl", "10800s"))
        self.cache_disabled_reason: str | None = None
        self.cache_disabled_keys: set[str] = set()
        self.fallback_model = fallback_model or OpenAILLMModel(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            extra_body=extra_body,
            extra_headers=extra_headers,
            provider_name=provider_name,
        )
        self.client: Any | None = None
        self.types: Any | None = None
        self.cache_store: Any | None = None

        try:
            genai, types = self._import_genai_sdk()
            from .Database import KeyValueStore

            self.client = genai.Client(api_key=api_key)
            self.types = types
            self.cache_store = KeyValueStore("gemini_context_cache")
        except Exception as e:
            log("warn", "Gemini native cache unavailable, using OpenAI-compatible fallback:", e)

    def _import_genai_sdk(self) -> tuple[Any, Any]:
        """Import google-genai without plugin dependency folders shadowing google-auth."""
        original_path = list(sys.path)
        try:
            site_package_paths = [
                str(path)
                for path in (*site.getsitepackages(), site.getusersitepackages())
                if path
            ]
        except Exception:
            site_package_paths = []

        def is_site_package(path: str) -> bool:
            try:
                normalized = path.lower()
                return any(normalized == site_path.lower() for site_path in site_package_paths)
            except Exception:
                return False

        try:
            sys.path[:] = (
                [path for path in original_path if is_site_package(path)]
                + [path for path in original_path if not is_site_package(path)]
            )
            for module_name in list(sys.modules):
                if module_name == "google.genai" or module_name.startswith("google.genai."):
                    sys.modules.pop(module_name, None)
                elif module_name == "google.auth" or module_name.startswith("google.auth."):
                    sys.modules.pop(module_name, None)

            from google import genai  # pyright: ignore[reportMissingImports]
            from google.genai import types  # pyright: ignore[reportMissingImports]
            import google.auth.transport._http_client  # pyright: ignore[reportMissingImports] # noqa: F401

            return genai, types
        finally:
            sys.path[:] = original_path

    def _fallback_generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[Any] = None,
    ) -> tuple[str | None, List[Any] | None, ModelUsageStats]:
        return self.fallback_model.generate(messages=messages, tools=tools, tool_choice=tool_choice)

    def _json_hash(self, value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _split_static_system(self, messages: List[dict]) -> tuple[str | None, List[dict]]:
        if not messages:
            return None, []

        first = _model_dump_compatible(messages[0])
        if isinstance(first, dict) and first.get("role") == "system":
            content = first.get("content")
            if isinstance(content, str):
                return content, messages[1:]
            if content is not None:
                return self._stringify_content(content), messages[1:]

        return None, messages

    def _stringify_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except TypeError:
            return str(content)

    def _convert_schema_for_gemini(self, schema: Any) -> Any:
        schema = _model_dump_compatible(schema)
        if isinstance(schema, dict):
            converted: dict[str, Any] = {}
            for key, value in schema.items():
                if key in {"default", "example", "examples", "additionalProperties", "additional_properties"}:
                    continue
                converted[key] = self._convert_schema_for_gemini(value)
            return converted
        if isinstance(schema, list):
            return [self._convert_schema_for_gemini(item) for item in schema]
        return schema

    def _convert_tools_for_gemini(self, tools: Optional[List[dict]]) -> list[Any]:
        if not tools or not self.types:
            return []

        function_declarations: list[Any] = []
        for raw_tool in tools:
            tool = _model_dump_compatible(raw_tool)
            if not isinstance(tool, dict):
                continue
            if tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
                continue

            function_data = _model_dump_compatible(tool["function"])
            if not isinstance(function_data, dict):
                continue

            declaration = {
                "name": function_data.get("name"),
                "description": function_data.get("description", ""),
                "parameters": self._convert_schema_for_gemini(function_data.get("parameters", {"type": "object", "properties": {}})),
            }
            declaration = {k: v for k, v in declaration.items() if v is not None}
            function_declarations.append(declaration)

        if not function_declarations:
            return []

        return [self.types.Tool(function_declarations=function_declarations)]

    def _make_text_part(self, text: str) -> Any:
        if self.types:
            return self.types.Part(text=text)
        return {"text": text}

    def _decode_thought_signature(self, signature: Any) -> bytes | None:
        if signature is None:
            return None
        if isinstance(signature, bytes):
            return signature
        if isinstance(signature, str) and signature:
            try:
                return base64.b64decode(signature)
            except Exception:
                return signature.encode("utf-8")
        return None

    def _encode_thought_signature(self, signature: Any) -> str | None:
        if signature is None:
            return None
        if isinstance(signature, bytes):
            return base64.b64encode(signature).decode("ascii")
        if isinstance(signature, str) and signature:
            return signature
        return None

    def _make_function_call_part(self, name: str, args: dict[str, Any], thought_signature: Any = None) -> Any:
        if self.types:
            return self.types.Part(
                function_call=self.types.FunctionCall(name=name, args=args),
                thought_signature=self._decode_thought_signature(thought_signature),
            )
        part = {"function_call": {"name": name, "args": args}}
        if thought_signature:
            part["thought_signature"] = thought_signature
        return part

    def _make_function_response_part(self, name: str, response: dict[str, Any]) -> Any:
        if self.types:
            return self.types.Part(function_response=self.types.FunctionResponse(name=name, response=response))
        return {"function_response": {"name": name, "response": response}}

    def _make_content(self, role: str, parts: list[Any]) -> Any:
        gemini_role = "model" if role == "assistant" else "user"
        if self.types:
            return self.types.Content(role=gemini_role, parts=parts)
        return {"role": gemini_role, "parts": parts}

    def _convert_content_parts(self, content: Any) -> list[Any]:
        if content is None:
            return []
        if isinstance(content, str):
            return [self._make_text_part(content)] if content else []
        if isinstance(content, list):
            parts: list[Any] = []
            for item in content:
                item = _model_dump_compatible(item)
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type in {"text", "input_text"}:
                        text = str(item.get("text", ""))
                        if text:
                            parts.append(self._make_text_part(text))
                        continue
                    if item_type in {"image_url", "input_image"}:
                        # Multimodal Gemini-native conversion can be added later.
                        parts.append(self._make_text_part(self._stringify_content(item)))
                        continue
                parts.append(self._make_text_part(self._stringify_content(item)))
            return parts
        return [self._make_text_part(self._stringify_content(content))]

    def _convert_messages_for_gemini(self, messages: List[dict]) -> list[Any]:
        contents: list[Any] = []

        for raw_message in messages:
            message = _model_dump_compatible(raw_message)
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            if role == "system":
                # Any non-leading system message is treated as user-visible context.
                parts = self._convert_content_parts(message.get("content"))
                if parts:
                    contents.append(self._make_content("user", parts))
                continue

            if role == "tool":
                name = str(message.get("name") or "tool_result")
                response = {
                    "content": self._stringify_content(message.get("content", "")),
                }
                contents.append(self._make_content("user", [self._make_function_response_part(name, response)]))
                continue

            if role not in {"user", "assistant"}:
                continue

            parts = self._convert_content_parts(message.get("content"))
            if role == "assistant":
                for raw_tool_call in message.get("tool_calls") or []:
                    tool_call = _model_dump_compatible(raw_tool_call)
                    if not isinstance(tool_call, dict):
                        continue
                    function_data = _model_dump_compatible(tool_call.get("function"))
                    if not isinstance(function_data, dict):
                        continue
                    name = str(function_data.get("name", ""))
                    try:
                        args = json.loads(function_data.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    if name:
                        thought_signature = (
                            tool_call.get("extra_content", {})
                            .get("google", {})
                            .get("thought_signature")
                        )
                        parts.append(self._make_function_call_part(
                            name,
                            args if isinstance(args, dict) else {},
                            thought_signature=thought_signature,
                        ))

            if parts:
                contents.append(self._make_content(role, parts))

        return contents

    def _build_cache_key(self, system_instruction: str | None, tools: list[Any]) -> tuple[str, dict[str, Any]]:
        tool_payload: list[Any] = []
        for tool in tools:
            if hasattr(tool, "to_json_dict"):
                tool_payload.append(tool.to_json_dict())
            elif hasattr(tool, "model_dump"):
                tool_payload.append(tool.model_dump())
            else:
                tool_payload.append(_model_dump_compatible(tool))

        static_payload = {
            "schema": self.CACHE_SCHEMA_VERSION,
            "model": self.model_name,
            "system_instruction": system_instruction or "",
            "tools": tool_payload,
        }
        return self._json_hash(static_payload), static_payload

    def _cache_ttl_seconds(self) -> int:
        ttl = self.cache_ttl.strip().lower()
        try:
            if ttl.endswith("s"):
                return int(float(ttl[:-1]))
            if ttl.endswith("m"):
                return int(float(ttl[:-1]) * 60)
            if ttl.endswith("h"):
                return int(float(ttl[:-1]) * 3600)
            return int(float(ttl))
        except Exception:
            return 10800

    def _cache_refresh_threshold_seconds(self) -> int:
        return min(3600, max(300, self._cache_ttl_seconds() // 3))

    def _supports_explicit_cache(self) -> bool:
        model_name = self.model_name.lower()
        return "gemini" in model_name

    def _cache_expire_timestamp(self, cache: Any) -> float | None:
        expire_time = getattr(cache, "expire_time", None)
        if expire_time is None:
            return None
        try:
            return float(expire_time.timestamp())
        except Exception:
            return None

    def _update_cache_store_entry(self, store_key: str, cached: dict[str, Any], expires_at: float) -> None:
        if not self.cache_store:
            return
        updated = {
            **cached,
            "model": self.model_name,
            "ttl": self.cache_ttl,
            "expires_at": expires_at,
        }
        self.cache_store.set(store_key, updated)

    def _refresh_cached_content_ttl(
        self,
        store_key: str,
        cached: dict[str, Any],
        cache_hash: str,
    ) -> None:
        if not self.client or not self.types:
            return
        cache_name = str(cached["name"])
        try:
            refreshed = self.client.caches.update(
                name=cache_name,
                config=self.types.UpdateCachedContentConfig(ttl=self.cache_ttl),
            )
        except Exception as e:
            log("warn", "Gemini explicit context cache TTL refresh failed", {
                "model": self.model_name,
                "cache": cache_name,
                "hash": cache_hash[:16],
                "error": str(e),
            })
            return

        expires_at = self._cache_expire_timestamp(refreshed)
        if expires_at is None:
            expires_at = time() + max(60, self._cache_ttl_seconds() - 60)
        self._update_cache_store_entry(store_key, cached, expires_at)
        log("debug", "Gemini explicit context cache TTL refreshed", {
            "model": self.model_name,
            "cache": cache_name,
            "hash": cache_hash[:16],
        })

    def _validated_cached_content_name(
        self,
        store_key: str,
        cached: dict[str, Any],
        cache_hash: str,
    ) -> str | None:
        if not self.client or not self.cache_store:
            return None
        cache_name = str(cached["name"])
        try:
            remote_cache = self.client.caches.get(name=cache_name)
        except Exception as e:
            self.cache_store.delete(store_key)
            log("info", "Gemini explicit context cache stale, removing local entry", {
                "model": self.model_name,
                "cache": cache_name,
                "hash": cache_hash[:16],
                "error": str(e),
            })
            return None

        expires_at = self._cache_expire_timestamp(remote_cache)
        if expires_at is not None and expires_at <= time():
            self.cache_store.delete(store_key)
            log("info", "Gemini explicit context cache expired, removing local entry", {
                "model": self.model_name,
                "cache": cache_name,
                "hash": cache_hash[:16],
            })
            return None

        if expires_at is not None:
            self._update_cache_store_entry(store_key, cached, expires_at)
            if expires_at - time() <= self._cache_refresh_threshold_seconds():
                self._refresh_cached_content_ttl(store_key, cached, cache_hash)

        log("debug", "Gemini explicit context cache hit", {
            "model": self.model_name,
            "cache": cache_name,
            "hash": cache_hash[:16],
        })
        return cache_name

    def _get_cached_content_name(self, system_instruction: str | None, tools: list[Any]) -> str | None:
        if not self.client or not self.types or not self.cache_store:
            return None
        if not self._supports_explicit_cache():
            return None
        if not system_instruction and not tools:
            return None

        cache_hash, _ = self._build_cache_key(system_instruction, tools)
        store_key = f"{self.model_name}:{cache_hash}"
        if store_key in self.cache_disabled_keys:
            return None

        cached = self.cache_store.get(store_key)
        if isinstance(cached, dict) and cached.get("name"):
            cache_name = self._validated_cached_content_name(store_key, cached, cache_hash)
            if cache_name:
                return cache_name

        config_kwargs: dict[str, Any] = {
            "display_name": f"covas-{cache_hash[:16]}",
            "ttl": self.cache_ttl,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = tools

        try:
            cache = self.client.caches.create(
                model=self.model_name,
                config=self.types.CreateCachedContentConfig(**config_kwargs),
            )
        except Exception as e:
            self.cache_disabled_reason = str(e)
            self.cache_disabled_keys.add(store_key)
            log("warn", "Gemini explicit context cache disabled for model:", self.model_name, e)
            return None

        cache_name = str(getattr(cache, "name", ""))
        if cache_name:
            self.cache_store.set(store_key, {
                "name": cache_name,
                "hash": cache_hash,
                "model": self.model_name,
                "ttl": self.cache_ttl,
                "expires_at": time() + max(60, self._cache_ttl_seconds() - 60),
            })
            log("info", "Gemini explicit context cache created", {
                "model": self.model_name,
                "cache": cache_name,
                "hash": cache_hash[:16],
            })
            return cache_name
        return None

    def _extract_usage(self, response: Any) -> ModelUsageStats:
        usage = getattr(response, "usage_metadata", None)
        stats = ModelUsageStats(provider=self.provider_name, model_name=self.model_name)
        if not usage:
            return stats

        stats.input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        stats.output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        stats.total_tokens = int(getattr(usage, "total_token_count", 0) or 0)
        stats.cached_tokens = int(getattr(usage, "cached_content_token_count", 0) or 0)

        thoughts = getattr(usage, "thoughts_token_count", None)
        if thoughts is not None:
            stats.reasoning_tokens = int(thoughts)
        return stats

    def _extract_tool_calls(self, response: Any) -> list[ChatCompletionMessageFunctionToolCall] | None:
        raw_function_calls: list[tuple[Any, str | None]] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                function_call = getattr(part, "function_call", None)
                if function_call:
                    raw_function_calls.append((
                        function_call,
                        self._encode_thought_signature(getattr(part, "thought_signature", None)),
                    ))

        if not raw_function_calls:
            raw_function_calls = [
                (function_call, None)
                for function_call in list(getattr(response, "function_calls", None) or [])
            ]

        tool_calls: list[ChatCompletionMessageFunctionToolCall] = []
        for function_call, thought_signature in raw_function_calls:
            name = str(getattr(function_call, "name", "") or "")
            args = getattr(function_call, "args", {}) or {}
            if hasattr(args, "to_json_dict"):
                args = args.to_json_dict()
            elif hasattr(args, "model_dump"):
                args = args.model_dump()
            if not isinstance(args, dict):
                args = {}
            if not name:
                continue

            tool_calls.append(ChatCompletionMessageFunctionToolCall.model_validate({
                "type": "function",
                "id": str(getattr(function_call, "id", None) or f"call_{uuid4().hex}"),
                "function": {
                    "name": name,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
                "extra_content": {
                    "google": {
                        "thought_signature": thought_signature,
                    },
                } if thought_signature else {},
            }))

        return tool_calls or None

    def _convert_tool_choice_for_gemini(self, tool_choice: Any) -> Any | None:
        if tool_choice is None:
            return None

        mode = None
        allowed_function_names = None

        if isinstance(tool_choice, str):
            choice = tool_choice.lower()
            if choice == "auto":
                mode = self.types.FunctionCallingConfigMode.AUTO
            elif choice == "none":
                mode = self.types.FunctionCallingConfigMode.NONE
            elif choice == "required":
                mode = self.types.FunctionCallingConfigMode.ANY
            else:
                raise ValueError(f"Unsupported Gemini tool_choice: {tool_choice}")
        elif isinstance(tool_choice, dict):
            function_name = (
                tool_choice.get("function", {}).get("name")
                if isinstance(tool_choice.get("function"), dict)
                else None
            )
            if tool_choice.get("type") == "function" and function_name:
                mode = self.types.FunctionCallingConfigMode.ANY
                allowed_function_names = [str(function_name)]
            else:
                raise ValueError(f"Unsupported Gemini tool_choice: {tool_choice}")
        else:
            raise ValueError(f"Unsupported Gemini tool_choice: {tool_choice}")

        function_config_kwargs: dict[str, Any] = {"mode": mode}
        if allowed_function_names:
            function_config_kwargs["allowed_function_names"] = allowed_function_names

        return self.types.ToolConfig(
            function_calling_config=self.types.FunctionCallingConfig(**function_config_kwargs)
        )

    def generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[Any] = None,
    ) -> tuple[str | None, List[Any] | None, ModelUsageStats]:
        if not self.client or not self.types:
            return self._fallback_generate(messages, tools, tool_choice)

        try:
            system_instruction, dynamic_messages = self._split_static_system(messages)
            gemini_tools = self._convert_tools_for_gemini(tools)
            tool_config = None
            if tool_choice is not None:
                tool_choice_value = tool_choice.lower() if isinstance(tool_choice, str) else None
                if gemini_tools or tool_choice_value != "auto":
                    tool_config = self._convert_tool_choice_for_gemini(tool_choice)
            can_use_cache_with_tool_choice = (
                tool_choice is None
                or (isinstance(tool_choice, str) and tool_choice.lower() == "auto")
            )
            cached_content = (
                self._get_cached_content_name(system_instruction, gemini_tools)
                if can_use_cache_with_tool_choice
                else None
            )
            contents = self._convert_messages_for_gemini(dynamic_messages)

            config_kwargs: dict[str, Any] = {
                "temperature": self.temperature,
                "automatic_function_calling": self.types.AutomaticFunctionCallingConfig(disable=True),
            }
            if tool_config and not cached_content:
                config_kwargs["tool_config"] = tool_config
            if cached_content:
                config_kwargs["cached_content"] = cached_content
            else:
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction
                if gemini_tools:
                    config_kwargs["tools"] = gemini_tools

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents or "",
                config=self.types.GenerateContentConfig(**config_kwargs),
            )
        except Exception as e:
            log("warn", "Gemini native generation failed, using OpenAI-compatible fallback:", e, traceback.format_exc())
            return self._fallback_generate(messages, tools, tool_choice)

        usage_metadata = self._extract_usage(response)
        response_actions = self._extract_tool_calls(response)
        response_text = None if response_actions else (getattr(response, "text", None) or None)

        if response_text is None and response_actions is None:
            return (None, None, usage_metadata)

        return (response_text, response_actions, usage_metadata)

    def list_models(self) -> List[str]:
        if not self.client:
            return self.fallback_model.list_models() if hasattr(self.fallback_model, "list_models") else []
        models = self.client.models.list()
        return [str(getattr(model, "name", getattr(model, "id", ""))) for model in models]

class OpenAIEmbeddingModel(EmbeddingModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, extra_headers: Optional[dict] = None, extra_body: Optional[dict] = None):
        super().__init__(model_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}

    def create_embedding(self, input_text: str) -> tuple[str, List[float]]:
        params: dict[str, Any] = {
            "model": self.model_name,
            "input": input_text,
            **self.extra_body
        }
        if self.extra_headers:
            params["extra_headers"] = self.extra_headers
            
        response = self.client.embeddings.create(**params)
        return (response.model, response.data[0].embedding)

class STTModel(ABC):
    model_name: str

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def transcribe(self, audio: sr.AudioData) -> str:
        pass

class OpenAISTTModel(STTModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, language: Optional[str] = None, prompt: Optional[str] = None):
        super().__init__(model_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.language = language
        self.prompt = prompt

    def transcribe(self, audio: sr.AudioData) -> str:
        audio_raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        # Convert raw PCM data to numpy array
        audio_np = np.frombuffer(audio_raw, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Create a BytesIO buffer for the Ogg file
        audio_ogg = io.BytesIO()
        
        # Write as Ogg Vorbis
        sf.write(audio_ogg, audio_np, 16000, format='OGG', subtype='VORBIS')
        audio_ogg.seek(0)
        audio_ogg.name = "audio.ogg"  # OpenAI needs a filename
        
        try:
            kwargs: dict[str, Any] = {
                "model": self.model_name,
                "file": audio_ogg,
                "language": self.language if self.language else None,  # pyright: ignore[reportArgumentType]
            }
            if self.prompt:
                kwargs["prompt"] = self.prompt

            transcription = self.client.audio.transcriptions.create(**kwargs)
        except APIStatusError as e:
            log("debug", "STT error request:", e.request.method, e.request.url, e.request.headers)
            log("debug", "STT error response:", e.response.status_code, e.response.headers, e.response.read().decode('utf-8', errors='replace'))
            
            try:
                error: dict = e.body[0] if hasattr(e, 'body') and e.body and isinstance(e.body, list) else e.body # pyright: ignore[reportAssignmentType]
                message = error.get('error', {}).get('message', e.body if e.body else 'Unknown error')
            except:
                message = e.message
            
            raise LLMError(f'STT {e.response.reason_phrase}: {message}', e)
        
        text = transcription.text
        return text

class OpenAIMultiModalSTTModel(STTModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, prompt: Optional[str] = None):
        super().__init__(model_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.prompt = prompt

    def transcribe(self, audio: sr.AudioData) -> str:
        audio_raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        # Convert raw PCM data to numpy array
        audio_np = np.frombuffer(audio_raw, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Create a BytesIO buffer for the Ogg file
        audio_wav = io.BytesIO()
        
        # Write as Ogg Vorbis
        sf.write(audio_wav, audio_np, 16000, format='WAV', subtype='PCM_16')
        audio_wav.seek(0)
        audio_wav.name = "audio.wav"  # OpenAI needs a filename
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role":"system", "content":
                        "You are a high quality transcription model. You are given audio input from the user, and return the transcribed text from the input. Do NOT add any additional text in your response, only respond with the text given by the user.\n" +
                        "The audio may be related to space sci-fi terminology like systems, equipment, and station names, specifically the game Elite Dangerous.\n" + 
                        #"Here is an example of the type of text you should return: <example>" + self.prompt + "</example>\n" +
                        "Always provide an exact transcription of the audio. If the user is not speaking or inaudible, return only the word 'silence'."
                    },
                    {"role": "user", "content": [{
                        "type": "text",
                        "text": "<input>"
                    },{
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio_wav.getvalue()).decode('utf-8'),
                            "format": "wav"
                        }
                    },{
                        "type": "text",
                        "text": "</input>"
                    },]}
                ]
            )
        except APIStatusError as e:
            log("debug", "STT mm error request:", e.request.method, e.request.url, e.request.headers, e.request.read().decode('utf-8', errors='replace'))
            log("debug", "STT mm error response:", e.response.status_code, e.response.headers, e.response.read().decode('utf-8', errors='replace'))
            
            try:
                error: dict = e.body[0] if hasattr(e, 'body') and e.body and isinstance(e.body, list) else e.body # pyright: ignore[reportAssignmentType]
                message = error.get('error', {}).get('message', e.body if e.body else 'Unknown error')
            except:
                message = e.message
            
            raise LLMError(f'STT {e.response.reason_phrase}: {message}', e)
        
        if not response.choices or not hasattr(response.choices[0], 'message') or not hasattr(response.choices[0].message, 'content'):
            log('debug', "STT mm response is incomplete or malformed:", response)
            raise LLMError('STT completion error: Response incomplete or malformed')
        
        text = response.choices[0].message.content
        if not text:
            return ''
        if text.strip() == 'silence' or text.strip() == '':
            return ''
        return text.strip()

class Mp3Stream(miniaudio.StreamableSource):
    def __init__(self, gen: Generator, prebuffer_size=4, initial_timeout: float = 10.0, chunk_timeout: float = 5.0) -> None:
        super().__init__()
        self.gen = gen
        self.prebuffer_size = prebuffer_size
        self.initial_timeout = initial_timeout
        self.chunk_timeout = chunk_timeout
        self.buffer = bytearray()
        self._done = False
        self._closed = False
        self._first_chunk = False
        self._last_chunk_time = time()
        threading.Thread(target=self._produce, daemon=True).start()

    def _produce(self):
        try:
            for ev in self.gen:
                if self._closed:
                    break
                if isinstance(ev, dict) and ev.get('type') == 'audio':
                    self.buffer.extend(ev['data'])
                    self._first_chunk = True
                    self._last_chunk_time = time()
        except Exception as e:
            log('error', 'Mp3Stream producer exception', e, traceback.format_exc())
            raise e
        finally:
            self._done = True

    def close(self):  # type: ignore[override]
        self._closed = True
        return super().close()

    def read(self, num_bytes: int) -> bytes:
        if self._closed:
            return b''
        out = bytearray()
        need = max(self.prebuffer_size * 720, num_bytes)
        while len(out) < need:
            # timeout checks
            timeout = self.initial_timeout if not self._first_chunk else self.chunk_timeout
            if (not self._done) and (time() - self._last_chunk_time > timeout):
                log('warn', 'TTS Stream timeout (initial)' if not self._first_chunk else 'TTS Stream timeout (gap)')
                self.close()
                raise IOError('TTS Stream timeout')
            if self.buffer:
                take = min(len(self.buffer), need - len(out))
                out.extend(self.buffer[:take])
                del self.buffer[:take]
            else:
                if self._done:
                    break
                sleep(0.01)
        return bytes(out)

class TTSModel(ABC):
    model_name: str

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def synthesize(self, text: str, voice: str) -> Iterable[bytes]:
        pass

class OpenAITTSModel(TTSModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, speed: float = 1.0, voice_instructions: str | None = None):
        super().__init__(model_name)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.speed = speed
        self.voice_instructions = voice_instructions

    def synthesize(self, text: str, voice: str) -> Iterable[bytes]:
        try:
            kwargs: SpeechCreateParams = {
                "model": self.model_name,
                "voice": voice, # pyright: ignore[reportArgumentType]
                "input": text,
                "response_format": "pcm",
                "speed": self.speed
            }
            if self.voice_instructions:
                kwargs["instructions"] = self.voice_instructions
            
            with self.client.audio.speech.with_streaming_response.create(**kwargs) as response:
                for chunk in response.iter_bytes(1024):
                    yield chunk
        except APIStatusError as e:
            log("debug", "TTS error request:", e.request.method, e.request.url, e.request.headers, e.request.read().decode('utf-8', errors='replace'))
            log("debug", "TTS error response:", e.response.status_code, e.response.headers, e.response.read().decode('utf-8', errors='replace'))
            
            try:
                error: dict = e.body[0] if hasattr(e, 'body') and e.body and isinstance(e.body, list) else e.body # pyright: ignore[reportAssignmentType]
                message = error.get('error', {}).get('message', e.body if e.body else 'Unknown error')
            except:
                message = e.message
            
            raise LLMError(f'TTS {e.response.reason_phrase}: {message}', e)

class EdgeTTSModel(TTSModel):
    def __init__(self, model_name: str, speed: float = 1.0):
        super().__init__(model_name)
        self.speed = speed
        self.prebuffer_size = 4

    def synthesize(self, text: str, voice: str) -> Iterable[bytes]:
        rate = f"+{int((float(self.speed) - 1) * 100)}%" if float(self.speed) > 1 else f"-{int((1 - float(self.speed)) * 100)}%"
        response = edge_tts.Communicate(text, voice=voice, rate=rate)
        
        pcm_stream = miniaudio.stream_any(
            source=Mp3Stream(response.stream_sync(), self.prebuffer_size),
            source_format=miniaudio.FileFormat.MP3,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=1,
            sample_rate=24000,
            frames_to_read=1024 // 2
        )

        for i in pcm_stream:
            yield i.tobytes()

def create_llm_model(provider: str, config: dict, prefix: str = "llm") -> LLMModel:
    base_url = str(config.get(f"{prefix}_endpoint", ""))
    api_key = str(config.get("api_key") if config.get(f"{prefix}_api_key", "") == "" else config.get(f"{prefix}_api_key"))
    model_name = str(config.get(f"{prefix}_model_name", ""))
    temperature = float(config.get(f"{prefix}_temperature", 1.0))
    reasoning_effort = config.get(f"{prefix}_reasoning_effort", None)
    if reasoning_effort:
        reasoning_effort = str(reasoning_effort)
    
    if provider == "openai":
        if not base_url:
            base_url = "https://api.openai.com/v1"
    elif provider == "google-ai-studio":
        if not base_url:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
    elif provider == "openrouter":
        if not base_url:
            base_url = "https://openrouter.ai/api/v1"
            
    extra_body = {}
    extra_headers = {}

    if provider == "openai":
        return OpenAIResponsesLLMModel(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            extra_body=extra_body,
            extra_headers=extra_headers,
            provider_name=provider,
        )

    if provider == "google-ai-studio" and ("gemini" in model_name.lower() or "google" in base_url.lower()):
        return GeminiCachedLLMModel(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            extra_body=extra_body,
            extra_headers=extra_headers,
            provider_name=provider,
        )

    return OpenAILLMModel(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        extra_body=extra_body,
        extra_headers=extra_headers,
        provider_name=provider,
    )

def create_embedding_model(provider: str, config: dict, prefix: str = "embedding") -> EmbeddingModel:
    base_url = str(config.get(f"{prefix}_endpoint", ""))
    api_key = str(config.get("api_key") if config.get(f"{prefix}_api_key", "") == "" else config.get(f"{prefix}_api_key"))
    model_name = str(config.get(f"{prefix}_model_name", ""))
    
    if provider == "openai":
        if not base_url:
            base_url = "https://api.openai.com/v1"
    elif provider == "google-ai-studio":
        if not base_url:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
    elif provider == "openrouter":
        if not base_url:
            base_url = "https://openrouter.ai/api/v1"
          

    return OpenAIEmbeddingModel(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
    )

def create_stt_model(provider: str, config: dict, prefix: str = "stt") -> STTModel | None:
    if provider == 'none':
        return None

    base_url = str(config.get(f"{prefix}_endpoint", ""))
    api_key = str(config.get("api_key") if config.get(f"{prefix}_api_key", "") == "" else config.get(f"{prefix}_api_key"))
    model_name = str(config.get(f"{prefix}_model_name", "whisper-1"))
    language = config.get(f"{prefix}_language", None)
    prompt = config.get(f"{prefix}_prompt", "COVAS, give me a status update... and throw in something inspiring, would you?")

    if provider == "openai" or provider == "custom" or provider == "local-ai-server":
        if provider == "openai" and not base_url:
            base_url = "https://api.openai.com/v1"
        return OpenAISTTModel(base_url, api_key, model_name, language, prompt)
    
    elif provider == "google-ai-studio" or provider == "custom-multi-modal":
        if provider == "google-ai-studio" and not base_url:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
        return OpenAIMultiModalSTTModel(base_url, api_key, model_name, prompt)
    
    return None

def create_tts_model(provider: str, config: dict, prefix: str = "tts") -> TTSModel | None:
    if provider == 'none':
        return None

    base_url = str(config.get(f"{prefix}_endpoint", ""))
    api_key = str(config.get("api_key") if config.get(f"{prefix}_api_key", "") == "" else config.get(f"{prefix}_api_key"))
    model_name = str(config.get(f"{prefix}_model_name", "tts-1"))
    speed = float(config.get(f"{prefix}_speed", 1.0))
    voice_instructions = config.get(f"{prefix}_voice_instructions", "") or None

    if provider == "openai" or provider == "custom" or provider == "local-ai-server":
        if provider == "openai" and not base_url:
            base_url = "https://api.openai.com/v1"
        return OpenAITTSModel(base_url, api_key, model_name, speed, voice_instructions)
    
    elif provider == "edge-tts":
        return EdgeTTSModel(model_name, speed)
    
    return None
