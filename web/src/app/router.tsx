import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { HomePage } from "../pages/HomePage";
import { ConversationPage } from "../pages/ConversationPage";
import { RunRedirectPage } from "../pages/RunRedirectPage";
import { RunsPage } from "../pages/RunsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "conversations/:conversationId",
        element: <ConversationPage />,
      },
      {
        path: "runs",
        element: <RunsPage />,
      },
      {
        path: "runs/:runId",
        element: <RunRedirectPage />,
      },
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
