import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/newsreader/400.css";
import "@fontsource/newsreader/500.css";
import "@fontsource/newsreader/400-italic.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "./index.css";
import { AppShell } from "./components/AppShell";
import { Loading } from "./components/ui";
import { SessionProvider, useSession } from "./lib/session";
import type { Role } from "./lib/types";
import { SignIn } from "./pages/SignIn";
import { AssignmentPage } from "./pages/professor/Assignment";
import { CourseOverview, Courses } from "./pages/professor/Courses";
import { InsightPage } from "./pages/professor/Insight";
import { InterventionPage } from "./pages/professor/Intervention";
import { EvaluationPage } from "./pages/professor/Evaluation";
import { SubmissionPage } from "./pages/professor/Submission";
import { StudentAssignmentPage, StudentHomePage } from "./pages/student/Student";
import { TaskPage } from "./pages/student/Task";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

function RequireRole({ role }: { role: Role }) {
  const { user, ready } = useSession();
  if (!ready) return <Loading />;
  if (!user) return <Navigate to="/" replace />;
  if (user.role !== role) return <Navigate to={user.role === "professor" ? "/p" : "/s"} replace />;
  return <AppShell />;
}

function Home() {
  const { user, ready } = useSession();
  if (!ready) return <Loading />;
  if (user) return <Navigate to={user.role === "professor" ? "/p" : "/s"} replace />;
  return <SignIn />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/p" element={<RequireRole role="professor" />}>
              <Route index element={<Courses />} />
              <Route path="courses/:courseId" element={<CourseOverview />} />
              <Route path="assignments/:assignmentId" element={<AssignmentPage />} />
              <Route path="insights/:insightId" element={<InsightPage />} />
              <Route path="submissions/:submissionId" element={<SubmissionPage />} />
              <Route path="interventions/:interventionId" element={<InterventionPage />} />
              <Route path="evaluation" element={<EvaluationPage />} />
            </Route>
            <Route path="/s" element={<RequireRole role="student" />}>
              <Route index element={<StudentHomePage />} />
              <Route path="assignments/:assignmentId" element={<StudentAssignmentPage />} />
              <Route path="tasks/:taskId" element={<TaskPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </SessionProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
