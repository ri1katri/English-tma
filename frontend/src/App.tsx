import { useEffect, useState } from 'react'
import type {
  DashboardStats,
  SystemDictionaryDetail,
  SystemDictionarySummary,
  UserDictionaryDetail,
  UserDictionarySummary,
  WordSearchResult,
} from './types'

const API_BASE = 'https://english-tma-api.onrender.com'

interface LearningQuestion {
  question_id: string
  word_id: string
  exercise_type: string
  prompt_main: string
  prompt_sub?: string | null
  options: string[]
}

interface PlacementQuestion {
  id: number
  word: string
  level: string
  question: string
  options: string[]
}

interface PlacementResult {
  score: number
  total: number
  cefr_level: string
  recommended_dictionary_id?: string
  recommended_dictionary_title?: string
}

export default function App() {
  const [tab, setTab] = useState<'search' | 'learning' | 'my' | 'catalog'>('search')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WordSearchResult | null>(null)
  const [notFoundQuery, setNotFoundQuery] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [dashboard, setDashboard] = useState<DashboardStats | null>(null)
  const [userLevel, setUserLevel] = useState<string | null>(null)

  const [myDictionaries, setMyDictionaries] = useState<UserDictionarySummary[]>([])
  const [catalog, setCatalog] = useState<SystemDictionarySummary[]>([])
  const [selectedMyDict, setSelectedMyDict] = useState<UserDictionaryDetail | null>(null)
  const [selectedSysDict, setSelectedSysDict] = useState<SystemDictionaryDetail | null>(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [wordToAdd, setWordToAdd] = useState<WordSearchResult | null>(null)
  const [newDictTitle, setNewDictTitle] = useState('')

  // Состояние сессии обучения («Учить»)
  const [learningQuestions, setLearningQuestions] = useState<LearningQuestion[]>([])
  const [currentLearnIdx, setCurrentLearnIdx] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [isAnswerChecked, setIsAnswerChecked] = useState(false)
  const [isAnswerCorrect, setIsAnswerCorrect] = useState<boolean | null>(null)
  const [correctAnswerText, setCorrectAnswerText] = useState<string>('')
  const [learningScore, setLearningScore] = useState(0)
  const [isLearnFinished, setIsLearnFinished] = useState(false)

  // Placement Test
  const [isTesting, setIsTesting] = useState(false)
  const [testQuestions, setTestQuestions] = useState<PlacementQuestion[]>([])
  const [currentQIndex, setCurrentQIndex] = useState(0)
  const [testAnswers, setTestAnswers] = useState<Record<number, string>>({})
  const [testResult, setTestResult] = useState<PlacementResult | null>(null)

  const getHeaders = (): Record<string, string> => {
    const tgInit = (window as any).Telegram?.WebApp?.initData
    return {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': tgInit || 'demo_mode',
    }
  }

  const loadDashboard = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/users/me/dashboard`, { headers: getHeaders() })
      if (res.ok) {
        const data = await res.json()
        setDashboard(data)
        if (data.cefr_level) setUserLevel(data.cefr_level)
      }
    } catch {}
  }

  const loadDictionaries = async () => {
    try {
      const [resMy, resSys] = await Promise.all([
        fetch(`${API_BASE}/api/v1/dictionaries`, { headers: getHeaders() }),
        fetch(`${API_BASE}/api/v1/system-dictionaries`, { headers: getHeaders() }),
      ])
      if (resMy.ok) setMyDictionaries(await resMy.json())
      if (resSys.ok) setCatalog(await resSys.json())
    } catch {}
  }

  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
    }
    loadDashboard()
    loadDictionaries()
  }, [])

  // Поиск слова
  const handleSearch = async (searchWord?: string) => {
    const target = (searchWord !== undefined ? searchWord : query).trim()
    if (!target) return

    setLoading(true)
    setError(null)
    setNotFoundQuery(null)
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/api/v1/words/search?query=${encodeURIComponent(target)}`, {
        headers: getHeaders(),
      })
      if (!res.ok) {
        // Бэкенд отвечает { detail: { code, message } }: по code отличаем
        // «слово не найдено» от «словарный сервис временно недоступен».
        let code: string | null = null
        try {
          const body = await res.json()
          code = body?.detail?.code ?? null
        } catch {
          code = null
        }
        if (code === 'word_not_found') {
          setNotFoundQuery(target)
        } else if (code === 'provider_unavailable') {
          setError('Словарный сервис временно недоступен. Попробуйте ещё раз через минуту.')
        } else if (code === 'invalid_input') {
          setError('Введите одно английское слово латинскими буквами.')
        } else {
          throw new Error(`Ошибка: ${res.status}`)
        }
      } else {
        const data: WordSearchResult = await res.json()
        setResult(data)
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка соединения с сервером')
    } finally {
      setLoading(false)
    }
  }

  // Запуск сессии обучения
  const startLearning = async (dictionaryId?: string) => {
    setLoading(true)
    setError(null)
    setIsLearnFinished(false)
    setCurrentLearnIdx(0)
    setLearningScore(0)
    setSelectedAnswer(null)
    setIsAnswerChecked(false)
    setIsAnswerCorrect(null)

    try {
      const url = dictionaryId
        ? `${API_BASE}/api/v1/learning/session?dictionary_id=${dictionaryId}&limit=6`
        : `${API_BASE}/api/v1/learning/session?limit=6`
      const res = await fetch(url, { headers: getHeaders() })
      if (res.ok) {
        const data = await res.json()
        if (!data.questions || data.questions.length === 0) {
          alert('В словаре пока нет слов для изучения. Добавьте слова через Поиск или Каталог!')
        } else {
          setLearningQuestions(data.questions)
          setTab('learning')
        }
      } else {
        alert('Не удалось загрузить тренировку')
      }
    } catch {
      alert('Ошибка соединения при запуске тренировки')
    } finally {
      setLoading(false)
    }
  }

  const handleCheckAnswer = async (selected: string) => {
    if (isAnswerChecked) return
    setSelectedAnswer(selected)
    const currentQ = learningQuestions[currentLearnIdx]

    try {
      const res = await fetch(`${API_BASE}/api/v1/learning/submit-answer`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          word_id: currentQ.word_id,
          selected_answer: selected,
          exercise_type: currentQ.exercise_type,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setIsAnswerCorrect(data.is_correct)
        setCorrectAnswerText(data.correct_answer)
        if (data.is_correct) {
          setLearningScore((s) => s + 1)
        }
        setIsAnswerChecked(true)
        loadDashboard()
      }
    } catch {
      alert('Ошибка сохранения ответа')
    }
  }

  const handleNextLearnQuestion = () => {
    if (currentLearnIdx + 1 < learningQuestions.length) {
      setCurrentLearnIdx((i) => i + 1)
      setSelectedAnswer(null)
      setIsAnswerChecked(false)
      setIsAnswerCorrect(null)
    } else {
      setIsLearnFinished(true)
    }
  }

  // Создание словаря
  const handleCreateAndAdd = async (dictTitle: string) => {
    if (!dictTitle.trim()) return
    try {
      const createRes = await fetch(`${API_BASE}/api/v1/dictionaries`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ title: dictTitle.trim() }),
      })
      if (!createRes.ok) {
        const errJson = await createRes.json().catch(() => ({}))
        alert(errJson.detail || 'Не удалось создать словарь')
        return
      }
      const newDict = await createRes.json()
      if (wordToAdd) {
        await handleAddWordToDict(newDict.id)
      }
      setNewDictTitle('')
      await loadDictionaries()
      await loadDashboard()
    } catch {
      alert('Ошибка при создании словаря')
    }
  }

  const handleAddWordToDict = async (dictId: string) => {
    if (!wordToAdd) return
    try {
      const res = await fetch(`${API_BASE}/api/v1/dictionaries/${dictId}/words`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ word_id: wordToAdd.id }),
      })
      if (res.ok) {
        setShowAddModal(false)
        setWordToAdd(null)
        loadDictionaries()
        loadDashboard()
      } else {
        alert('Слово уже находится в этом словаре')
      }
    } catch {
      alert('Не удалось добавить слово')
    }
  }

  // Тестирование уровня
  const startTest = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/v1/placement/test`, { headers: getHeaders() })
      if (res.ok) {
        const data = await res.json()
        setTestQuestions(data.questions)
        setCurrentQIndex(0)
        setTestAnswers({})
        setTestResult(null)
        setIsTesting(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleAnswerTest = (answer: string) => {
    const q = testQuestions[currentQIndex]
    const nextAnswers = { ...testAnswers, [q.id]: answer }
    setTestAnswers(nextAnswers)

    if (currentQIndex + 1 < testQuestions.length) {
      setCurrentQIndex(currentQIndex + 1)
    } else {
      finishTest(nextAnswers)
    }
  }

  const finishTest = async (finalAnswers: Record<number, string>) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/placement/submit`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ answers: finalAnswers }),
      })
      if (res.ok) {
        const resultData: PlacementResult = await res.json()
        setTestResult(resultData)
        setUserLevel(resultData.cefr_level)
        loadDashboard()
      } else {
        alert('Ошибка при сохранении результатов теста')
      }
    } finally {
      setLoading(false)
    }
  }

  const copyRecommendedDict = async (dictId?: string) => {
    if (!dictId) return
    try {
      const res = await fetch(`${API_BASE}/api/v1/system-dictionaries/${dictId}/copy`, {
        method: 'POST',
        headers: getHeaders(),
      })
      if (res.ok) {
        setIsTesting(false)
        setTestResult(null)
        await loadDictionaries()
        setTab('my')
      }
    } catch {}
  }

  const openSystemDict = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/system-dictionaries/${id}`, { headers: getHeaders() })
      if (res.ok) setSelectedSysDict(await res.json())
    } catch {}
  }

  const openMyDict = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dictionaries/${id}`, { headers: getHeaders() })
      if (res.ok) setSelectedMyDict(await res.json())
    } catch {}
  }

  const currentLearnQ = learningQuestions[currentLearnIdx]

  return (
    <div className="app-container">
      {/* Шапка с дашбордом */}
      {!isTesting && (
        <div className="dashboard-banner">
          <div className="banner-top" onClick={startTest} style={{ cursor: 'pointer' }}>
            <span>🎯 Уровень: <b>{userLevel ? `${userLevel}` : 'Не определен (Пройти тест)'}</b></span>
            <span>➔</span>
          </div>
          <div className="dashboard-stats">
            <div><b>{dashboard?.total_words_in_dicts || 0}</b> в словарях</div>
            <div><b>{dashboard?.words_learning || 0}</b> учу</div>
            <div><b>{dashboard?.words_mastered || 0}</b> выучено</div>
          </div>
        </div>
      )}

      {/* Режим Placement Test */}
      {isTesting && (
        <div className="test-container">
          {!testResult ? (
            <div>
              <div className="test-header">
                <span>Вопрос {currentQIndex + 1} из {testQuestions.length}</span>
                <span className="badge-level">{testQuestions[currentQIndex]?.level}</span>
              </div>
              <h2 className="test-word">{testQuestions[currentQIndex]?.word}</h2>
              <p className="test-prompt">{testQuestions[currentQIndex]?.question}</p>

              <div className="test-options">
                {testQuestions[currentQIndex]?.options.map((opt, i) => (
                  <button key={i} className="test-opt-btn" onClick={() => handleAnswerTest(opt)}>
                    {opt}
                  </button>
                ))}
              </div>
              <button className="btn-cancel" onClick={() => setIsTesting(false)}>Прервать тест</button>
            </div>
          ) : (
            <div className="test-result-box">
              <div className="result-badge">{testResult.cefr_level}</div>
              <h2>Твой уровень: {testResult.cefr_level}! 🎉</h2>
              <p style={{ margin: '8px 0', color: 'var(--text-muted)' }}>
                Правильных ответов: {testResult.score} из {testResult.total}
              </p>

              {testResult.recommended_dictionary_id && (
                <button
                  className="search-btn"
                  style={{ width: '100%', marginTop: '16px' }}
                  onClick={() => copyRecommendedDict(testResult.recommended_dictionary_id)}
                >
                  📥 Добавить словарь «{testResult.recommended_dictionary_title}»
                </button>
              )}
              <button
                className="btn-cancel"
                style={{ marginTop: '10px' }}
                onClick={() => { setIsTesting(false); setTestResult(null) }}
              >
                В главное меню
              </button>
            </div>
          )}
        </div>
      )}

      {/* Навигация вкладок */}
      {!isTesting && (
        <div className="nav-tabs">
          <button className={`nav-btn ${tab === 'search' ? 'active' : ''}`} onClick={() => setTab('search')}>
            🔍 Поиск
          </button>
          <button className={`nav-btn ${tab === 'learning' ? 'active' : ''}`} onClick={() => startLearning()}>
            🎓 Учить
          </button>
          <button className={`nav-btn ${tab === 'my' ? 'active' : ''}`} onClick={() => { setTab('my'); setSelectedMyDict(null) }}>
            📚 Мои ({myDictionaries.length})
          </button>
          <button className={`nav-btn ${tab === 'catalog' ? 'active' : ''}`} onClick={() => { setTab('catalog'); setSelectedSysDict(null) }}>
            🌟 Каталог ({catalog.length})
          </button>
        </div>
      )}

      {/* Вкладка 1: Поиск */}
      {!isTesting && tab === 'search' && (
        <div>
          <form className="search-form" onSubmit={(e) => { e.preventDefault(); handleSearch() }}>
            <input
              type="text"
              className="search-input"
              placeholder="Введите любое английское слово..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className="search-btn" disabled={loading}>Найти</button>
          </form>

          <div className="hints">
            <span>Попробуйте:</span>
            <span className="hint-chip" onClick={() => { setQuery('apple'); handleSearch('apple') }}>apple</span>
            <span className="hint-chip" onClick={() => { setQuery('freedom'); handleSearch('freedom') }}>freedom</span>
            <span className="hint-chip" onClick={() => { setQuery('soul'); handleSearch('soul') }}>soul</span>
          </div>

          {loading && <div className="state-box"><div className="spinner"></div><p>Ищем слово...</p></div>}
          {error && <div className="state-box"><p style={{ color: 'var(--danger)' }}>{error}</p></div>}
          {notFoundQuery && <div className="state-box"><p>Слово «{notFoundQuery}» не найдено</p></div>}

          {result && (
            <div className="result-container">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 className="word-title">{result.word}</h2>
                <button
                  className="search-btn"
                  style={{ padding: '6px 14px', fontSize: '13px' }}
                  onClick={() => { setWordToAdd(result); setShowAddModal(true) }}
                >
                  + В словарь
                </button>
              </div>

              <div className="senses-list" style={{ marginTop: '12px' }}>
                {result.senses.map((s) => (
                  <div key={s.id} className="sense-card">
                    <div className="sense-top">
                      <span className="pos-badge">{s.part_of_speech}</span>
                      {s.transcription && <span className="transcription">{s.transcription}</span>}
                    </div>
                    {s.translations_ru.length > 0 ? (
                      <div className="translations">{s.translations_ru.join(', ')}</div>
                    ) : (
                      <div style={{ fontSize: '13px', opacity: 0.6, margin: '4px 0' }}>
                        Русский перевод пока недоступен
                      </div>
                    )}
                    <div className="definition">{s.definition_en}</div>
                    {s.synonyms.length > 0 && (
                      <div style={{ fontSize: '13px', opacity: 0.75, marginTop: '4px' }}>
                        Synonyms: {s.synonyms.join(', ')}
                      </div>
                    )}
                    {s.example_en && (
                      <div className="example-box">
                        <div className="example-en">“{s.example_en}”</div>
                        {s.example_ru && <div className="example-ru">{s.example_ru}</div>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Вкладка 2: Учить (Learning Engine) */}
      {!isTesting && tab === 'learning' && (
        <div>
          {loading && <div className="state-box"><div className="spinner"></div><p>Загрузка сессии...</p></div>}

          {!loading && isLearnFinished && (
            <div className="test-result-box" style={{ background: '#fff', borderRadius: '14px', padding: '24px 16px' }}>
              <h2>Сессия завершена! 🎉</h2>
              <p style={{ margin: '10px 0', fontSize: '16px' }}>
                Правильно: <b>{learningScore}</b> из <b>{learningQuestions.length}</b>
              </p>
              <button className="search-btn" style={{ width: '100%', marginTop: '12px' }} onClick={() => startLearning()}>
                Учить ещё раз
              </button>
              <button className="btn-cancel" style={{ marginTop: '8px' }} onClick={() => setTab('search')}>
                В меню
              </button>
            </div>
          )}

          {!loading && !isLearnFinished && currentLearnQ && (
            <div className="test-container">
              <div className="test-header">
                <span>Вопрос {currentLearnIdx + 1} из {learningQuestions.length}</span>
                <span className="badge-level">Тренировка</span>
              </div>

              <h2 className="test-word">{currentLearnQ.prompt_main}</h2>
              {currentLearnQ.prompt_sub && (
                <p className="test-prompt">{currentLearnQ.prompt_sub}</p>
              )}

              <div className="test-options" style={{ marginTop: '14px' }}>
                {currentLearnQ.options.map((opt, i) => {
                  let btnBg = '#f4f4f7'
                  let borderCol = 'var(--border)'

                  if (isAnswerChecked) {
                    if (opt === correctAnswerText) {
                      btnBg = '#d1fae5'
                      borderCol = 'var(--accent-green)'
                    } else if (opt === selectedAnswer) {
                      btnBg = '#fee2e2'
                      borderCol = 'var(--danger)'
                    }
                  }

                  return (
                    <button
                      key={i}
                      className="test-opt-btn"
                      disabled={isAnswerChecked}
                      style={{ background: btnBg, borderColor: borderCol }}
                      onClick={() => handleCheckAnswer(opt)}
                    >
                      {opt}
                    </button>
                  )
                })}
              </div>

              {isAnswerChecked && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{
                    padding: '10px',
                    borderRadius: '10px',
                    textAlign: 'center',
                    fontWeight: 600,
                    background: isAnswerCorrect ? '#d1fae5' : '#fee2e2',
                    color: isAnswerCorrect ? '#065f46' : '#991b1b',
                    marginBottom: '12px'
                  }}>
                    {isAnswerCorrect ? 'Отлично! Верный ответ 👍' : `Ошибка! Правильно: ${correctAnswerText}`}
                  </div>
                  <button className="search-btn" style={{ width: '100%' }} onClick={handleNextLearnQuestion}>
                    {currentLearnIdx + 1 < learningQuestions.length ? 'Следующий вопрос ➔' : 'Завершить тренировку'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Вкладка 3: Мои словари */}
      {!isTesting && tab === 'my' && (
        <div>
          {!selectedMyDict ? (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Новый словарь (напр. Book)"
                  value={newDictTitle}
                  onChange={(e) => setNewDictTitle(e.target.value)}
                />
                <button className="search-btn" onClick={() => handleCreateAndAdd(newDictTitle)}>Создать</button>
              </div>
              <div className="dict-list">
                {myDictionaries.length === 0 ? (
                  <div className="state-box"><p>У вас пока нет словарей. Создайте первый!</p></div>
                ) : (
                  myDictionaries.map((d) => (
                    <div key={d.id} className="dict-card" onClick={() => openMyDict(d.id)}>
                      <div>
                        <h3>{d.title}</h3>
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{d.words_count} слов</p>
                      </div>
                      <span>Открыть ➔</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <button className="btn-cancel" style={{ textAlign: 'left', width: 'auto', padding: '6px 0' }} onClick={() => setSelectedMyDict(null)}>
                  ← Назад к словарям
                </button>
                <button
                  className="search-btn"
                  style={{ padding: '6px 12px', fontSize: '13px' }}
                  onClick={() => startLearning(selectedMyDict.id)}
                >
                  🎓 Учить этот словарь
                </button>
              </div>
              <h2 style={{ marginBottom: '12px' }}>{selectedMyDict.title}</h2>
              <div className="senses-list">
                {selectedMyDict.words.map((w) => (
                  <div key={w.id} className="sense-card">
                    <b>{w.word}</b>
                    <div style={{ color: 'var(--primary)', fontWeight: 600 }}>
                      {w.senses[0]?.translations_ru.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Вкладка 4: Каталог */}
      {!isTesting && tab === 'catalog' && (
        <div>
          {!selectedSysDict ? (
            <div className="dict-list">
              {catalog.map((c) => (
                <div key={c.id} className="dict-card" onClick={() => openSystemDict(c.id)}>
                  <div>
                    <span className="badge-level">{c.target_level || 'ALL'}</span>
                    <h3 style={{ margin: '4px 0' }}>{c.title}</h3>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{c.description}</p>
                  </div>
                  <span>{c.words_count} слов ➔</span>
                </div>
              ))}
            </div>
          ) : (
            <div>
              <button className="btn-cancel" style={{ textAlign: 'left', marginBottom: '8px' }} onClick={() => setSelectedSysDict(null)}>
                ← В каталог
              </button>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h2>{selectedSysDict.title}</h2>
                <button className="search-btn" onClick={() => copyRecommendedDict(selectedSysDict.id)}>
                  📥 Сохранить себе
                </button>
              </div>
              <div className="senses-list">
                {selectedSysDict.words.map((w) => (
                  <div key={w.id} className="sense-card">
                    <b>{w.word}</b> — {w.senses[0]?.translations_ru.join(', ')}
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {w.senses[0]?.definition_en}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Модальное окно добавления в словарь */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Добавить «{wordToAdd?.word}» в словарь</h3>
            <div className="dict-list" style={{ maxHeight: '180px', overflowY: 'auto', margin: '12px 0' }}>
              {myDictionaries.map((d) => (
                <div key={d.id} className="dict-card" style={{ padding: '10px' }} onClick={() => handleAddWordToDict(d.id)}>
                  <span>{d.title}</span>
                  <span style={{ fontSize: '12px' }}>Выбрать +</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                type="text"
                className="search-input"
                placeholder="Или имя нового словаря"
                value={newDictTitle}
                onChange={(e) => setNewDictTitle(e.target.value)}
              />
              <button className="search-btn" onClick={() => handleCreateAndAdd(newDictTitle)}>OK</button>
            </div>
            <button className="btn-cancel" style={{ marginTop: '10px' }} onClick={() => setShowAddModal(false)}>
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  )
}