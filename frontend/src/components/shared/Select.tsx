import { useState, useRef, useEffect, useId } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { create } from 'zustand'
import CloudinaryImage from './CloudinaryImage'
import Icon from './SVGIcon'

export type SelectOption = {
  value: number | string
  label: string
  icon?: string
}

interface CustomSelectProps {
  options: SelectOption[]
  defaultValue?: SelectOption
  selectedValue?: string | number | null
  placeholder?: string
  disabled?: boolean
  onChange?: (option: SelectOption) => void
  classNames?: {
    root?: string
    input?: string
    dropdown?: string
    option?: string
  }
  name?: string
  arrowType?: 'filled' | 'line'
}

type SelectStore = {
  openSelectId: string | null
  setOpenSelectId: (id: string | null) => void
}

export const useSelectStore = create<SelectStore>((set) => ({
  openSelectId: null,
  setOpenSelectId: (id) => set({ openSelectId: id }),
}))

/**
 * Select 컴포넌트
 * - defaultValue & selectedValue 병행: 제어/비제어 모두 지원
 * - openSelectId: 전역에서 관리 -> 여러 Select 중 하나만 열리는 형태
 */
export default function Select({
  options,
  defaultValue,
  selectedValue,
  placeholder,
  disabled = false,
  onChange,
  classNames = {},
  name,
  arrowType = 'filled',
}: CustomSelectProps) {
  const generatedId = useId()
  const selectId = `select-${generatedId}`

  const [selectedOption, setSelectedOption] = useState<SelectOption | null>(
    defaultValue || (options.length > 0 && !placeholder ? options[0] : null),
  )

  const selectRef = useRef<HTMLDivElement>(null)

  const { openSelectId, setOpenSelectId } = useSelectStore()
  const isOpen = openSelectId === selectId
  const hasOptions = options.length > 0

  useEffect(() => {
    if (selectedValue === null || selectedValue === undefined) {
      setSelectedOption(null)
      return
    }
    const found = options.find((opt) => opt.value === selectedValue)
    if (found) {
      setSelectedOption(found)
    }
  }, [selectedValue, options])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        selectRef.current &&
        !selectRef.current.contains(e.target as Node) &&
        openSelectId === selectId
      ) {
        setOpenSelectId(null)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [openSelectId, selectId, setOpenSelectId])

  const toggleDropdown = () => {
    if (!disabled && hasOptions) {
      setOpenSelectId(isOpen ? null : selectId)
    }
  }
  const handleSelect = (option: SelectOption) => {
    setSelectedOption(option)
    setOpenSelectId(null)
    if (onChange) {
      onChange(option)
    }
  }

  return (
    <div
      ref={selectRef}
      className={`custom-select ${disabled ? 'disabled' : ''} ${
        !hasOptions ? 'no-options' : ''
      } ${classNames.root || ''}`}
    >
      <div
        className={`select-input ${classNames.input || ''}`}
        onClick={disabled ? undefined : toggleDropdown}
        onKeyDown={(e) => {
          if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault()
            toggleDropdown()
          }
        }}
        role="button"
        tabIndex={disabled || !hasOptions ? -1 : 0}
        aria-expanded={isOpen}
        aria-disabled={disabled}
        aria-haspopup={hasOptions ? 'listbox' : undefined}
        data-state={isOpen ? 'open' : 'closed'}
        data-disabled={disabled || undefined}
        data-has-value={selectedOption ? true : undefined}
        data-placeholder={!selectedOption && placeholder ? true : undefined}
      >
        <div className="select-value">
          {selectedOption?.icon && (
            <CloudinaryImage
              publicId={selectedOption.icon}
              className="option-icon"
            />
          )}
          <span className="option-text">
            {selectedOption
              ? selectedOption.label
              : placeholder || '선택하세요'}
          </span>
        </div>

        {/* 옵션이 존재할 때만 화살표 아이콘 표시 */}
        {hasOptions && (
          <div
            className={`select-arrow ${isOpen ? 'open' : ''} ${
              disabled ? 'disabled' : ''
            }`}
          >
            <Icon
              type={arrowType === 'filled' ? 'downFilled' : 'downLine'}
              className="select-arrow-icon"
            />
          </div>
        )}
      </div>

      <AnimatePresence>
        {isOpen && hasOptions && (
          <motion.div
            className={`select-options ${classNames.dropdown || ''}`}
            role="listbox"
            id={`${selectId}-options`}
            aria-labelledby={`${selectId}-label`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            style={{ zIndex: 1000 }}
          >
            {options.map((option) => (
              <div
                key={option.value}
                className={`select-option ${
                  selectedOption?.value === option.value ? 'selected' : ''
                } ${classNames.option || ''}`}
                onClick={() => handleSelect(option)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handleSelect(option)
                  }
                }}
                role="option"
                tabIndex={0}
                aria-selected={selectedOption?.value === option.value}
              >
                {option.icon && (
                  <CloudinaryImage
                    publicId={option.icon}
                    className="option-icon"
                  />
                )}
                <span className="option-text">{option.label}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {name && (
        <input type="hidden" name={name} value={selectedOption?.value || ''} />
      )}
    </div>
  )
}
