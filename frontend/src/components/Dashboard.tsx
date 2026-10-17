"use client";

import { useState } from "react";
import { CsvUpload } from "./CsvUpload";
import { HistoryTable } from "./HistoryTable";
import { PredictForm } from "./PredictForm";
import { StatusPanel } from "./StatusPanel";

export function Dashboard() {
  // Bumped after each prediction so the history table refetches.
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <div className="md:col-span-2">
        <StatusPanel />
      </div>
      <PredictForm onPredicted={refresh} />
      <CsvUpload onPredicted={refresh} />
      <div className="md:col-span-2">
        <HistoryTable refreshKey={refreshKey} />
      </div>
    </div>
  );
}
