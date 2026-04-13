import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useRunQuery } from "../hooks/useResearchRuns";


export function RunRedirectPage() {
  const { runId = "" } = useParams();
  const navigate = useNavigate();
  const runQuery = useRunQuery(runId);

  useEffect(() => {
    if (!runQuery.data) {
      return;
    }
    navigate(`/conversations/${runQuery.data.conversation_id}`, { replace: true });
  }, [navigate, runQuery.data]);

  if (runQuery.isLoading) {
    return <div className="workspace-screen workspace-loading">正在定位会话...</div>;
  }

  if (runQuery.isError || !runQuery.data) {
    return <div className="workspace-screen workspace-error">无法定位该运行对应的会话。</div>;
  }

  return <div className="workspace-screen workspace-loading">正在跳转到会话...</div>;
}
