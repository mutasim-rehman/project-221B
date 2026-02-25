/** API client for 221B backend. Uses VITE_API_BASE when set; falls back to mock when unreachable. */

const API_BASE = (import.meta.env.VITE_API_BASE as string) || ''

export interface CaseStoryResponse {
  story: string
  characters: string[]
  sources: string[]
  mode: string
  setting: string
}

export interface ChatroomResponse {
  scene: string
  characters: string[]
  sources: string[]
  mode: string
  setting: string
}

export interface CharacterChatResponse {
  reply: string
  character: string
  sources: string[]
  mode: string
  strictness: string
}

function getSessionId(): string {
  let sid = sessionStorage.getItem('221b_session_id')
  if (!sid) {
    sid = crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem('221b_session_id', sid)
  }
  return sid
}

async function post<T>(path: string, body: Record<string, string>): Promise<T> {
  if (!API_BASE) {
    throw new Error('API_BASE not configured')
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchCaseStory(casePrompt: string, strictness = 'creative'): Promise<CaseStoryResponse> {
  try {
    const sessionId = getSessionId()
    const data = await post<CaseStoryResponse>('/api/six-case-story', {
      case_prompt: casePrompt,
      session_id: sessionId,
      strictness,
    })
    return data
  } catch {
    return mockCaseStory(casePrompt)
  }
}

export async function fetchChatroomTurn(question: string, strictness = 'balanced'): Promise<ChatroomResponse> {
  try {
    const sessionId = getSessionId()
    const data = await post<ChatroomResponse>('/api/six-chatroom', {
      question,
      session_id: sessionId,
      strictness,
    })
    return data
  } catch {
    return mockChatroomTurn(question)
  }
}

export async function fetchCharacterReply(
  characterKey: string,
  question: string,
  strictness = 'strict'
): Promise<string> {
  try {
    const sessionId = getSessionId()
    const data = await post<CharacterChatResponse>('/api/character-chat', {
      character_key: characterKey,
      question,
      session_id: sessionId,
      strictness,
    })
    return data.reply
  } catch {
    return mockCharacterReplyText(characterKey, question)
  }
}

function mockCharacterReplyText(characterKey: string, question: string): string {
  const lowered = question.trim().toLowerCase()
  const prompts: Record<string, string> = {
    sherlock:
      'From the fragments you provide, certain general conclusions may already be drawn. Yet I advise you to add every small, seemingly irrelevant detail; it is upon such trifles that cases have so often turned.',
    watson:
      'Your account has the ring of genuine experience. I should like to know a little more of the circumstances and of the persons involved, if you would not find it too great a strain to relate them.',
    moriarty:
      "You stand, perhaps without knowing it, at the edge of a very intricate web. Before you proceed, be certain you understand what you are prepared to pay for a resolution.",
    irene:
      'There is more to this than you have yet chosen to say. Consider carefully what you wish to reveal, and then tell me the part that matters most to you.',
    mycroft:
      'The picture is incomplete. Supply the missing elements, and I will determine whether the matter warrants further attention.',
    lestrade:
      "I need names, dates, and what you saw. Nothing else will do. When you have them, come back.",
  }
  if (!lowered) {
    return 'A blank page rarely conceals a trivial matter. When you are ready, give me the bare facts as you know them.'
  }
  return prompts[characterKey] ?? prompts.lestrade
}

function mockChatroomTurn(_question: string): ChatroomResponse {
  const scene = `Sherlock Holmes: You raise a most intriguing point. Watson, you have observed the same irregularity in the timeline?

Dr. John Watson: I confess it had escaped my notice until you drew attention to it, Holmes.

Professor James Moriarty: Perhaps the irregularity is not in the timeline, but in the assumptions we bring to it.

Irene Adler: I should like to hear what the inspector makes of it.

Inspector G. Lestrade: I make of it that we need more facts. Evidence, gentlemen. Evidence.

Mycroft Holmes: The matter will resolve itself when the relevant papers are consulted. Until then, speculation is merely exercise.`
  return {
    scene,
    characters: ['Sherlock Holmes', 'Dr. John Watson', 'Professor James Moriarty', 'Irene Adler', 'Inspector G. Lestrade', 'Mycroft Holmes'],
    sources: ['The Red-Headed League', 'A Scandal in Bohemia'],
    mode: 'six_chatroom',
    setting: 'room_conversation',
  }
}

function mockCaseStory(casePrompt: string): CaseStoryResponse {
  const prompts: Record<string, string> = {
    default:
      'The gas lamps had barely been lit along Pall Mall when a most singular delegation arrived at 221B. Sherlock Holmes, Dr. Watson, Professor Moriarty, Irene Adler, Inspector Lestrade, and Mycroft Holmes found themselves convened—each for reasons they would only gradually reveal. The case, as Watson would later record it, began with a cipher and ended with a truth no single mind could have deduced alone.',
  }
  const story =
    prompts[casePrompt.toLowerCase().slice(0, 20)] ??
    prompts.default.replace(
      'The case, as Watson would later record it',
      `The case—${casePrompt.slice(0, 80)}${casePrompt.length > 80 ? '…' : ''}—as Watson would later record it`
    )
  return {
    story,
    characters: ['Sherlock Holmes', 'Dr. John Watson', 'Professor James Moriarty', 'Irene Adler', 'Inspector G. Lestrade', 'Mycroft Holmes'],
    sources: ['A Study in Scarlet', 'The Sign of Four'],
    mode: 'six_case_story',
    setting: 'case_story',
  }
}
