import { useMemo, useState, useEffect } from 'react'
import Icon from './SVGIcon'

interface ClassNamesProps {
  container?: string
  pageItem?: string
  active?: string
  arrow?: string
  firstLastArrow?: string
}

interface PaginationProps {
  currentPage?: number
  totalPages: number
  onPageChange?: (page: number) => void
  className?: string
  classNames?: ClassNamesProps
}

export default function Pagination({
  currentPage: externalCurrentPage = 1,
  totalPages,
  onPageChange,
  className = '',
  classNames = {},
}: PaginationProps) {
  const [internalCurrentPage, setInternalCurrentPage] =
    useState(externalCurrentPage)

  const mergedClassNames = {
    container: `pagination-container ${classNames.container || ''}`,
    pageItem: `pagination-item ${classNames.pageItem || ''}`,
    active: `active ${classNames.active || ''}`,
    arrow: `pagination-arrow ${classNames.arrow || ''}`,
    firstLastArrow: `pagination-first-last-arrow ${
      classNames.firstLastArrow || ''
    }`,
  }

  useEffect(() => {
    setInternalCurrentPage(externalCurrentPage)
  }, [externalCurrentPage])

  const currentPage = internalCurrentPage

  const pages = useMemo(() => {
    const pageArray = []
    const edgePageCount = 4
    const displayCount = 5

    if (totalPages <= displayCount) {
      for (let i = 1; i <= totalPages; i++) {
        pageArray.push(i)
      }
    } else {
      let startPage, endPage

      if (currentPage <= edgePageCount) {
        startPage = 1
        endPage = displayCount
      } else if (currentPage > totalPages - edgePageCount) {
        startPage = totalPages - displayCount + 1
        endPage = totalPages
      } else {
        startPage = currentPage - Math.floor(displayCount / 2)
        endPage = startPage + displayCount - 1
      }

      if (startPage < 1) {
        startPage = 1
        endPage = startPage + displayCount - 1
      }

      if (endPage > totalPages) {
        endPage = totalPages
        startPage = Math.max(endPage - displayCount + 1, 1)
      }

      for (let i = startPage; i <= endPage; i++) {
        pageArray.push(i)
      }
    }

    return pageArray
  }, [currentPage, totalPages])

  const handlePageClick = (page: number) => {
    if (page !== currentPage) {
      setInternalCurrentPage(page)

      if (onPageChange) {
        onPageChange(page)
      }
    }
  }

  const handlePrevClick = () => {
    if (currentPage > 1) {
      const newPage = currentPage - 1
      setInternalCurrentPage(newPage)

      if (onPageChange) {
        onPageChange(newPage)
      }
    }
  }

  const handleNextClick = () => {
    if (currentPage < totalPages) {
      const newPage = currentPage + 1
      setInternalCurrentPage(newPage)

      if (onPageChange) {
        onPageChange(newPage)
      }
    }
  }

  const handleFirstClick = () => {
    if (currentPage !== 1) {
      setInternalCurrentPage(1)

      if (onPageChange) {
        onPageChange(1)
      }
    }
  }

  const handleLastClick = () => {
    if (currentPage !== totalPages) {
      setInternalCurrentPage(totalPages)

      if (onPageChange) {
        onPageChange(totalPages)
      }
    }
  }

  const isFriendListEmpty = !pages.length

  return (
    <div className={`${mergedClassNames.container} ${className}`}>
      <div className="btns-group">
        <button
          className={mergedClassNames.firstLastArrow}
          disabled={currentPage === 1}
          onClick={handleFirstClick}
          aria-label="첫 페이지로 이동"
        >
          <Icon
            className="pagination-arrow-icon cheverons"
            type="chevronsLeft"
          />
        </button>

        <button
          className={mergedClassNames.arrow}
          disabled={currentPage === 1}
          onClick={handlePrevClick}
          aria-label="이전 페이지"
        >
          <Icon className="pagination-arrow-icon cheveron" type="chevronLeft" />
        </button>
      </div>

      <div className="pagination-pages">
        {pages.map((page, index) => (
          <button
            key={index}
            className={`${mergedClassNames.pageItem} ${
              page === currentPage ? mergedClassNames.active : ''
            }`}
            onClick={() => handlePageClick(page)}
            aria-current={page === currentPage ? 'page' : undefined}
            aria-label={`${page} 페이지로 이동`}
          >
            {page}
          </button>
        ))}
      </div>

      <div className="btns-group">
        <button
          className={mergedClassNames.arrow}
          disabled={currentPage === totalPages || isFriendListEmpty}
          onClick={handleNextClick}
          aria-label="다음 페이지"
        >
          <Icon
            className="pagination-arrow-icon cheveron"
            type="chevronRight"
          />
        </button>

        <button
          className={mergedClassNames.firstLastArrow}
          disabled={currentPage === totalPages || isFriendListEmpty}
          onClick={handleLastClick}
          aria-label="마지막 페이지로 이동"
        >
          <Icon
            className="pagination-arrow-icon cheverons"
            type="chevronsRight"
          />
        </button>
      </div>
    </div>
  )
}
