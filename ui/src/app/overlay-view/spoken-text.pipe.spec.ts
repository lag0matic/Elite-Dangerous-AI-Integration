import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { SpokenTextPipe } from './spoken-text.pipe';

describe('SpokenTextPipe', () => {
  const pipe = new SpokenTextPipe();

  it('hides voice metadata and expressives for assistant captions', () => {
    expect(pipe.transform('[voice:amused] Nice flying. [chuckle]', 'covas')).toBe('Nice flying.');
  });

  it('handles all approved performance tags', () => {
    for (const tag of ['chuckle', 'laugh', 'sigh', 'gasp', 'groan', 'cough', 'sniff', 'shush', 'shhh', 'clear throat', 'breathe', 'yawn']) {
      expect(pipe.transform(`One. [${tag}] Two.`, 'covas')).toBe('One. Two.');
    }
  });

  it('preserves ordinary brackets and Unicode', () => {
    expect(pipe.transform('[voice:soft] You’re home, Dark—[cargo: gold]. [sigh]', 'assistant')).toBe('You’re home, Dark—[cargo: gold].');
  });

  it('does not alter commander text or diagnostic messages', () => {
    const raw = '[voice:amused] Say [laugh], please.';
    for (const role of ['cmdr', 'user', 'error', 'info', 'event', 'action']) {
      expect(pipe.transform(raw, role)).toBe(raw);
    }
  });

  it('handles other shipboard voices and mixed case', () => {
    expect(pipe.transform('[VOICE:ANGRY] [GROAN] Fine.', 'NPC_MESSAGE')).toBe('Fine.');
  });

  it('cleans metadata-only lines without flattening the reply', () => {
    expect(pipe.transform('[voice:soft]\r\n[sigh]\r\nHello.\r\nWelcome back.', 'covas')).toBe('Hello.\nWelcome back.');
  });

  it('does not merge words or leave a gap before punctuation', () => {
    expect(pipe.transform('One[chuckle]two [sigh].', 'covas')).toBe('One two.');
  });

  it('preserves text exactly when no tags are present', () => {
    const raw = 'One  deliberate space.\nAnother line.';
    expect(pipe.transform(raw, 'covas')).toBe(raw);
  });

  it('accepts empty captions', () => {
    expect(pipe.transform('', 'covas')).toBe('');
    expect(pipe.transform('[voice:neutral] [sigh]', 'covas')).toBe('');
  });

  it('renders clean text without mutating the original chat record', async () => {
    @Component({ standalone: true, imports: [SpokenTextPipe], template: '<span>{{ message.message | spokenText:message.role }}</span>' })
    class TestCaption {
      message = Object.freeze({ role: 'covas', message: '[voice:amused] Pad two, Boss. [chuckle]' });
    }
    await TestBed.configureTestingModule({ imports: [TestCaption] }).compileComponents();
    const fixture = TestBed.createComponent(TestCaption);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toBe('Pad two, Boss.');
    expect(fixture.componentInstance.message.message).toBe('[voice:amused] Pad two, Boss. [chuckle]');
  });
});
