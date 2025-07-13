import Icon from '../shared/SVGIcon'

interface MyPageHeaderProps {
  username: string
}

export default function MyPageHeader({ username }: MyPageHeaderProps) {
  return (
    <div className="page-header">
      <h1 className="page-header-title">마이페이지</h1>
      <div className="my-info">
        <span className="my-info-item">
          <Icon type="user" />
          {username} 님
        </span>
        {/* <span className="my-info-item"> */}
        {/* 휴대폰 번호로 변경..(?) 아니면 그냥 삭제(?) */}
        {/* <Icon type="email" /> */}
        {/* </span> */}
      </div>
    </div>
  )
}
