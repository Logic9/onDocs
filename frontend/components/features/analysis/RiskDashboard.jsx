import { memo } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  ShieldAlert,
  Activity,
} from "lucide-react";

const RiskDashboard = memo(({ riskResults }) => {
  const riskCount = riskResults.length;
  let statusColor = "bg-green-100 text-green-700 border-green-200";
  let statusIcon = <ShieldCheck size={16} />;
  let statusText = "안전 (Safe)";

  if (riskCount > 0 && riskCount <= 2) {
    statusColor = "bg-amber-100 text-amber-700 border-amber-200";
    statusIcon = <AlertTriangle size={16} />;
    statusText = "주의 (Caution)";
  } else if (riskCount > 2) {
    statusColor = "bg-red-100 text-red-700 border-red-200";
    statusIcon = <ShieldAlert size={16} />;
    statusText = "위험 (Check Required)";
  }

  return (
    <div className="mb-4 p-4 rounded-xl bg-white border border-gray-200 shadow-sm">
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1">
        <Activity size={12} /> 문서 특이사항 리포트
      </h3>
      <div className="flex items-center justify-between">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${statusColor} text-xs font-bold`}
        >
          {statusIcon} <span>{statusText}</span>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-gray-400">탐지된 제약/위험</div>
          <div className="text-lg font-bold text-gray-900">{riskCount}건</div>
        </div>
      </div>
    </div>
  );
});

RiskDashboard.displayName = "RiskDashboard";
export default RiskDashboard;
