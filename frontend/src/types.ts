export interface WordSense {
  id: string
  part_of_speech: string
  transcription: string | null
  translations_ru: string[]
  definition_en: string
  example_en: string | null
  example_ru: string | null
  synonyms: string[]
  order_index: number
}

export interface WordSearchResult {
  id: string
  word: string
  senses: WordSense[]
}

export interface UserDictionarySummary {
  id: string
  title: string
  description?: string | null
  words_count: number
  created_at: string
}

export interface UserDictionaryDetail {
  id: string
  title: string
  description?: string | null
  created_at: string
  words: WordSearchResult[]
}

export interface SystemDictionarySummary {
  id: string
  slug: string
  title: string
  description?: string | null
  target_level?: string | null
  words_count: number
}

export interface SystemDictionaryDetail {
  id: string
  slug: string
  title: string
  description?: string | null
  target_level?: string | null
  words: WordSearchResult[]
}

export interface DashboardStats {
  total_words_in_dicts: number
  words_new: number
  words_learning: number
  words_mastered: number
}

export interface WordProgress {
  word_id: string
  status: 'new' | 'learning' | 'mastered'
  correct_count: number
  incorrect_count: number
  streak_count: number
  last_reviewed_at?: string | null
}

export type ExerciseType =
  | 'multiple_choice'
  | 'letter_scramble'
  | 'missing_letters'
  | 'sentence_reorder'

export interface LearningCard {
  question_id: string
  exercise_type: ExerciseType
  prompt_main: string
  prompt_sub?: string | null
  target_answer: string
  tokens: string[]
  options: string[]
}

export interface LearningSessionResponse {
  cards: LearningCard[]
}

export interface PlacementQuestion {
  id: number
  level: string
  word: string
  prompt: string
  options: string[]
}

export interface PlacementTestResponse {
  questions: PlacementQuestion[]
}

export interface PlacementResultResponse {
  score: number
  total: number
  cefr_level: string
  level_title: string
  description: string
  recommended_dictionary_id?: string | null
}

export interface UserProfile {
  id: string
  telegram_id: number
  first_name: string
  last_name?: string | null
  username?: string | null
  cefr_level?: string | null
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string
        initDataUnsafe?: {
          user?: {
            id: number
            first_name: string
            last_name?: string
            username?: string
          }
        }
        ready: () => void
        expand: () => void
        close: () => void
        HapticFeedback?: {
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void
          impactOccurred: (style: 'light' | 'medium' | 'heavy') => void
        }
        themeParams?: {
          bg_color?: string
          text_color?: string
          hint_color?: string
          link_color?: string
          button_color?: string
          button_text_color?: string
          secondary_bg_color?: string
        }
      }
    }
  }
}