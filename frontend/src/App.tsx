import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { fetchCanonReply, fetchCaseStory, fetchCharacterReply, fetchChatroomTurn, isApiConfigured, warmupConnection } from './api'

import sherlockImg from '../resources/sherlock.png'
import watsonImg from '../resources/watson.png'
import moriartyImg from '../resources/moriarty.png'
import ireneImg from '../resources/irene.png'
import mycroftImg from '../resources/mycroft.png'
import lestradeImg from '../resources/lestrade.png'
import sherlockWatsonImg from '../resources/sherlock+watson.png'
import fullCastImg from '../resources/sherlock+watson+mycroft+irene.png'
import atmosphericsImg from '../resources/atmospherics.jpg'

type CharacterKey = 'sherlock' | 'watson' | 'moriarty' | 'irene' | 'mycroft' | 'lestrade'

type SixMode = 'case_story' | 'chatroom'

type MobileArchiveChoice = null | 'character' | 'six' | 'canon'

type Speaker = 'user' | 'character'

const CHARACTER_IMAGES: Record<CharacterKey, string> = {
  sherlock: sherlockImg,
  watson: watsonImg,
  moriarty: moriartyImg,
  irene: ireneImg,
  mycroft: mycroftImg,
  lestrade: lestradeImg,
}

interface CharacterConfig {
  key: CharacterKey
  name: string
  title: string
  summary: string
  tone: string
  signature: string
}

interface Message {
  id: string
  speaker: Speaker
  text: string
  createdAt: string
}

const CHARACTERS: CharacterConfig[] = [
  {
    key: 'sherlock',
    name: 'Sherlock Holmes',
    title: 'Consulting Detective',
    summary:
      'An intellect honed to a razor edge; laconic, precise, and relentlessly observant. Expects you to present the facts.',
    tone: 'Analytical, dry, exacting.',
    signature: 'S.H.',
  },
  {
    key: 'watson',
    name: 'Dr. John Watson',
    title: 'Medical Doctor & Chronicler',
    summary:
      'A steady, compassionate correspondent. Records your case with warmth and clarity, and never withholds his admiration for Holmes.',
    tone: 'Warm, narrative, gentlemanly.',
    signature: 'J.H.W.',
  },
  {
    key: 'moriarty',
    name: 'Professor James Moriarty',
    title: 'Consulting Criminal',
    summary:
      'A mind of chilling symmetry and calculation. Treats every problem as an exercise in pure intellect—morals notwithstanding.',
    tone: 'Polite, measured, quietly menacing.',
    signature: 'J.M.',
  },
  {
    key: 'irene',
    name: 'Irene Adler',
    title: 'The Woman',
    summary:
      'Independent, inscrutable, and alert to every unspoken implication. Assists only on terms of her own choosing.',
    tone: 'Wry, self‑possessed, incisive.',
    signature: 'I.A.',
  },
  {
    key: 'mycroft',
    name: 'Mycroft Holmes',
    title: 'Government Functionary',
    summary:
      'Sherlock’s elder brother: greater powers of reasoning, but physically indolent. Speaks with authority and brevity, often alluding to affairs of state.',
    tone: 'Concise, formal, cryptic.',
    signature: 'M.H.',
  },
  {
    key: 'lestrade',
    name: 'Inspector G. Lestrade',
    title: 'Scotland Yard Inspector',
    summary:
      'Energetic, dogged, occasionally brusque. Respects Holmes’s methods but remains proud of official police work and procedure.',
    tone: 'Straightforward, practical, no-nonsense.',
    signature: 'G.L.',
  },
]

const MOBILE_BREAKPOINT = 640

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  )
  useEffect(() => {
    const mq = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mq.addEventListener('change', handler)
    setMatches(mq.matches)
    return () => mq.removeEventListener('change', handler)
  }, [query])
  return matches
}

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function makeId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function buildInitialWelcome(character: CharacterConfig): Message[] {
  const now = new Date()
  const label =
    character.key === 'sherlock'
      ? 'Case file received at Baker Street.'
      : character.key === 'watson'
      ? 'Your particulars will be recorded with care.'
      : character.key === 'moriarty'
      ? 'A most curious problem presents itself.'
      : character.key === 'irene'
      ? 'You have the attention of a most singular correspondent.'
      : character.key === 'mycroft'
      ? 'Communications received. State the matter.'
      : 'Inspector Lestrade, Scotland Yard. Get to the point.'

  const body =
    character.key === 'sherlock'
      ? 'Pray set down your case plainly: the facts first, the conjectures afterward. I shall concern myself with the inferences.'
      : character.key === 'watson'
      ? 'Tell me, in your own words, what weighs upon your mind. I shall do my best to arrange the narrative and, where needful, to consult Holmes.'
      : character.key === 'moriarty'
      ? 'State the problem without ornament. Every system has its weak points; it is merely a question of discovering where the pressure should be applied.'
      : character.key === 'irene'
      ? 'You may be assured that whatever you confide will go no farther than is advantageous to us both. Begin where the story truly starts, not where convention would have it begin.'
      : character.key === 'mycroft'
      ? 'Be brief. I have little time for digression. The essential facts, in order of importance.'
      : 'Evidence and procedure, that’s what counts. Give me the facts, and we’ll see what the law makes of them.'

  return [
    {
      id: makeId(),
      speaker: 'character',
      text: `${label}\n\n${body}`,
      createdAt: formatTimestamp(now),
    },
  ]
}

