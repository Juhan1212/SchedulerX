export default function Loading({ isLoading }: { isLoading: boolean }) {
  if (!isLoading) return null

  return (
    <div className="loading-overlay">
      <div className="loading-spinner">
        <div className="loading-bounce loading-bounce1"></div>
        <div className="loading-bounce loading-bounce2"></div>
        <div className="loading-bounce loading-bounce3"></div>
        <div className="loading-bounce loading-bounce4"></div>
        <div className="loading-bounce loading-bounce5"></div>
      </div>
    </div>
  )
}
