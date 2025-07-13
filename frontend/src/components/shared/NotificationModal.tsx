import { Form, useNavigation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, type ReactNode } from 'react'
import { create } from 'zustand'

interface NotificationModalProps {
  title?: string
  content: string
  pendingMsg?: string
  type?: 'alert' | 'info'
  method?: 'get' | 'post'
  bodyPayload?: ReactNode
}

interface NotificationState {
  isOpen: boolean
  openModalPayload?: unknown
  openModal: (openModalPayload: unknown) => void
  closeModal: () => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  isOpen: false,
  openModal: (openModalPayload: unknown) =>
    set({ isOpen: true, openModalPayload }),
  closeModal: () => set({ isOpen: false }),
}))

export default function NotificationModal({
  title,
  content,
  type = 'alert',
  method = 'post',
  bodyPayload,
  pendingMsg,
}: NotificationModalProps) {
  const navigation = useNavigation()
  const isPending = navigation.state === 'submitting'
  const isSuccess = navigation.state === 'idle' && navigation.formMethod
  const { isOpen, closeModal } = useNotificationStore()

  useEffect(() => {
    if (!isSuccess) return

    closeModal()
  }, [isSuccess, closeModal])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.5 }}
          transition={{ duration: 0 }}
          className="flex items-center justify-center"
        >
          <div className="absolute bg-blue-600 p-6 rounded-lg shadow-lg w-96 text-center">
            {title && <h3>{title}</h3>}
            <p>{content}</p>
            <div>
              {type === 'info' && (
                <button type="button" onClick={closeModal}>
                  확인
                </button>
              )}
              {type === 'alert' && !isPending && !isSuccess && (
                <div className="flex justify-center mt-4">
                  <button type="button" onClick={closeModal}>
                    <span className="text-red-800 font-semibold mr-4">
                      취소
                    </span>
                  </button>
                  <Form method={method}>
                    {bodyPayload}
                    <button type="submit">
                      <span className="text-purple-800 font-semibold">
                        확인
                      </span>
                    </button>
                  </Form>
                </div>
              )}
              {type === 'alert' && isPending && (
                <div className="mt-4">
                  <span className="text-orange-700">{pendingMsg}</span>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
