// // frontend\src\components\ResearchHeader.tsx
// import type { IconType } from "react-icons";
// import { FaChartLine } from "react-icons/fa";

// interface ResearchHeaderProps {
//   title?: string;
//   subtitle?: string;
//   icon?: IconType;
// }

// export default function ResearchHeader({
//   title = "SmartResearch",
//   subtitle = "AI driven Advanced Market Research - Powered by GenIntel",
//   icon: Icon = FaChartLine,
// }: ResearchHeaderProps) {
//   return (
//     <div className="text-center space-y-1">
//       <div className="flex items-center justify-center gap-2 mb-1">
//         <div className="p-2 bg-indigo-600/90 rounded-xl shadow-sm">
//           <Icon className="text-white" size={18} />
//         </div>
//         <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-700 to-purple-700 bg-clip-text text-transparent">
//           {title}
//         </h1>
//       </div>
//       <p className="text-base text-gray-600">{subtitle}</p>
//       <div className="w-20 h-1 bg-gradient-to-r from-indigo-500 to-purple-500 mx-auto rounded-full"></div>
//     </div>
//   );
// }


// frontend/src/components/ResearchHeader.tsx
import type { IconType } from "react-icons";
import { FaChartLine } from "react-icons/fa";

interface ResearchHeaderProps {
  title?: string;
  subtitle?: string;
  icon?: IconType;
  compact?: boolean; // ✅ new
  sticky?: boolean;  // ✅ new
}

export default function ResearchHeader({
  title = "SmartResearch",
  subtitle = "AI driven Advanced Market Research - Powered by GenIntel",
  icon: Icon = FaChartLine,
  compact = false,
  sticky = false,
}: ResearchHeaderProps) {
  return (
    <header
      className={`${
        sticky ? "sticky top-0 z-30 backdrop-blur bg-white/70" : ""
      } text-center space-y-1`}
    >
      <div className="flex items-center justify-center gap-2 mb-1">
        <div className="p-2 bg-indigo-600/90 rounded-xl shadow-sm">
          <Icon className="text-white" size={18} />
        </div>
        <h1
          className={`font-bold bg-gradient-to-r from-indigo-700 to-purple-700 bg-clip-text text-transparent ${
            compact ? "text-lg" : "text-2xl"
          }`}
        >
          {title}
        </h1>
      </div>
      {subtitle && (
        <p className={`${compact ? "text-sm" : "text-base"} text-gray-600`}>
          {subtitle}
        </p>
      )}
      <div className="w-20 h-1 bg-gradient-to-r from-indigo-500 to-purple-500 mx-auto rounded-full"></div>
    </header>
  );
}
