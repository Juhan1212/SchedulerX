import DocumentIcon from "@icons/document.svg?react";
import BookmarkIcon from "@icons/bookmark.svg?react";
import PencilIcon from "@icons/pencil.svg?react";
import SymbolIcon from "@icons/symbol.svg?react";
import ErrorIcon from "@icons/error.svg?react";
import UserIcon from "@icons/user.svg?react";
import LogoutIcon from "@icons/logout.svg?react";
import DownFilledIcon from "@icons/down-filled.svg?react";
import DownLineIcon from "@icons/down-line.svg?react";
import ClockIcon from "@icons/clock.svg?react";
import AddIcon from "@icons/add.svg?react";
import RemoveIcon from "@icons/remove.svg?react";
import CursorIcon from "@icons/cursor.svg?react";
import HorizontalLineIcon from "@icons/tool-horizontal.svg?react";
import VerticalLineIcon from "@icons/tool-vertical.svg?react";
import TrendLineIcon from "@icons/tool-trend.svg?react";
import RayLineIcon from "@icons/tool-ray.svg?react";
import Erasericon from "@icons/tool-eraser.svg?react";
import VisibleIcon from "@icons/visible.svg?react";
import InvisibleIcon from "@icons/invisible.svg?react";
import EmailIcon from "@icons/email.svg?react";
import HamburgerIcon from "@icons/hamburger.svg?react";
import ChartIcon from "@icons/chart.svg?react";
import ArrowIcon from "@icons/arrow.svg?react";
import CheckIcon from "@icons/check.svg?react";
import CopyIcon from "@icons/copy.svg?react";
import MoneyIcon from "@icons/money.svg?react";
import chevronLeftIcon from "@icons/chevron-left.svg?react";
import chevronsLeftIcon from "@icons/chevrons-left.svg?react";
import chevronRightIcon from "@icons/chevron-right.svg?react";
import chevronsRightIcon from "@icons/chevrons-right.svg?react";
import closeIcon from "@icons/close.svg?react";
import checkboxIcon from "@icons/checkbox-outline.svg?react";
import checkboxCheckedIcon from "@icons/checkbox-checked.svg?react";
import longArrowIcon from "@icons/long-arrow.svg?react";
import checkCircleIcon from "@icons/check-circle-outline.svg?react";
import checkCircleCheckedIcon from "@icons/check-circle.svg?react";

export const icons = {
  document: DocumentIcon,
  bookmark: BookmarkIcon,
  pencil: PencilIcon,
  symbol: SymbolIcon,
  error: ErrorIcon,
  user: UserIcon,
  logout: LogoutIcon,
  downFilled: DownFilledIcon,
  downLine: DownLineIcon,
  clock: ClockIcon,
  add: AddIcon,
  remove: RemoveIcon,
  cursor: CursorIcon,
  horizontalLine: HorizontalLineIcon,
  verticalLine: VerticalLineIcon,
  trendLine: TrendLineIcon,
  visible: VisibleIcon,
  rayLine: RayLineIcon,
  eraser: Erasericon,
  invisible: InvisibleIcon,
  email: EmailIcon,
  hamburger: HamburgerIcon,
  chart: ChartIcon,
  arrow: ArrowIcon,
  check: CheckIcon,
  copy: CopyIcon,
  money: MoneyIcon,
  chevronLeft: chevronLeftIcon,
  chevronsLeft: chevronsLeftIcon,
  chevronRight: chevronRightIcon,
  chevronsRight: chevronsRightIcon,
  close: closeIcon,
  checkbox: checkboxIcon,
  checkboxChecked: checkboxCheckedIcon,
  longArrow: longArrowIcon,
  checkCircle: checkCircleIcon,
  checkCircleChecked: checkCircleCheckedIcon,
};

export type IconName = keyof typeof icons;