interface JournalEntryProps {
  message: Message
  character: CharacterConfig
}

function JournalEntry({ message, character }: JournalEntryProps) {
  const isUser = message.speaker === 'user'
  const label = isUser ? 'Case entry' : 'Correspondence'
  const speakerLabel = isUser ? 'You' : character.name

  return (
    <article
      className={`journal-entry ${isUser ? 'journal-entry--user' : 'journal-entry--character'}`}
      aria-label={`${label} — ${speakerLabel}`}
    >
      <header className="journal-header">
        {!isUser && (
          <img
            src={CHARACTER_IMAGES[character.key]}
            alt=""
            className="journal-avatar"
            aria-hidden="true"
          />
        )}
        <div className="journal-header-text">
          <div className="journal-label">
            <strong>{label}</strong> — {speakerLabel}
          </div>
          <div className="journal-meta">{message.createdAt}</div>
        </div>
      </header>
      <div className="journal-body">{message.text}</div>
      {!isUser && (
        <div className="journal-signature">
          — <span>{character.signature}</span>
        </div>
      )}
    </article>
  )
}

const SIX_CHARACTER_NAMES =
  'Sherlock Holmes, Dr. John Watson, Professor Moriarty, Irene Adler, Inspector Lestrade, and Mycroft Holmes'

/** Placeholder config for canon mode replies (RAG Q&A over canon index). */
const CANON_PLACEHOLDER: CharacterConfig = {
  key: 'sherlock',
  name: 'The Canon Index',
  title: 'RAG-powered Q&A',
  summary: 'Questions answered from the Sherlock Holmes canon.',
  tone: 'Factual, grounded in text.',
  signature: '—',
}

