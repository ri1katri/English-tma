import React, { useEffect, useState } from 'react'
import type {
  DashboardStats,
  ExerciseType,
  LearningCard,
  LearningSessionResponse,
  PlacementQuestion,
  PlacementResultResponse,
  PlacementTestResponse,
  SystemDictionaryDetail,
  SystemDictionarySummary,
  UserDictionaryDetail,
  UserDictionarySummary,
  UserProfile,
  WordProgress,
  WordSearchResult,
} from './types'

export default function App() {
  const [activeTab, setActiveTab] = useState<'search' | 'dictionaries' | 'catalog' | 'learning'>('search')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WordSearchResult | null>(null)
  const [notFoundQuery, setNotFoundQuery] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)

  // Дашборд аналитики
  const [dashboard, setDashboard] = useState<DashboardStats>({
    total_words_in_dicts: 0,
    words_new: 0,
    words_learning: 0,
    words_mastered: 0,
  })

  // Прогресс текущего слова
  const [currentWordProgress, setCurrentWordProgress] = useState<WordProgress | null>(null)

  // Словари
  const [dictionaries, setDictionaries] = useState<UserDictionarySummary[]>([])
  const [selectedDict, setSelectedDict] = useState<UserDictionaryDetail | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newDictTitle, setNewDictTitle] = useState('')
  const [modalSuccessMsg, setModalSuccessMsg] = useState<string | null>(null)

  // Каталог
  const [catalog, setCatalog] = useState<SystemDictionarySummary[]>([])
  const [selectedCatalog, setSelectedCatalog] = useState<SystemDictionaryDetail | null>(null)
  const [copying, setCopying] = useState(false)

  // Learning Engine State
  const [learningSession, setLearningSession] = useState<LearningCard[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [assembledTokens, setAssembledTokens] = useState<string[]>([])
  const [usedTokenIndices, setUsedTokenIndices] = useState<number[]>([])
  const [isAnswerChecked, setIsAnswerChecked] = useState(false)
  const [isCurrentCorrect, setIsCurrentCorrect] = useState<boolean | null>(null)
  const [score, setScore] = useState(0)
  const [isSessionFinished, setIsSessionFinished] = useState(false)

  // Placement Test State
  const [isTestingMode, setIsTestingMode] = useState(false)
  const [placementQuestions, setPlacementQuestions] = useState<PlacementQuestion[]>([])
  const [testIndex, setTestIndex] = useState(0)
  const [testAnswers, setTestAnswers] = useState<{ question_id: number; selected_option: string }[]>([])
  const [testResult, setTestResult] = useState<PlacementResultResponse | null>(null)

  const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined
  const initData = tg?.initData || ''

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (initData) {
      headers['X-Telegram-Init-Data'] = initData
    }
    return headers
  }

  const triggerHaptic = (type: 'success' | 'error') => {
    try {
      tg?.HapticFeedback?.notificationOccurred(type)
    } catch {
      // Игнорируем вне Telegram клиента
    }
  }

  useEffect(() => {
    if (tg) {
      tg.ready()
      tg.expand()
      if (initData) {
        fetch('/api/v1/auth/telegram', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ init_data: initData }),
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data: UserProfile | null) => {
            if (data) setUserProfile(data)
          })
          .catch((err) => console.error('Auth sync error:', err))
      }
    }
    loadDashboard()
    loadDictionaries()
    loadCatalog()
  }, [tg, initData])

  const loadDashboard = async () => {
    try {
      const res = await fetch('/api/v1/users/me/dashboard', { headers: getHeaders() })
      if (res.ok) {
        const data: DashboardStats = await res.json()
        setDashboard(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки дашборда:', err)
    }
  }

  const loadDictionaries = async () => {
    try {
      const res = await fetch('/api/v1/dictionaries', { headers: getHeaders() })
      if (res.ok) {
        const data: UserDictionarySummary[] = await res.json()
        setDictionaries(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки словарей:', err)
    }
  }

  const loadCatalog = async () => {
    try {
      const res = await fetch('/api/v1/system-dictionaries')
      if (res.ok) {
        const data: SystemDictionarySummary[] = await res.json()
        setCatalog(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки каталога:', err)
    }
  }

  const loadWordProgress = async (wordId: string) => {
    try {
      const res = await fetch(`/api/v1/words/${wordId}/progress`, { headers: getHeaders() })
      if (res.ok) {
        const data: WordProgress = await res.json()
        setCurrentWordProgress(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки прогресса слова:', err)
    }
  }

  const handleUpdateWordStatus = async (wordId: string, newStatus: 'new' | 'learning' | 'mastered') => {
    try {
      const res = await fetch(`/api/v1/words/${wordId}/progress`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        const data: WordProgress = await res.json()
        setCurrentWordProgress(data)
        await loadDashboard()
      }
    } catch (err) {
      console.error('Ошибка смены статуса слова:', err)
    }
  }

  // --- Learning Session Logic ---
  const startLearningSession = async (dictionaryId?: string) => {
    setLoading(true)
    setError(null)
    setIsSessionFinished(false)
    setCurrentIndex(0)
    setScore(0)
    setSelectedOption(null)
    setAssembledTokens([])
    setUsedTokenIndices([])
    setIsAnswerChecked(false)
    setIsCurrentCorrect(null)

    try {
      const url = dictionaryId
        ? `/api/v1/learning/session?dictionary_id=${dictionaryId}&limit=6`
        : `/api/v1/learning/session?limit=6`
      const res = await fetch(url, { headers: getHeaders() })
      if (res.ok) {
        const data: LearningSessionResponse = await res.json()
        setLearningSession(data.cards)
        setActiveTab('learning')
      } else {
        throw new Error('Не удалось сформировать сессию обучения')
      }
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Ошибка старта сессии')
    } finally {
      setLoading(false)
    }
  }

  const currentCard: LearningCard | undefined = learningSession[currentIndex]

  const handleCheckAnswer = async () => {
    if (!currentCard || isAnswerChecked) return

    let isCorrect = false

    if (currentCard.exercise_type === 'multiple_choice') {
      if (!selectedOption) return
      isCorrect = selectedOption === currentCard.target_answer
    } else if (currentCard.exercise_type === 'letter_scramble') {
      const assembledWord = assembledTokens.join('').toLowerCase()
      isCorrect = assembledWord === currentCard.target_answer.toLowerCase()
    } else if (currentCard.exercise_type === 'missing_letters') {
      let assembled = ''
      let tokenIdx = 0
      for (const ch of currentCard.prompt_main) {
        if (ch === '_') {
          assembled += assembledTokens[tokenIdx] || ''
          tokenIdx++
        } else {
          assembled += ch
        }
      }
      isCorrect = assembled.toLowerCase() === currentCard.target_answer.toLowerCase()
    } else if (currentCard.exercise_type === 'sentence_reorder') {
      const assembledSentence = assembledTokens.join(' ').toLowerCase()
      isCorrect = assembledSentence === currentCard.target_answer.toLowerCase()
    }

    setIsCurrentCorrect(isCorrect)
    setIsAnswerChecked(true)
    if (isCorrect) {
      setScore((s) => s + 1)
      triggerHaptic('success')
    } else {
      triggerHaptic('error')
    }

    try {
      await fetch('/api/v1/learning/submit-answer', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          word_id: currentCard.question_id,
          is_correct: isCorrect,
        }),
      })
      await loadDashboard()
    } catch (err) {
      console.error('Ошибка сохранения ответа:', err)
    }
  }

  const handleNextQuestion = () => {
    if (currentIndex + 1 < learningSession.length) {
      setCurrentIndex((i) => i + 1)
      setSelectedOption(null)
      setAssembledTokens([])
      setUsedTokenIndices([])
      setIsAnswerChecked(false)
      setIsCurrentCorrect(null)
    } else {
      setIsSessionFinished(true)
    }
  }

  const handleTokenClick = (token: string, tokenIndex: number) => {
    if (isAnswerChecked || usedTokenIndices.includes(tokenIndex)) return
    setAssembledTokens([...assembledTokens, token])
    setUsedTokenIndices([...usedTokenIndices, tokenIndex])
  }

  const handleRemoveToken = (indexToRemove: number) => {
    if (isAnswerChecked) return
    const tokenIndexInBank = usedTokenIndices[indexToRemove]
    setAssembledTokens(assembledTokens.filter((_, idx) => idx !== indexToRemove))
    setUsedTokenIndices(usedTokenIndices.filter((idx) => idx !== tokenIndexInBank))
  }

  // --- Placement Test Logic ---
  const startPlacementTest = async () => {
    setLoading(true)
    setTestResult(null)
    setTestIndex(0)
    setTestAnswers([])
    try {
      const res = await fetch('/api/v1/placement/test')
      if (res.ok) {
        const data: PlacementTestResponse = await res.json()
        setPlacementQuestions(data.questions)
        setIsTestingMode(true)
      }
    } catch (err) {
      console.error('Ошибка старта теста:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectTestOption = async (option: string) => {
    const q = placementQuestions[testIndex]
    const updatedAnswers = [...testAnswers, { question_id: q.id, selected_option: option }]
    setTestAnswers(updatedAnswers)

    if (testIndex + 1 < placementQuestions.length) {
      setTestIndex(testIndex + 1)
    } else {
      // Отправляем результат
      setLoading(true)
      try {
        const res = await fetch('/api/v1/placement/submit', {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ answers: updatedAnswers }),
        })
        if (res.ok) {
          const resultData: PlacementResultResponse = await res.json()
          setTestResult(resultData)
          if (userProfile) {
            setUserProfile({ ...userProfile, cefr_level: resultData.cefr_level })
          }
        }
      } catch (err) {
        console.error('Ошибка отправки результатов теста:', err)
      } finally {
        setLoading(false)
      }
    }
  }

  const loadDictionaryDetail = async (id: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/v1/dictionaries/${id}`, { headers: getHeaders() })
      if (res.ok) {
        const data: UserDictionaryDetail = await res.json()
        setSelectedDict(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки словаря:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadCatalogDetail = async (id: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/v1/system-dictionaries/${id}`)
      if (res.ok) {
        const data: SystemDictionaryDetail = await res.json()
        setSelectedCatalog(data)
      }
    } catch (err) {
      console.error('Ошибка загрузки системного словаря:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCopySystemDict = async (id: string) => {
    setCopying(true)
    try {
      const res = await fetch(`/api/v1/system-dictionaries/${id}/copy`, {
        method: 'POST',
        headers: getHeaders(),
      })
      if (res.ok) {
        await loadDictionaries()
        await loadDashboard()
        setSelectedCatalog(null)
        setIsTestingMode(false)
        setActiveTab('dictionaries')
      } else {
        alert('Не удалось скопировать словарь')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setCopying(false)
    }
  }

  const handleCreateDictionary = async () => {
    if (!newDictTitle.trim()) return
    try {
      const res = await fetch('/api/v1/dictionaries', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ title: newDictTitle.trim() }),
      })
      if (res.ok) {
        setNewDictTitle('')
        await loadDictionaries()
      } else {
        const err = await res.json()
        alert(err.detail || 'Не удалось создать словарь')
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleAddWordToDict = async (dictId: string) => {
    if (!result) return
    try {
      const res = await fetch(`/api/v1/dictionaries/${dictId}/words`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ word_id: result.id }),
      })
      if (res.ok) {
        setModalSuccessMsg('Слово добавлено!')
        setTimeout(() => {
          setModalSuccessMsg(null)
          setShowAddModal(false)
        }, 1200)
        await loadDictionaries()
        await loadDashboard()
        await loadWordProgress(result.id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleDeleteWordFromDict = async (dictId: string, wordId: string) => {
    try {
      const res = await fetch(`/api/v1/dictionaries/${dictId}/words/${wordId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (res.ok) {
        if (selectedDict) {
          setSelectedDict({
            ...selectedDict,
            words: selectedDict.words.filter((w) => w.id !== wordId),
          })
        }
        await loadDictionaries()
        await loadDashboard()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleSearch = async (searchWord?: string) => {
    const target = (searchWord !== undefined ? searchWord : query).trim()
    if (!target) return

    setLoading(true)
    setError(null)
    setNotFoundQuery(null)
    setResult(null)
    setCurrentWordProgress(null)

    try {
      const response = await fetch(
        `/api/v1/words/search?query=${encodeURIComponent(target)}`,
        { headers: getHeaders() }
      )

      if (response.status === 404) {
        setNotFoundQuery(target)
      } else if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`)
      } else {
        const data: WordSearchResult = await response.json()
        setResult(data)
        await loadWordProgress(data.id)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Не удалось связаться с сервером')
    } finally {
      setLoading(false)
    }
  }

  const getExerciseBadgeText = (type: ExerciseType) => {
    switch (type) {
      case 'multiple_choice':
        return '🎯 Выбор перевода'
      case 'letter_scramble':
        return '🔤 Сборка слова'
      case 'missing_letters':
        return '🧩 Пропущенные буквы'
      case 'sentence_reorder':
        return '📝 Порядок слов'
    }
  }

  return (
    <div className="app-container">
      {/* Шапка с пользователем и уровнем CEFR */}
      <div className="user-banner-row">
        <span>{userProfile ? `Привет, ${userProfile.first_name}! 👋` : ''}</span>
        {userProfile?.cefr_level && (
          <span className="level-badge">Уровень: {userProfile.cefr_level}</span>
        )}
      </div>

      {/* Экран прохождения Placement Test */}
      {isTestingMode ? (
        <div className="learning-screen">
          {loading && (
            <div className="state-box">
              <div className="spinner"></div>
              <p className="state-desc">Загрузка теста...</p>
            </div>
          )}

          {!loading && testResult && (
            <div className="state-box">
              <h2 style={{ fontSize: '24px' }}>Тест завершён! 🚀</h2>
              <div
                className="level-badge"
                style={{ fontSize: '18px', padding: '6px 14px', margin: '8px 0' }}
              >
                {testResult.level_title}
              </div>
              <p className="state-desc" style={{ fontSize: '15px' }}>
                {testResult.description}
              </p>
              <p style={{ color: 'var(--tg-hint)', fontSize: '13px' }}>
                Правильных ответов: {testResult.score} из {testResult.total}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%', marginTop: '14px' }}>
                {testResult.recommended_dictionary_id && (
                  <button
                    className="btn-primary"
                    onClick={() => handleCopySystemDict(testResult.recommended_dictionary_id!)}
                  >
                    📥 Добавить словарь уровня {testResult.cefr_level}
                  </button>
                )}
                <button
                  className="btn-secondary"
                  onClick={() => setIsTestingMode(false)}
                >
                  В главное меню
                </button>
              </div>
            </div>
          )}

          {!loading && !testResult && placementQuestions.length > 0 && (
            <>
              <div className="learning-progress-bar-bg">
                <div
                  className="learning-progress-bar-fill"
                  style={{
                    width: `${((testIndex + 1) / placementQuestions.length) * 100}%`,
                  }}
                ></div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--tg-hint)' }}>
                <span>Вопрос {testIndex + 1} из {placementQuestions.length}</span>
                <span className="level-badge">{placementQuestions[testIndex].level}</span>
              </div>

              <div className="quiz-card">
                <div className="prompt-main">{placementQuestions[testIndex].word}</div>
                <div className="prompt-sub">{placementQuestions[testIndex].prompt}</div>

                <div className="options-grid">
                  {placementQuestions[testIndex].options.map((opt, i) => (
                    <button
                      key={i}
                      className="option-btn"
                      onClick={() => handleSelectTestOption(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <button
                className="btn-secondary"
                style={{ alignSelf: 'center' }}
                onClick={() => setIsTestingMode(false)}
              >
                Прервать тест
              </button>
            </>
          )}
        </div>
      ) : (
        <>
          {/* Баннер-приглашение пройти Placement Test */}
          {!userProfile?.cefr_level && (
            <div className="placement-banner" onClick={startPlacementTest}>
              <div>
                <div className="placement-banner-title">🎯 Определите свой уровень (A1–C2)</div>
                <div className="placement-banner-desc">Быстрый тест на 2 минуты для подбора словаря</div>
              </div>
              <span style={{ fontSize: '18px', color: '#2563eb' }}>➔</span>
            </div>
          )}

          {/* Сводный персональный дашборд */}
          <div className="dashboard-card">
            <div className="stat-item">
              <span className="stat-value">📚 {dashboard.total_words_in_dicts}</span>
              <span className="stat-label">В словарях</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">📖 {dashboard.words_learning}</span>
              <span className="stat-label">Учу</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">✅ {dashboard.words_mastered}</span>
              <span className="stat-label">Выучено</span>
            </div>
          </div>

          {/* Вкладки навигации */}
          <div className="tab-nav">
            <button
              className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('search')
                setSelectedDict(null)
                setSelectedCatalog(null)
                loadDashboard()
              }}
            >
              🔍 Поиск
            </button>
            <button
              className={`tab-btn ${activeTab === 'learning' ? 'active' : ''}`}
              onClick={() => startLearningSession()}
            >
              🎓 Учить
            </button>
            <button
              className={`tab-btn ${activeTab === 'dictionaries' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('dictionaries')
                setSelectedCatalog(null)
                loadDictionaries()
                loadDashboard()
              }}
            >
              📚 Мои ({dictionaries.length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'catalog' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('catalog')
                setSelectedDict(null)
                loadCatalog()
              }}
            >
              🌟 Каталог ({catalog.length})
            </button>
          </div>

          {activeTab === 'search' && (
            <>
              <form
                className="search-form"
                onSubmit={(e) => {
                  e.preventDefault()
                  handleSearch()
                }}
              >
                <input
                  type="text"
                  className="search-input"
                  placeholder="Введите английское слово..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  autoFocus
                />
                <button type="submit" className="search-btn" disabled={loading}>
                  Найти
                </button>
              </form>

              <div className="hints">
                <span>Попробуйте:</span>
                {['apple', 'run', 'set'].map((w) => (
                  <span
                    key={w}
                    className="hint-chip"
                    onClick={() => {
                      setQuery(w)
                      handleSearch(w)
                    }}
                  >
                    {w}
                  </span>
                ))}
              </div>

              {loading && (
                <div className="state-box">
                  <div className="spinner"></div>
                  <p className="state-desc">Ищем слово в словаре...</p>
                </div>
              )}

              {error && (
                <div className="state-box">
                  <p className="state-title" style={{ color: 'var(--danger)' }}>
                    Ошибка соединения
                  </p>
                  <p className="state-desc">{error}</p>
                  <button className="search-btn" onClick={() => handleSearch()}>
                    Повторить
                  </button>
                </div>
              )}

              {notFoundQuery && (
                <div className="state-box">
                  <p className="state-title">Слово не найдено</p>
                  <p className="state-desc">
                    Слово <b>«{notFoundQuery}»</b> пока отсутствует в словаре.
                  </p>
                </div>
              )}

              {result && (
                <div className="result-container">
                  <div className="word-header-row">
                    <div>
                      <h2 className="word-title">{result.word}</h2>
                      {currentWordProgress && (
                        <span
                          className={`status-badge status-${currentWordProgress.status}`}
                          style={{ marginTop: '4px', display: 'inline-block' }}
                        >
                          {currentWordProgress.status === 'mastered'
                            ? 'Выучено'
                            : currentWordProgress.status === 'learning'
                            ? 'Изучается'
                            : 'Новое'}
                        </span>
                      )}
                    </div>

                    <div className="action-buttons">
                      {currentWordProgress?.status !== 'mastered' ? (
                        <button
                          className="btn-secondary"
                          onClick={() => handleUpdateWordStatus(result.id, 'mastered')}
                        >
                          ✓ Выучено
                        </button>
                      ) : (
                        <button
                          className="btn-secondary"
                          onClick={() => handleUpdateWordStatus(result.id, 'learning')}
                        >
                          📖 В изучение
                        </button>
                      )}
                      <button
                        className="btn-secondary"
                        onClick={() => setShowAddModal(true)}
                      >
                        + В словарь
                      </button>
                    </div>
                  </div>

                  <div className="senses-list" style={{ marginTop: '14px' }}>
                    {result.senses.map((sense) => (
                      <div key={sense.id} className="sense-card">
                        <div className="sense-top">
                          <span className="pos-badge">{sense.part_of_speech}</span>
                          {sense.transcription && (
                            <span className="transcription">{sense.transcription}</span>
                          )}
                        </div>
                        <div className="translations">
                          {sense.translations_ru.join(', ')}
                        </div>
                        <div className="definition">{sense.definition_en}</div>
                        {sense.example_en && (
                          <div className="example-box">
                            <div className="example-en">“{sense.example_en}”</div>
                            {sense.example_ru && (
                              <div className="example-ru">{sense.example_ru}</div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === 'learning' && (
            <div className="learning-screen">
              {loading && (
                <div className="state-box">
                  <div className="spinner"></div>
                  <p className="state-desc">Подбираем упражнения...</p>
                </div>
              )}

              {/* Безопасная заглушка при 0 слов */}
              {!loading && learningSession.length === 0 && (
                <div className="state-box">
                  <p className="state-title">Нет слов для тренировки</p>
                  <p className="state-desc">
                    Добавьте слова из поиска или сохраните готовый словарь из каталога!
                  </p>
                  <button
                    className="btn-primary"
                    style={{ marginTop: '10px' }}
                    onClick={() => setActiveTab('catalog')}
                  >
                    🌟 Перейти в каталог
                  </button>
                </div>
              )}

              {!loading && isSessionFinished && (
                <div className="state-box">
                  <h2 style={{ fontSize: '24px' }}>Тренировка завершена! 🎉</h2>
                  <p className="state-desc" style={{ fontSize: '16px' }}>
                    Ваш результат: <b>{score}</b> из <b>{learningSession.length}</b> верно!
                  </p>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                    <button
                      className="btn-primary"
                      onClick={() => startLearningSession()}
                    >
                      Ещё раз
                    </button>
                    <button
                      className="btn-secondary"
                      onClick={() => setActiveTab('search')}
                    >
                      В меню
                    </button>
                  </div>
                </div>
              )}

              {!loading && !isSessionFinished && currentCard && (
                <>
                  <div className="learning-progress-bar-bg">
                    <div
                      className="learning-progress-bar-fill"
                      style={{
                        width: `${((currentIndex + 1) / learningSession.length) * 100}%`,
                      }}
                    ></div>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '13px',
                      color: 'var(--tg-hint)',
                    }}
                  >
                    <span>
                      Вопрос {currentIndex + 1} из {learningSession.length}
                    </span>
                    <span className="exercise-type-tag">
                      {getExerciseBadgeText(currentCard.exercise_type)}
                    </span>
                  </div>

                  <div className="quiz-card">
                    <div className="prompt-main">{currentCard.prompt_main}</div>
                    {currentCard.prompt_sub && (
                      <div className="prompt-sub">{currentCard.prompt_sub}</div>
                    )}

                    {currentCard.exercise_type === 'multiple_choice' && (
                      <div className="options-grid" style={{ marginTop: '10px' }}>
                        {currentCard.options.map((opt, idx) => {
                          let btnClass = 'option-btn'
                          if (isAnswerChecked) {
                            if (opt === currentCard.target_answer) {
                              btnClass += ' selected-correct'
                            } else if (opt === selectedOption) {
                              btnClass += ' selected-wrong'
                            }
                          } else if (selectedOption === opt) {
                            btnClass += ' selected-correct'
                          }
                          return (
                            <button
                              key={idx}
                              className={btnClass}
                              disabled={isAnswerChecked}
                              onClick={() => setSelectedOption(opt)}
                            >
                              {opt}
                            </button>
                          )
                        })}
                      </div>
                    )}

                    {(currentCard.exercise_type === 'letter_scramble' ||
                      currentCard.exercise_type === 'missing_letters' ||
                      currentCard.exercise_type === 'sentence_reorder') && (
                      <div style={{ marginTop: '12px' }}>
                        <div className="chips-assembly-area">
                          {assembledTokens.length === 0 ? (
                            <span style={{ color: 'var(--tg-hint)', fontSize: '13px' }}>
                              Нажимайте на элементы внизу, чтобы сложить ответ
                            </span>
                          ) : (
                            assembledTokens.map((tok, i) => (
                              <span
                                key={i}
                                className="chip-item"
                                onClick={() => handleRemoveToken(i)}
                              >
                                {tok} ✕
                              </span>
                            ))
                          )}
                        </div>

                        <div className="chips-bank">
                          {currentCard.tokens.map((tok, i) => {
                            const isUsed = usedTokenIndices.includes(i)
                            return (
                              <button
                                key={i}
                                className={`chip-item ${isUsed ? 'used' : ''}`}
                                disabled={isUsed || isAnswerChecked}
                                onClick={() => handleTokenClick(tok, i)}
                              >
                                {tok}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}

                    {isAnswerChecked && (
                      <div
                        className={`feedback-banner ${
                          isCurrentCorrect ? 'correct' : 'wrong'
                        }`}
                      >
                        {isCurrentCorrect
                          ? 'Правильно! Отличная работа 👍'
                          : `Неверно. Правильный ответ: ${currentCard.target_answer}`}
                      </div>
                    )}
                  </div>

                  {!isAnswerChecked ? (
                    <button
                      className="btn-primary"
                      onClick={handleCheckAnswer}
                    >
                      Проверить
                    </button>
                  ) : (
                    <button
                      className="btn-primary"
                      onClick={handleNextQuestion}
                    >
                      {currentIndex + 1 < learningSession.length ? 'Далее ➔' : 'Завершить'}
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {activeTab === 'dictionaries' && (
            <div>
              {!selectedDict ? (
                <div className="dict-list">
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="text"
                      className="search-input"
                      placeholder="Новый словарь..."
                      value={newDictTitle}
                      onChange={(e) => setNewDictTitle(e.target.value)}
                    />
                    <button
                      className="search-btn"
                      onClick={handleCreateDictionary}
                    >
                      Создать
                    </button>
                  </div>

                  {dictionaries.length === 0 ? (
                    <div className="state-box">
                      <p className="state-title">Нет словарей</p>
                      <p className="state-desc">
                        Создайте свой словарь или выберите готовый во вкладке «Каталог».
                      </p>
                    </div>
                  ) : (
                    dictionaries.map((dict) => (
                      <div
                        key={dict.id}
                        className="dict-card"
                        onClick={() => loadDictionaryDetail(dict.id)}
                      >
                        <div>
                          <div className="dict-title">{dict.title}</div>
                          <div className="dict-meta">{dict.words_count} слов(а)</div>
                        </div>
                        <span>➔</span>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '16px',
                    }}
                  >
                    <button
                      className="btn-secondary"
                      onClick={() => setSelectedDict(null)}
                    >
                      ← Назад к спискам
                    </button>
                    <button
                      className="btn-primary"
                      style={{ padding: '8px 14px', fontSize: '13px' }}
                      onClick={() => startLearningSession(selectedDict.id)}
                    >
                      🎓 Учить этот словарь
                    </button>
                  </div>

                  <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>
                    {selectedDict.title}
                  </h3>

                  {selectedDict.words.length === 0 ? (
                    <div className="state-box">
                      <p className="state-desc">В этом словаре пока нет слов.</p>
                    </div>
                  ) : (
                    <div className="senses-list">
                      {selectedDict.words.map((w) => (
                        <div key={w.id} className="sense-card">
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <h4 style={{ fontSize: '18px', textTransform: 'capitalize' }}>
                              {w.word}
                            </h4>
                            <button
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--danger)',
                                cursor: 'pointer',
                                fontSize: '13px',
                              }}
                              onClick={() => handleDeleteWordFromDict(selectedDict.id, w.id)}
                            >
                              Удалить
                            </button>
                          </div>
                          <div className="translations">
                            {w.senses[0]?.translations_ru.join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'catalog' && (
            <div>
              {!selectedCatalog ? (
                <div className="dict-list">
                  {catalog.map((pack) => (
                    <div
                      key={pack.id}
                      className="dict-card"
                      onClick={() => loadCatalogDetail(pack.id)}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="dict-title">{pack.title}</span>
                          {pack.target_level && (
                            <span className="level-badge">{pack.target_level}</span>
                          )}
                        </div>
                        <div className="dict-meta">{pack.description}</div>
                        <div className="dict-meta" style={{ fontWeight: 600 }}>
                          {pack.words_count} слов(а)
                        </div>
                      </div>
                      <span>➔</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '16px',
                    }}
                  >
                    <button
                      className="btn-secondary"
                      onClick={() => setSelectedCatalog(null)}
                    >
                      ← В каталог
                    </button>
                    <button
                      className="btn-primary"
                      disabled={copying}
                      onClick={() => handleCopySystemDict(selectedCatalog.id)}
                    >
                      {copying ? 'Сохранение...' : '📥 Сохранить себе'}
                    </button>
                  </div>

                  <div style={{ marginBottom: '14px' }}>
                    <h3 style={{ fontSize: '20px' }}>{selectedCatalog.title}</h3>
                    <p className="state-desc" style={{ textAlign: 'left', marginTop: '4px' }}>
                      {selectedCatalog.description}
                    </p>
                  </div>

                  <div className="senses-list">
                    {selectedCatalog.words.map((w) => (
                      <div key={w.id} className="sense-card">
                        <h4 style={{ fontSize: '18px', textTransform: 'capitalize' }}>
                          {w.word}
                        </h4>
                        <div className="translations">
                          {w.senses[0]?.translations_ru.join(', ')}
                        </div>
                        <div className="definition">{w.senses[0]?.definition_en}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {showAddModal && (
        <div
          className="modal-backdrop"
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-title">Добавить «{result?.word}» в словарь</div>

            {modalSuccessMsg && (
              <p style={{ color: 'green', fontWeight: 600 }}>{modalSuccessMsg}</p>
            )}

            {dictionaries.length === 0 ? (
              <div>
                <p className="state-desc" style={{ marginBottom: '10px' }}>
                  Сначала создайте словарь:
                </p>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Название словаря..."
                    value={newDictTitle}
                    onChange={(e) => setNewDictTitle(e.target.value)}
                  />
                  <button
                    className="search-btn"
                    onClick={handleCreateDictionary}
                  >
                    ОК
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {dictionaries.map((d) => (
                  <div
                    key={d.id}
                    className="dict-option"
                    onClick={() => handleAddWordToDict(d.id)}
                  >
                    <span>{d.title}</span>
                    <span style={{ color: 'var(--tg-hint)', fontSize: '13px' }}>
                      {d.words_count} слов
                    </span>
                  </div>
                ))}
              </div>
            )}

            <button
              className="btn-secondary"
              style={{ marginTop: '8px' }}
              onClick={() => setShowAddModal(false)}
            >
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  )
}