"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api, type ModelInfo } from "@/lib/api";

export type ModelState =
  | { status: "loading" }
  | { status: "offline" }
  | { status: "ready"; model: ModelInfo; mlUp: boolean };

const ModelContext = createContext<ModelState>({ status: "loading" });

// Fetches model + health once for every landing section that needs them.
export function ModelProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ModelState>({ status: "loading" });

  useEffect(() => {
    Promise.all([api.health(), api.model()])
      .then(([health, model]) => setState({ status: "ready", model, mlUp: health.ml.status === "ok" }))
      .catch(() => setState({ status: "offline" }));
  }, []);

  return <ModelContext value={state}>{children}</ModelContext>;
}

export const useModel = () => useContext(ModelContext);
