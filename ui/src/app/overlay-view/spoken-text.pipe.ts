import { Pipe, PipeTransform } from '@angular/core';

const SPEAKER_ROLES = new Set(['covas', 'assistant', 'npc_message']);
const DELIVERY_TAG = /\[voice:[a-z0-9_-]+\]/gi;
const PERFORMANCE_TAG = /\[(?:chuckle|laugh|sigh|gasp|groan|cough|sniff|shush|shh+|clear throat|breathe|yawn)\]/gi;

@Pipe({ name: 'spokenText', standalone: true })
export class SpokenTextPipe implements PipeTransform {
  transform(text: string, role: string): string {
    if (!SPEAKER_ROLES.has(role?.toLowerCase()) || !text) {
      return text;
    }

    // Display only: never modify shared chat records used by logs or speech.
    const visible = text.replace(DELIVERY_TAG, ' ').replace(PERFORMANCE_TAG, ' ');
    if (visible === text) {
      return text;
    }
    return visible
      .replace(/[ \t]+/g, ' ')
      .replace(/[ \t]*\r?\n[ \t]*/g, '\n')
      .replace(/ +([,.!?;:])/g, '$1')
      .trim();
  }
}
