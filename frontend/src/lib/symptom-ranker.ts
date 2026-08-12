import type { DoctorSummary } from './types'

interface CategoryRule {
  name: string
  keywords: string[]
}

const CATEGORY_RULES: CategoryRule[] = [
  {
    name: 'Cardiology',
    keywords: ['chest', 'heart', 'palpitation', 'hypertension', 'pressure', 'angina', 'cardio'],
  },
  {
    name: 'Dentistry',
    keywords: ['tooth', 'teeth', 'gum', 'jaw', 'dental', 'denture', 'caries'],
  },
  {
    name: 'Pediatrics',
    keywords: ['child', 'baby', 'kid', 'infant', 'newborn', 'toddler'],
  },
  {
    name: 'Neurology',
    keywords: ['headache', 'migraine', 'dizzy', 'dizziness', 'seizure', 'tremor', 'nerve', 'neuro'],
  },
  {
    name: 'Dermatology',
    keywords: ['rash', 'skin', 'acne', 'itch', 'eczema', 'psoriasis', 'dermat', 'hives'],
  },
  {
    name: 'Gynecology',
    keywords: ['pregnan', 'menstru', 'gyneco', 'womb', 'ovary', 'period', 'cervical'],
  },
  {
    name: 'Ophthalmology',
    keywords: ['eye', 'vision', 'sight', 'blurr', 'cataract', 'glaucoma', 'ophthal'],
  },
  {
    name: 'Orthopedics',
    keywords: ['bone', 'joint', 'knee', 'back pain', 'spine', 'fracture', 'ortho', 'muscle', 'ankle'],
  },
  {
    name: 'Therapy',
    keywords: ['flu', 'cold', 'fever', 'cough', 'throat', 'infection', 'weakness', 'temperature', 'gastro', 'stomach', 'nausea', 'diarrhea'],
  },
  {
    name: 'ENT',
    keywords: ['ear', 'nose', 'sinus', 'throat', 'hearing', 'ent', 'tonsil'],
  },
]

const RED_FLAG_PHRASES = [
  'chest pain',
  'difficulty breathing',
  'shortness of breath',
  'severe bleeding',
  'unconscious',
  'stroke',
  'seizure',
  'suicid',
]

export interface RankedDoctor {
  doctor: DoctorSummary
  categoryName: string
  hospitalName: string
  hospitalId: number
  city: string
  score: number
}

export function classifySymptoms(text: string): string[] {
  const lower = text.toLowerCase()
  return CATEGORY_RULES.filter((rule) =>
    rule.keywords.some((keyword) => lower.includes(keyword)),
  ).map((rule) => rule.name)
}

export function hasRedFlagSymptoms(text: string): boolean {
  const lower = text.toLowerCase()
  return RED_FLAG_PHRASES.some((phrase) => lower.includes(phrase))
}

export function scoreDoctors(
  doctors: { doctor: DoctorSummary; categoryName: string; hospitalName: string; hospitalId: number; city: string }[],
): RankedDoctor[] {
  return doctors
    .map((item) => ({ ...item, score: item.doctor.rating_avg }))
    .sort((a, b) => b.score - a.score)
}
