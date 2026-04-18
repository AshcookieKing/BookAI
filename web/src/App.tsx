import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { PhotoStudioPage } from "./pages/PhotoStudioPage";
import { VideoStudioPage } from "./pages/VideoStudioPage";
import { BookStudioPage } from "./pages/BookStudioPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { PricingPage } from "./pages/PricingPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/studio/photo" element={<PhotoStudioPage />} />
        <Route path="/studio/video" element={<VideoStudioPage />} />
        <Route path="/studio/book" element={<BookStudioPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
