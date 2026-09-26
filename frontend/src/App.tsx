import React, { useEffect, useState } from 'react'
import {
  DashboardStats,
  SystemDictionaryDetail,
  SystemDictionarySummary,
  UserDictionaryDetail,
  UserDictionarySummary,
  WordSearchResult,
} from './types'

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
  const [tab, setTab] = useState<'search' | 'my' | 'catalog' | 'learning'>('search')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WordSearchResult | null>(null)
  const [notFoundQuery, setNotFoundQuery] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Данные профиля и дашборда
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null)
  const [userLevel, setUserLevel] = useState<string | null>(null)

  // Словари
  const [myDictionaries, setMyDictionaries] = useState<UserDictionarySummary[]>([])
  const [catalog, setCatalog] = useState<SystemDictionarySummary[]>([])
  const [selectedMyDict, setSelectedMyDict] = useState<UserDictionaryDetail | null>(null)
  const [selectedSysDict, setSelectedSysDict] = useState<SystemDictionaryDetail | null>(null)

  // Модалка добавления слова в словарь
  const [showAddModal, setShowAddModal] = useState(false)
  const [wordToAdd, setWordToAdd] = useState<WordSearchResult | null>(null)
  const [newDictTitle, setNewDictTitle] = useState('')

  // Состояние Placement Test
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
      const res = await fetch('/api/v1/users/me/dashboard', { headers: getHeaders() })
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
        fetch('/api/v1/dictionaries', { headers: getHeaders() }),
        fetch('/api/v1/system-dictionaries', { headers: getHeaders() }),
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
      const res = await fetch(`/api/v1/words/search?query=${encodeURIComponent(target)}`, {
        headers: getHeaders(),
      })
      if (res.status === 404) {
        setNotFoundQuery(target)
      } else if (!res.ok) {
        throw new Error(`Ошибка: ${res.status}`)
      } else {
        const data: WordSearchResult = await res.json()
        setResult(data)
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка соединения')
    } finally {
      setLoading(false)
    }
  }

  // Создание словаря и добавление слова
  const handleCreateAndAdd = async (dictTitle: string) => {
    if (!dictTitle.trim() || !wordToAdd) return
    try {
      const createRes = await fetch('/api/v1/dictionaries', {
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
      await handleAddWordToDict(newDict.id)
      setNewDictTitle('')
    } catch {
      alert('Ошибка при создании словаря')
    }
  }

  const handleAddWordToDict = async (dictId: string) => {
    if (!wordToAdd) return
    try {
      const res = await fetch(`/api/v1/dictionaries/${dictId}/words`, {
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
        alert('Слово уже в словаре')
      }
    } catch {
      alert('Не удалось добавить слово')
    }
  }

  // Placement Test
  const startTest = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/v1/placement/test', { headers: getHeaders() })
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
      const res = await fetch('/api/v1/placement/submit', {
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
      const res = await fetch(`/api/v1/system-dictionaries/${dictId}/copy`, {
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
      const res = await fetch(`/api/v1/system-dictionaries/${id}`, { headers: getHeaders() })
      if (res.ok) setSelectedSysDict(await res.json())
    } catch {}
  }

  const openMyDict = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/dictionaries/${id}`, { headers: getHeaders() })
      if (res.ok) setSelectedMyDict(await res.json())
    } catch {}
  }

  return (
    <div className="app-container">
      {/* Шапка с дашбордом */}
      {!isTesting && (
        <div className="dashboard-banner">
          <div className="banner-top" onClick={startTest} style={{ cursor: 'pointer' }}>
            <span>🎯 Уровень: <b>{userLevel || 'Не определен (Пройти тест)'}</b></span>
            <span>➔</span>
          </div>
          <div className="dashboard-stats">
            <div><b>{dashboard?.total_words_in_dicts || 0}</b> в словарях</div>
            <div><b>{dashboard?.words_learning || 0}</b> учу</div>
            <div><b>{dashboard?.words_mastered || 0}</b> выучено</div>
          </div>
        </div>
      )}

      {/* Режим прохождения тестирования */}
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
              <p>Правильных ответов: {testResult.score} из {testResult.total}</p>

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
            <span className="hint-chip" onClick={() => { setQuery('car'); handleSearch('car') }}>car</span>
            <span className="hint-chip" onClick={() => { setQuery('freedom'); handleSearch('freedom') }}>freedom</span>
          </div>

          {loading && <div className="state-box"><div className="spinner"></div><p>Ищем слово...</p></div>}
          {error && <div className="state-box"><p style={{ color: 'red' }}>{error}</p></div>}
          {notFoundQuery && <div className="state-box"><p>Слово «{notFoundQuery}» не найдено</p></div>}

          {result && (
            <div className="result-container">
              <div className="word-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 className="word-title">{result.word}</h2>
                <button
                  className="search-btn"
                  style={{ padding: '6px 12px', fontSize: '13px' }}
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
                    <div className="translations">{s.translations_ru.join(', ')}</div>
                    <div className="definition">{s.definition_en}</div>
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

      {/* Вкладка 2: Мои словари */}
      {!isTesting && tab === 'my' && (
        <div>
          {!selectedMyDict ? (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Новый словарь (напр. Рабочие слова)"
                  value={newDictTitle}
                  onChange={(e) => setNewDictTitle(e.target.value)}
                />
                <button className="search-btn" onClick={() => handleCreateAndAdd(newDictTitle)}>Создать</button>
              </div>
              <div className="dict-list">
                {myDictionaries.map((d) => (
                  <div key={d.id} className="dict-card" onClick={() => openMyDict(d.id)}>
                    <h3>{d.title}</h3>
                    <span>{d.words_count} слов ➔</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <button className="btn-cancel" onClick={() => setSelectedMyDict(null)}>⬅ Назад к словарям</button>
              <h2 style={{ margin: '12px 0' }}>{selectedMyDict.title}</h2>
              <div className="senses-list">
                {selectedMyDict.words.map((w) => (
                  <div key={w.id} className="sense-card">
                    <b>{w.word}</b>
                    <div>{w.senses[0]?.translations_ru.join(', ')}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Вкладка 3: Каталог */}
      {!isTesting && tab === 'catalog' && (
        <div>
          {!selectedSysDict ? (
            <div className="dict-list">
              {catalog.map((c) => (
                <div key={c.id} className="dict-card" onClick={() => openSystemDict(c.id)}>
                  <div>
                    <span className="badge-level">{c.target_level || 'ALL'}</span>
                    <h3 style={{ margin: '6px 0' }}>{c.title}</h3>
                    <p style={{ fontSize: '13px', color: 'gray' }}>{c.description}</p>
                  </div>
                  <span>{c.words_count} слов ➔</span>
                </div>
              ))}
            </div>
          ) : (
            <div>
              <button className="btn-cancel" onClick={() => setSelectedSysDict(null)}>⬅ В каталог</button>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '12px 0' }}>
                <h2>{selectedSysDict.title}</h2>
                <button className="search-btn" onClick={() => copyRecommendedDict(selectedSysDict.id)}>
                  📥 Сохранить себе
                </button>
              </div>
              <div className="senses-list">
                {selectedSysDict.words.map((w) => (
                  <div key={w.id} className="sense-card">
                    <b>{w.word}</b> — {w.senses[0]?.translations_ru.join(', ')}
                    <div style={{ fontSize: '13px', color: 'gray' }}>{w.senses[0]?.definition_en}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Модалка добавления слова в словарь */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Добавить «{wordToAdd?.word}» в словарь</h3>
            <div className="dict-list" style={{ maxHeight: '200px', overflowY: 'auto', margin: '12px 0' }}>
              {myDictionaries.map((d) => (
                <div key={d.id} className="dict-card" style={{ padding: '8px' }} onClick={() => handleAddWordToDict(d.id)}>
                  <span>{d.title}</span>
                  <button className="search-btn" style={{ padding: '4px 8px' }}>Выбрать</button>
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
            <button className="btn-cancel" style={{ width: '100%', marginTop: '10px' }} onClick={() => setShowAddModal(false)}>
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  )
}