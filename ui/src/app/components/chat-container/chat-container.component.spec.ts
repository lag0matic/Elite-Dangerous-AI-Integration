import { TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';
import { ChatContainerComponent } from './chat-container.component';
import { ChatMessage, ChatService } from '../../services/chat.service';
import { CharacterService } from '../../services/character.service';

describe('ChatContainerComponent delivery metadata', () => {
  it('hides assistant tags in main chat without modifying raw messages', async () => {
    const raw = '[voice:amused] Loud and clear, Boss. [chuckle]';
    const messages: ChatMessage[] = [
      Object.freeze({ type: 'chat' as const, role: 'cmdr', message: 'Please use [laugh].', index: 1, timestamp: '2026-11-01T20:00:00Z' }),
      Object.freeze({ type: 'chat' as const, role: 'covas', message: raw, index: 2, timestamp: '2026-11-01T20:00:01Z' }),
    ];
    const history = new BehaviorSubject(messages);
    await TestBed.configureTestingModule({
      imports: [ChatContainerComponent],
      providers: [
        { provide: ChatService, useValue: { chatHistory$: history.asObservable() } },
        { provide: CharacterService, useValue: { character$: new BehaviorSubject(null).asObservable() } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(ChatContainerComponent);
    fixture.detectChanges();
    const displayed = Array.from(fixture.nativeElement.querySelectorAll('.message') as NodeListOf<HTMLElement>).map(element => element.textContent?.trim());
    expect(displayed).toEqual(['Please use [laugh].', 'Loud and clear, Boss.']);
    expect(history.value[1].message).toBe(raw);
    expect(fixture.componentInstance.chat[1].message).toBe(raw);
    fixture.destroy();
  });
});
