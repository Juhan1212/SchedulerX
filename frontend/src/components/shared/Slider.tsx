import React, { useState, useEffect, useRef } from 'react'
import type { ChangeEvent } from 'react'

interface SliderProps {
  min: number
  max: number
  step: number
  value: number
  onChange: (value: number) => void
  disabled?: boolean
  labelText?: string
  showValue?: boolean
  valueUnit?: string
  name?: string
  classNames?: {
    root?: string
    track?: string
    fill?: string
    thumb?: string
    input?: string
    label?: string
    value?: string
    markers?: string
    marker?: string
    markerLabel?: string
  }
  markers?: Array<{ value: number; label: string }>
}

const Slider: React.FC<SliderProps> = ({
  min,
  max,
  step,
  value,
  onChange,
  disabled = false,
  labelText,
  showValue = false,
  valueUnit = '',
  name,
  classNames = {},
  markers = [],
}) => {
  const [sliderValue, setSliderValue] = useState<number>(value)
  const sliderRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState<boolean>(false)

  const fillPercentage = (() => {
    const value = sliderValue
    if (value < min) return 0
    if (value > max) return 100
    return ((value - min) / (max - min)) * 100
  })()

  const handleMarkerClick = (markerValue: number) => {
    if (disabled) return
    setSliderValue(markerValue)
    onChange(markerValue)
  }

  const displayMarkers = markers.length > 0 ? markers : []

  useEffect(() => {
    setSliderValue(value)
  }, [value])

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newValue = Number(e.target.value)
    setSliderValue(newValue)
    onChange(newValue)
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return
    e.preventDefault() // 텍스트 선택 방지
    setIsDragging(true)
    updateValueFromPosition(e.clientX)

    // Add event listeners for drag and release
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      e.preventDefault() // 드래그 중 텍스트 선택 방지
      updateValueFromPosition(e.clientX)
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }

  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled) return
    setIsDragging(true)
    updateValueFromPosition(e.touches[0].clientX)
    // non‑passive 로 등록
    document.addEventListener('touchmove', handleTouchMove, { passive: false })
    document.addEventListener('touchend', handleTouchEnd)
  }

  const handleTouchMove = (e: TouchEvent) => {
    e.preventDefault()
    updateValueFromPosition((e.touches && e.touches[0].clientX) || 0)
  }

  const handleTouchEnd = () => {
    setIsDragging(false)
    document.removeEventListener('touchmove', handleTouchMove)
    document.removeEventListener('touchend', handleTouchEnd)
  }

  const updateValueFromPosition = (clientX: number) => {
    if (!sliderRef.current) return

    const sliderRect = sliderRef.current.getBoundingClientRect()
    const sliderWidth = sliderRect.width
    const offsetX = clientX - sliderRect.left

    const percentage = Math.max(0, Math.min(1, offsetX / sliderWidth))
    const raw = percentage * (max - min) + min
    const newValue = Math.min(Math.floor(raw / step) * step, max)

    setSliderValue(newValue)
    onChange(newValue)
  }

  // 마커가 현재 슬라이더 값보다 작거나 같은지 확인하는 함수
  const isMarkerPassed = (markerValue: number) => {
    const value = sliderValue
    if (value > max) return true
    if (value < min) return false
    return markerValue <= value
  }

  return (
    <div className={`slider-container ${classNames.root || ''}`}>
      {labelText && (
        <label className={`slider-label ${classNames.label || ''}`}>
          {labelText}
        </label>
      )}
      <div className="slider-wrapper">
        <div
          ref={sliderRef}
          className={`slider-track ${disabled ? 'slider-disabled' : ''} ${
            classNames.track || ''
          }`}
          onMouseDown={disabled ? undefined : handleMouseDown}
          onTouchStart={disabled ? undefined : handleTouchStart}
          role="slider"
          aria-valuemin={min}
          aria-valuemax={max}
          aria-valuenow={sliderValue}
          aria-orientation="horizontal"
          aria-disabled={disabled || undefined}
          tabIndex={disabled ? -1 : 0}
          onKeyDown={(e) => {
            if (disabled) return

            let nextValue
            switch (e.key) {
              case 'ArrowRight':
              case 'ArrowUp':
                e.preventDefault()
                nextValue = Math.min(max, sliderValue + step)
                setSliderValue(nextValue)
                onChange(nextValue)
                break
              case 'ArrowLeft':
              case 'ArrowDown':
                e.preventDefault()
                nextValue = Math.max(min, sliderValue - step)
                setSliderValue(nextValue)
                onChange(nextValue)
                break
              case 'Home':
                e.preventDefault()
                setSliderValue(min)
                onChange(min)
                break
              case 'End':
                e.preventDefault()
                setSliderValue(max)
                onChange(max)
                break
              default:
                break
            }
          }}
        >
          <div
            className={`slider-fill ${classNames.fill || ''}`}
            style={{ width: `${fillPercentage}%` }}
          ></div>
          <div
            className={`slider-thumb ${classNames.thumb || ''}`}
            style={{ left: `${fillPercentage}%` }}
            onMouseDown={(e) => {
              if (disabled) return
              e.preventDefault()
              e.stopPropagation() // 트랙의 이벤트 막음
              setIsDragging(true)

              // 드래그 처리 이벤트리스너
              const handleThumbMouseMove = (moveEvent: MouseEvent) => {
                moveEvent.preventDefault()
                updateValueFromPosition(moveEvent.clientX)
              }

              const handleThumbMouseUp = () => {
                setIsDragging(false)
                document.removeEventListener('mousemove', handleThumbMouseMove)
                document.removeEventListener('mouseup', handleThumbMouseUp)
              }

              // 문서 레벨에서 이벤트 처리
              document.addEventListener('mousemove', handleThumbMouseMove)
              document.addEventListener('mouseup', handleThumbMouseUp)
            }}
            onTouchStart={disabled ? undefined : handleTouchStart}
            role="button"
            tabIndex={disabled ? -1 : 0}
            aria-label="슬라이더 조절"
            onKeyDown={(e) => {
              if (disabled) return
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                // 엔터나 스페이스바를 누르면 현재 위치로
              }
            }}
          />
          {displayMarkers.length > 0 && (
            <div
              className={`slider-markers ${classNames.markers || ''}`}
              style={{ pointerEvents: isDragging ? 'none' : 'auto' }} // 드래그 중에는 마커 상호작용 비활성화
            >
              {displayMarkers.map((marker) => {
                const markerPosition =
                  ((marker.value - min) / (max - min)) * 100
                const isPassed = isMarkerPassed(marker.value)

                return (
                  <div
                    key={marker.value}
                    className={`slider-marker ${
                      sliderValue === marker.value ? 'slider-marker-active' : ''
                    } ${isPassed ? 'slider-marker-passed' : ''} ${
                      classNames.marker || ''
                    }`}
                    style={{ left: `${markerPosition}%` }}
                    onClick={(e) => {
                      e.stopPropagation() // 슬라이더 트랙 클릭 이벤트와 충돌 방지
                      handleMarkerClick(marker.value)
                    }}
                    role="button"
                    tabIndex={disabled ? -1 : 0}
                    aria-label={`Set value to ${marker.label}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleMarkerClick(marker.value)
                      }
                    }}
                  >
                    <div
                      className={`slider-marker-label ${
                        isPassed ? 'slider-marker-label-passed' : ''
                      } ${classNames.markerLabel || ''}`}
                    >
                      {marker.label}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={sliderValue}
          onChange={handleInputChange}
          className={`slider-input ${classNames.input || ''}`}
          disabled={disabled}
          name={name}
        />
        {showValue && (
          <div className={`slider-value ${classNames.value || ''}`}>
            {sliderValue}
            {valueUnit}
          </div>
        )}
      </div>
    </div>
  )
}

export default Slider
