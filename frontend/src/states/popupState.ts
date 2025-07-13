import { create } from "zustand";

interface PopupState<T = unknown> {
  isOpen: boolean;
  popupData: T | null;
  openPopup: (data?: T | null) => void;
  closePopup: () => void;
}

export const usePopupState = create<PopupState<unknown>>((set) => ({
  isOpen: false,
  popupData: null,
  openPopup: (data = null) => set({ isOpen: true, popupData: data }),
  closePopup: () => set({ isOpen: false, popupData: null }),
}));
