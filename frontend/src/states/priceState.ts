import { create } from 'zustand'

interface PriceState {
  clickedPrice: number | null
  setClickedPrice: (price: number | null) => void
}

export const usePriceStore = create<PriceState>((set) => ({
  clickedPrice: null,
  setClickedPrice: (price) => set({ clickedPrice: price }),
}))