function App() {
  useEffect(() => {
    warmupConnection()
  }, [])

  const isMobile = useMediaQuery(`(max-width: ${MOBILE_BREAKPOINT}px)`)
  const [mobileArchiveChoice, setMobileArchiveChoice] = useState<MobileArchiveChoice>(null)
  const [activeKey, setActiveKey] = useState<CharacterKey | null>(null)
  const [activeSixMode, setActiveSixMode] = useState<SixMode | null>(null)
  const [activeCanonMode, setActiveCanonMode] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [isAwaitingReply, setIsAwaitingReply] = useState(false)
  const [caseStory, setCaseStory] = useState<string | null>(null)
  const [chatroomScenes, setChatroomScenes] = useState<{ id: string; userText: string; scene: string; createdAt: string }[]>([])

  const chatJournalRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const el = chatJournalRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages, chatroomScenes])

  const activeCharacter = useMemo(
    () => CHARACTERS.find((c) => c.key === activeKey) ?? null,
    [activeKey],
  )

  const handleSelectCharacter = (character: CharacterConfig) => {
    setActiveKey(character.key)
    setActiveSixMode(null)
    setActiveCanonMode(false)
    setMessages(buildInitialWelcome(character))
    setDraft('')
    setIsAwaitingReply(false)
    setCaseStory(null)
    setChatroomScenes([])
  }

  const handleSelectSixMode = (mode: SixMode) => {
    setActiveSixMode(mode)
    setActiveKey(null)
    setActiveCanonMode(false)
    setMessages([])
    setDraft('')
    setIsAwaitingReply(false)
    setCaseStory(null)
    setChatroomScenes([])
  }

  const handleSelectCanonMode = () => {
    setActiveCanonMode(true)
    setActiveKey(null)
    setActiveSixMode(null)
    setMessages([])
    setDraft('')
    setIsAwaitingReply(false)
    setCaseStory(null)
    setChatroomScenes([])
  }

  const handleReturnToArchive = () => {
    setMobileArchiveChoice(null)
    setActiveKey(null)
    setActiveSixMode(null)
    setActiveCanonMode(false)
    setMessages([])
    setDraft('')
    setIsAwaitingReply(false)
    setCaseStory(null)
    setChatroomScenes([])
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!activeCharacter) return
    const trimmed = draft.trim()
    if (!trimmed || isAwaitingReply) return

    const now = new Date()
    const userMessage: Message = {
      id: makeId(),
      speaker: 'user',
      text: trimmed,
      createdAt: formatTimestamp(now),
    }

    setMessages((prev) => [...prev, userMessage])
    setDraft('')
    setIsAwaitingReply(true)

    try {
      const replyText = await fetchCharacterReply(activeCharacter.key, trimmed)
      const reply: Message = {
        id: makeId(),
        speaker: 'character',
        text: replyText,
        createdAt: formatTimestamp(new Date()),
      }
      setMessages((prev) => [...prev, reply])
    } finally {
      setIsAwaitingReply(false)
    }
  }

  const handleCanonSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || isAwaitingReply) return

    const now = new Date()
    const userMessage: Message = {
      id: makeId(),
      speaker: 'user',
      text: trimmed,
      createdAt: formatTimestamp(now),
    }
    setMessages((prev) => [...prev, userMessage])
    setDraft('')
    setIsAwaitingReply(true)

    try {
      const answer = await fetchCanonReply(trimmed, 'strict')
      const reply: Message = {
        id: makeId(),
        speaker: 'character',
        text: answer,
        createdAt: formatTimestamp(new Date()),
      }
      setMessages((prev) => [...prev, reply])
    } finally {
      setIsAwaitingReply(false)
    }
  }

  if (activeCanonMode) {
    return (
      <div className="archive-shell">
        <div className="archive-inner archive-inner--chat">
          <aside className="sidebar-card" aria-label="Interactive canon mode">
            <div className="sidebar-header">
              <div className="sidebar-title">
                <div className="sidebar-label">Interactive canon</div>
                <div className="sidebar-character-name">RAG Q&A over the canon</div>
              </div>
              <button
                type="button"
                className="sidebar-back"
                onClick={handleReturnToArchive}
                aria-label="Exit and return to the main archives"
              >
                <span>←</span>
                <span>Exit</span>
              </button>
            </div>
            <div className="sidebar-meta">
              <strong>Ask the canon directly</strong>
              <br />
              Pose questions about the Sherlock Holmes stories. The system retrieves relevant passages and answers from the indexed canon.
            </div>
            {!isApiConfigured && (
              <div className="sidebar-note">
                API not connected. Replies use local mocks. Set VITE_GRADIO_SPACE or VITE_API_BASE to connect.
              </div>
            )}
          </aside>
          <main className="chat-shell" aria-label="Interactive canon conversation">
            <header className="chat-header">
              <div>
                <div className="chat-heading">
                  Interactive canon — <span>RAG Q&A</span>
                </div>
                <div className="chat-subtitle">
                  Ask questions about the Sherlock Holmes canon. Answers are grounded in retrieved passages.
                </div>
              </div>
              <div className="chat-header-meta">
                Session mode: <strong>Canon Q&A</strong>
              </div>
            </header>

            <section ref={chatJournalRef} className="chat-journal" aria-label="Conversation log">
              {messages.length === 0 && (
                <article className="journal-entry journal-entry--character">
                  <header className="journal-header">
                    <div className="journal-label"><strong>Welcome</strong> — The Canon Index</div>
                  </header>
                  <div className="journal-body">
                    Ask a question about the Sherlock Holmes stories. The system will retrieve relevant passages and provide an answer grounded in the canon.
                  </div>
                </article>
              )}
              {messages.map((message) => (
                <JournalEntry
                  key={message.id}
                  message={message}
                  character={CANON_PLACEHOLDER}
                />
              ))}
            </section>

            <form className="chat-input-row" onSubmit={handleCanonSubmit}>
              <div className="chat-input">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="e.g. Who is Mycroft? What happened in the Hound of the Baskervilles?"
                  aria-label="Question for the canon"
                />
                <div className="chat-hint" data-hide-on-mobile>
                  Questions about characters, plots, and details from the stories.
                </div>
              </div>
              <div>
                <button
                  className="chat-submit"
                  type="submit"
                  disabled={!draft.trim() || isAwaitingReply}
                  aria-label={isAwaitingReply ? 'Awaiting reply' : 'Send question'}
                >
                  <span className="chat-submit__icon chat-submit__icon--desktop" aria-hidden>✉</span>
                  <span className="chat-submit__icon chat-submit__icon--mobile" aria-hidden>→</span>
                  <span className="chat-submit__label">{isAwaitingReply ? 'Fetching…' : 'Send question'}</span>
                </button>
                <div
                  className="chat-status"
                  data-hide-on-mobile={!isAwaitingReply ? '' : undefined}
                >
                  {isAwaitingReply
                    ? 'Retrieving passages and generating answer…'
                    : isApiConfigured
                      ? 'Answers are grounded in retrieved canon passages.'
                      : 'API not connected. Replies use local mocks.'}
                </div>
              </div>
            </form>
          </main>
        </div>
      </div>
    )
  }

  if (activeSixMode === 'case_story') {
    return (
      <div className="archive-shell">
        <div className="archive-inner archive-inner--chat">
          <aside className="sidebar-card" aria-label="Case story mode">
            <div className="sidebar-header">
              <div className="sidebar-title">
                <div className="sidebar-label">Six-character mode</div>
                <div className="sidebar-character-name">Case-based story</div>
              </div>
              <button
                type="button"
                className="sidebar-back"
                onClick={handleReturnToArchive}
                aria-label="Exit and return to the main archives"
              >
                <span>←</span>
                <span>Exit</span>
              </button>
            </div>
            <div className="sidebar-meta">
              <strong>Generate a story</strong>
              <br />
              Describe a case or scenario. The system will generate a short story episode featuring{' '}
              {SIX_CHARACTER_NAMES}.
            </div>
          </aside>
          <main className="chat-shell" aria-label="Case story">
            <header className="chat-header">
              <div>
                <div className="chat-heading">Case-based story — <span>all six characters</span></div>
                <div className="chat-subtitle">
                  Enter a case prompt below. The story is grounded in canon and generated with the full cast.
                </div>
              </div>
            </header>
            {!caseStory ? (
              <form
                className="chat-input-row case-story-form"
                onSubmit={async (e: FormEvent) => {
                  e.preventDefault()
                  const trimmed = draft.trim()
                  if (!trimmed || isAwaitingReply) return
                  setIsAwaitingReply(true)
                  setDraft('')
                  try {
                    const res = await fetchCaseStory(trimmed)
                    setCaseStory(res.story)
                  } finally {
                    setIsAwaitingReply(false)
                  }
                }}
              >
                <div className="chat-input">
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="e.g. A jewel theft at the Diogenes Club that implicates a government official…"
                    aria-label="Case prompt"
                  />
                </div>
                <button
                  className="chat-submit"
                  type="submit"
                  disabled={!draft.trim() || isAwaitingReply}
                >
                  <span>✉</span>
                  <span>{isAwaitingReply ? 'Generating…' : 'Generate story'}</span>
                </button>
              </form>
            ) : (
              <section className="chat-journal">
                <article className="journal-entry journal-entry--character">
                  <header className="journal-header">
                    <div className="journal-label"><strong>Story</strong> — Generated episode</div>
                  </header>
                  <div className="journal-body" style={{ whiteSpace: 'pre-wrap' }}>{caseStory}</div>
                </article>
              </section>
            )}
          </main>
        </div>
      </div>
    )
  }

  if (activeSixMode === 'chatroom') {
    return (
      <div className="archive-shell">
        <div className="archive-inner archive-inner--chat">
          <aside className="sidebar-card" aria-label="Chatroom mode">
            <div className="sidebar-header">
              <div className="sidebar-title">
                <div className="sidebar-label">Six-character mode</div>
                <div className="sidebar-character-name">Character chatroom</div>
              </div>
              <button
                type="button"
                className="sidebar-back"
                onClick={handleReturnToArchive}
                aria-label="Exit and return to the main archives"
              >
                <span>←</span>
                <span>Exit</span>
              </button>
            </div>
            <div className="sidebar-meta">
              <strong>You are in the room</strong>
              <br />
              {SIX_CHARACTER_NAMES} are present. Type a message to steer the conversation; they will respond in character.
            </div>
          </aside>
          <main className="chat-shell" aria-label="Chatroom conversation">
            <header className="chat-header">
              <div>
                <div className="chat-heading">Character chatroom</div>
                <div className="chat-subtitle">
                  All six characters in one room. Your messages guide the discussion.
                </div>
              </div>
            </header>
            <section ref={chatJournalRef} className="chat-journal">
              {chatroomScenes.length === 0 && (
                <article className="journal-entry journal-entry--character">
                  <header className="journal-header">
                    <div className="journal-label"><strong>Scene</strong> — The room awaits</div>
                  </header>
                  <div className="journal-body">
                    The six have gathered. Address them — pose a question, introduce a topic, or describe a situation. They will respond.
                  </div>
                </article>
              )}
              {chatroomScenes.map(({ id, userText, scene, createdAt }) => (
                <div key={id}>
                  <article className="journal-entry journal-entry--user">
                    <header className="journal-header">
                      <div className="journal-label"><strong>You</strong></div>
                      <div className="journal-meta">{createdAt}</div>
                    </header>
                    <div className="journal-body">{userText}</div>
                  </article>
                  <article className="journal-entry journal-entry--character">
                    <header className="journal-header">
                      <div className="journal-label"><strong>Room dialogue</strong></div>
                      <div className="journal-meta">{createdAt}</div>
                    </header>
                    <div className="journal-body chatroom-scene" style={{ whiteSpace: 'pre-wrap' }}>
                      {scene}
                    </div>
                  </article>
                </div>
              ))}
            </section>
            <form
              className="chat-input-row"
              onSubmit={async (e: FormEvent) => {
                e.preventDefault()
                const trimmed = draft.trim()
                if (!trimmed || isAwaitingReply) return
                const now = new Date()
                const userText = trimmed
                setDraft('')
                setIsAwaitingReply(true)
                setChatroomScenes((prev) => [
                  ...prev,
                  {
                    id: makeId(),
                    userText,
                    scene: '…',
                    createdAt: formatTimestamp(now),
                  },
                ])
                try {
                  const res = await fetchChatroomTurn(trimmed)
                  setChatroomScenes((prev) => {
                    const next = [...prev]
                    const last = next[next.length - 1]
                    if (last && last.scene === '…') {
                      next[next.length - 1] = { ...last, scene: res.scene }
                    }
                    return next
                  })
                } finally {
                  setIsAwaitingReply(false)
                }
              }}
            >
              <div className="chat-input">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Address the room…"
                  aria-label="Message to the room"
                />
              </div>
              <button
                className="chat-submit"
                type="submit"
                disabled={!draft.trim() || isAwaitingReply}
              >
                <span>✉</span>
                <span>{isAwaitingReply ? 'Awaiting reply…' : 'Send'}</span>
              </button>
            </form>
          </main>
        </div>
      </div>
    )
  }

  if (!activeCharacter) {
    return (
      <div className="archive-shell">
        <div className="archive-inner">
          <div className="archive-inner-content">
            <header className="archive-hero">
              <div>
                <p className="archive-kicker">Private case records</p>
                <h1 className="archive-title">
                  The Case Archives of <span>Sherlock Holmes</span>
                </h1>
                <p className="archive-subtitle">
                  Converse with the preserved minds of Baker Street. Each exchange is treated as a
                  matter of professional confidence, recorded as if upon paper, by lamplight, in the
                  quiet of 221B.
                </p>
                <p className="archive-hero-tagline">
                  Choose a correspondent below to open their portion of the archive.
                </p>
              </div>
              <div className="archive-hero-metadata">
                <div className="seal-pill">
                  THE BAKER STREET <strong>CASE ARCHIVES</strong>
                </div>
                <div className="hero-plaque" aria-label="Archive identification plaque">
                  <div className="hero-plaque-label">Registry mark</div>
                  <div className="hero-plaque-main">
                    <div className="hero-plaque-title">221B</div>
                    <div className="hero-plaque-sub">Baker Street, London</div>
                  </div>
                </div>
              </div>
            </header>

            <section className="archive-layout" aria-label="Character selection and atmosphere">
              {isMobile && mobileArchiveChoice === null ? (
                <section className="mobile-chooser" aria-label="Choose experience type">
                  <h2 className="section-heading">
                    Choose your <span>experience</span>
                  </h2>
                  <p className="section-lead">
                    Select one to continue.
                  </p>
                  <div className="mobile-chooser-grid">
                    <button
                      type="button"
                      className="mobile-chooser-card"
                      onClick={() => setMobileArchiveChoice('character')}
                    >
                      <div className="mobile-chooser-icon" aria-hidden="true">
                        <img src={sherlockImg} alt="" className="mobile-chooser-illustration" />
                      </div>
                      <div className="mobile-chooser-body">
                        <div className="mobile-chooser-title">Character-based chatbot</div>
                        <p className="mobile-chooser-summary">
                          Consult a single correspondent from the archives—Sherlock, Watson, Moriarty, Irene, Mycroft, or Lestrade.
                        </p>
                        <span className="mobile-chooser-btn">Choose character</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      className="mobile-chooser-card"
                      onClick={() => setMobileArchiveChoice('six')}
                    >
                      <div className="mobile-chooser-icon" aria-hidden="true">
                        <img src={fullCastImg} alt="" className="mobile-chooser-illustration" />
                      </div>
                      <div className="mobile-chooser-body">
                        <div className="mobile-chooser-title">6 character experience</div>
                        <p className="mobile-chooser-summary">
                          Generate a story or enter a chatroom with all six characters together.
                        </p>
                        <span className="mobile-chooser-btn">View options</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      className="mobile-chooser-card"
                      onClick={() => {
                        setMobileArchiveChoice('canon')
                        handleSelectCanonMode()
                      }}
                    >
                      <div className="mobile-chooser-icon" aria-hidden="true">
                        <img src={sherlockWatsonImg} alt="" className="mobile-chooser-illustration" />
                      </div>
                      <div className="mobile-chooser-body">
                        <div className="mobile-chooser-title">Interactive canon mode</div>
                        <p className="mobile-chooser-summary">
                          Ask questions directly about the Sherlock Holmes canon. RAG-powered Q&A.
                        </p>
                        <span className="mobile-chooser-btn">Ask the canon</span>
                      </div>
                    </button>
                  </div>
                </section>
              ) : isMobile && mobileArchiveChoice === 'character' ? (
                <section className="character-panel character-panel--mobile-drill" aria-label="Character selection">
                  <button
                    type="button"
                    className="mobile-drill-back"
                    onClick={() => setMobileArchiveChoice(null)}
                    aria-label="Back to experience choice"
                  >
                    <span>←</span>
                    <span>Back</span>
                  </button>
                  <h2 className="section-heading">
                    Whom will you <span>consult</span>?
                  </h2>
                  <p className="section-lead">
                    Select one to open a private exchange in the case journal.
                  </p>
                  <div className="character-grid">
                    {CHARACTERS.map((character) => (
                      <button
                        key={character.key}
                        type="button"
                        className={`character-card${
                          activeKey === character.key ? ' is-active' : ''
                        }`}
                        onClick={() => handleSelectCharacter(character)}
                      >
                        <div className="portrait-frame" aria-hidden="true">
                          <img
                            src={CHARACTER_IMAGES[character.key]}
                            alt=""
                            className="portrait-image"
                          />
                        </div>
                        <div className="character-body">
                          <div>
                            <div className="character-name">{character.name}</div>
                            <div className="character-title">{character.title}</div>
                          </div>
                          <p className="character-summary">{character.summary}</p>
                          <div className="character-footer">
                            <div className="character-meta">
                              Tone: <span>{character.tone}</span>
                            </div>
                            <span className="character-button">
                              <span>Consult</span>
                              <span>↗</span>
                            </span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              ) : isMobile && mobileArchiveChoice === 'six' ? (
                <section className="six-mode-panel six-mode-panel--mobile-drill" aria-label="Archive experiences">
                  <button
                    type="button"
                    className="mobile-drill-back"
                    onClick={() => setMobileArchiveChoice(null)}
                    aria-label="Back to experience choice"
                  >
                    <span>←</span>
                    <span>Back</span>
                  </button>
                  <h3 className="six-mode-heading">Archive experiences</h3>
                  <p className="six-mode-lead">
                    Six-character stories, chatroom, or direct canon Q&A.
                  </p>
                  <div className="six-mode-grid">
                    <button
                      type="button"
                      className={`six-mode-card${activeSixMode === 'case_story' ? ' is-active' : ''}`}
                      onClick={() => handleSelectSixMode('case_story')}
                    >
                      <div className="six-mode-icon" aria-hidden="true">
                        <img src={sherlockWatsonImg} alt="" className="six-mode-illustration" />
                      </div>
                      <div className="six-mode-body">
                        <div className="six-mode-title">Case-based story</div>
                        <p className="six-mode-summary">
                          Choose a case or scenario—a theft, a disappearance, a cipher. We generate a story episode
                          involving all six characters, grounded in canon and woven into late Victorian London.
                        </p>
                        <span className="six-mode-btn">Generate story</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      className={`six-mode-card${activeSixMode === 'chatroom' ? ' is-active' : ''}`}
                      onClick={() => handleSelectSixMode('chatroom')}
                    >
                      <div className="six-mode-icon" aria-hidden="true">
                        <img src={fullCastImg} alt="" className="six-mode-illustration" />
                      </div>
                      <div className="six-mode-body">
                        <div className="six-mode-title">Character chatroom</div>
                        <p className="six-mode-summary">
                          Imagine a room at Baker Street—or elsewhere—where all six have gathered. You are present.
                          Address them, pose a question, or introduce a topic. They converse and respond in character.
                        </p>
                        <span className="six-mode-btn">Enter room</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      className={`six-mode-card${activeCanonMode ? ' is-active' : ''}`}
                      onClick={handleSelectCanonMode}
                    >
                      <div className="six-mode-icon" aria-hidden="true">
                        <img src={sherlockWatsonImg} alt="" className="six-mode-illustration" />
                      </div>
                      <div className="six-mode-body">
                        <div className="six-mode-title">Interactive canon mode</div>
                        <p className="six-mode-summary">
                          Ask questions directly about the Sherlock Holmes canon. RAG-powered Q&A.
                        </p>
                        <span className="six-mode-btn">Ask the canon</span>
                      </div>
                    </button>
                  </div>
                </section>
              ) : (
                <>
                  <section className="character-panel" aria-label="Character selection">
                    <h2 className="section-heading">
                      Whom will you <span>consult</span>?
                    </h2>
                    <p className="section-lead">
                      These are not modern avatars but preserved correspondents. Select one to open a
                      private exchange in the case journal.
                    </p>
                    <div className="character-grid">
                      {CHARACTERS.map((character) => (
                        <button
                          key={character.key}
                          type="button"
                          className={`character-card${
                            activeKey === character.key ? ' is-active' : ''
                          }`}
                          onClick={() => handleSelectCharacter(character)}
                        >
                          <div className="portrait-frame" aria-hidden="true">
                            <img
                              src={CHARACTER_IMAGES[character.key]}
                              alt=""
                              className="portrait-image"
                            />
                          </div>
                          <div className="character-body">
                            <div>
                              <div className="character-name">{character.name}</div>
                              <div className="character-title">{character.title}</div>
                            </div>
                            <p className="character-summary">{character.summary}</p>
                            <div className="character-footer">
                              <div className="character-meta">
                                Tone: <span>{character.tone}</span>
                              </div>
                              <span className="character-button">
                                <span>Consult</span>
                                <span>↗</span>
                              </span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </section>

                  <div className="archive-sidebar">
                    <aside className="ambient-panel" aria-label="Atmosphere and notes">
                    <div className="ambient-illustration">
                      <img src={atmosphericsImg} alt="" aria-hidden="true" />
                    </div>
                    <div className="ambient-header">
                      <div className="ambient-heading">Atmospherics</div>
                      <div className="ambient-tagline">Fog, ink, and deduction</div>
                    </div>
                    <div className="ambient-body">
                      <p className="ambient-quote">
                        “You know my methods,” Holmes once remarked. “Apply them.” What follows is a
                        record of such applications—annotated, cross‑referenced, and kept from the
                        vulgar eye.
                      </p>
                      <div>
                        <div className="ambient-list-label">Within these rooms</div>
                        <ul className="ambient-list">
                          <li>A lamplit desk, paper weighted by a service revolver.</li>
                          <li>The murmur of London outside, dim through the fog.</li>
                          <li>
                            Marginalia in a familiar hand: deductions, doubts, and sudden, precise
                            conclusions.
                          </li>
                        </ul>
                      </div>
                      <p className="ambient-footnote">
                        <strong>Note.</strong> This interface is not a chat window but a viewing slit
                        into an orderly chaos of cases, reconstructed for your private consultation.
                      </p>
                    </div>
                  </aside>

                  <section className="six-mode-panel" aria-label="Archive experiences">
                    <h3 className="six-mode-heading">Archive experiences</h3>
                    <p className="six-mode-lead">
                      Six-character stories, chatroom, or direct canon Q&A.
                    </p>
                    <div className="six-mode-grid">
                      <button
                        type="button"
                        className={`six-mode-card${activeSixMode === 'case_story' ? ' is-active' : ''}`}
                        onClick={() => handleSelectSixMode('case_story')}
                      >
                        <div className="six-mode-icon" aria-hidden="true">
                          <img src={sherlockWatsonImg} alt="" className="six-mode-illustration" />
                        </div>
                        <div className="six-mode-body">
                          <div className="six-mode-title">Case-based story</div>
                          <p className="six-mode-summary">
                            Choose a case or scenario—a theft, a disappearance, a cipher. We generate a story episode
                            involving all six characters, grounded in canon and woven into late Victorian London.
                          </p>
                          <span className="six-mode-btn">Generate story</span>
                        </div>
                      </button>
                      <button
                        type="button"
                        className={`six-mode-card${activeSixMode === 'chatroom' ? ' is-active' : ''}`}
                        onClick={() => handleSelectSixMode('chatroom')}
                      >
                        <div className="six-mode-icon" aria-hidden="true">
                          <img src={fullCastImg} alt="" className="six-mode-illustration" />
                        </div>
                        <div className="six-mode-body">
                          <div className="six-mode-title">Character chatroom</div>
                          <p className="six-mode-summary">
                            Imagine a room at Baker Street—or elsewhere—where all six have gathered. You are present.
                            Address them, pose a question, or introduce a topic. They converse and respond in character.
                          </p>
                          <span className="six-mode-btn">Enter room</span>
                        </div>
                      </button>
                      <button
                        type="button"
                        className={`six-mode-card${activeCanonMode ? ' is-active' : ''}`}
                        onClick={handleSelectCanonMode}
                      >
                        <div className="six-mode-icon" aria-hidden="true">
                          <img src={sherlockWatsonImg} alt="" className="six-mode-illustration" />
                        </div>
                        <div className="six-mode-body">
                          <div className="six-mode-title">Interactive canon mode</div>
                          <p className="six-mode-summary">
                            Ask questions directly about the Sherlock Holmes canon. RAG-powered Q&A over the indexed stories.
                          </p>
                          <span className="six-mode-btn">Ask the canon</span>
                        </div>
                      </button>
                    </div>
                  </section>
                  </div>
                </>
              )}
            </section>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="archive-shell">
      <div className="archive-inner archive-inner--chat">
        <aside className="sidebar-card" aria-label="Character details">
          <div className="sidebar-portrait">
            <img
              src={CHARACTER_IMAGES[activeCharacter.key]}
              alt=""
              aria-hidden="true"
            />
          </div>
          <div className="sidebar-header">
            <div className="sidebar-title">
              <div className="sidebar-label">Consulting correspondent</div>
              <div className="sidebar-character-name">{activeCharacter.name}</div>
            </div>
            <button
              type="button"
              className="sidebar-back"
              onClick={handleReturnToArchive}
              aria-label="Exit and return to the main archives"
            >
              <span>←</span>
              <span>Exit</span>
            </button>
          </div>
          <div className="sidebar-meta">
            <strong>{activeCharacter.title}</strong>
            <br />
            {activeCharacter.summary}
          </div>
          {!isApiConfigured && (
            <div className="sidebar-note">
              API not connected. Replies use local mocks. Set VITE_GRADIO_SPACE (e.g. mutasim-rehman/appledoor) or VITE_API_BASE to connect.
            </div>
          )}
        </aside>

        <main className="chat-shell" aria-label="Case journal conversation">
          <header className="chat-header">
            <div>
              <div className="chat-heading">
                Case journal — <span>{activeCharacter.name}</span>
              </div>
              <div className="chat-subtitle">
                Record your query as you would dictate it for the record. Replies arrive as formal
                written response.
              </div>
            </div>
            <div className="chat-header-meta">
              Session mode: <strong>Character chat</strong>
              <br />
              Strictness: <strong>Strict canon</strong>
            </div>
          </header>

          <section ref={chatJournalRef} className="chat-journal" aria-label="Conversation log">
            {messages.map((message) => (
              <JournalEntry
                key={message.id}
                message={message}
                character={activeCharacter}
              />
            ))}
          </section>

          <form className="chat-input-row" onSubmit={handleSubmit}>
            <div className="chat-input">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Describe your difficulty as you would in a letter to Baker Street…"
                aria-label="Case entry"
              />
              <div className="chat-hint" data-hide-on-mobile>
                You may begin plainly: who you are, what has occurred, and what puzzles you most.
              </div>
            </div>
            <div>
              <button
                className="chat-submit"
                type="submit"
                disabled={!draft.trim() || isAwaitingReply}
                aria-label={isAwaitingReply ? 'Awaiting reply' : 'Dispatch entry'}
              >
                <span className="chat-submit__icon chat-submit__icon--desktop" aria-hidden>✉</span>
                <span className="chat-submit__icon chat-submit__icon--mobile" aria-hidden>→</span>
                <span className="chat-submit__label">Dispatch entry</span>
              </button>
              <div
                className="chat-status"
                data-hide-on-mobile={!isAwaitingReply ? '' : undefined}
              >
                {isAwaitingReply
                  ? `Awaiting ${activeCharacter.name.split(' ')[0]}’s written reply…`
                  : isApiConfigured
                    ? 'Replies are generated by the RAG backend and grounded in canon.'
                    : 'API not connected. Replies use local mocks.'}
              </div>
            </div>
          </form>
        </main>
      </div>
    </div>
  )
}

export default App
