import React from 'react';
import { AlertCircle } from 'lucide-react';

export const SyntheticLabBanner: React.FC = () => {
  return (
    <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6 rounded-r-md">
      <div className="flex items-start">
        <AlertCircle className="w-5 h-5 text-amber-600 mr-3 mt-0.5 shrink-0" />
        <div>
          <h3 className="text-sm font-semibold text-amber-800">
            Synthetic Fault-Injection Laboratory
          </h3>
          <p className="text-xs text-amber-700 mt-1">
            Experiments run in strictly isolated synthetic test namespaces with fictional data.
            Fault switches intentionally exercise real retained vector chunks, caches, and memory in this lab only.
            Ordinary application documents always use the secure pipeline.
          </p>
        </div>
      </div>
    </div>
  );
};
