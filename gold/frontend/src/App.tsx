import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Splash from "./components/Splash";
import Toasts from "./components/Toasts";
import Alerts from "./pages/Alerts";
import ChartPage from "./pages/ChartPage";
import Detail from "./pages/Detail";
import Home from "./pages/Home";
import News from "./pages/News";
import Settings from "./pages/Settings";
import { useMarket } from "./state/Market";

export default function App() {
  const { loading, quoteList } = useMarket();
  const [splashGone, setSplashGone] = useState(false);

  useEffect(() => {
    if (!loading && quoteList.length > 0) {
      const t = window.setTimeout(() => setSplashGone(true), 450);
      return () => window.clearTimeout(t);
    }
    const safety = window.setTimeout(() => setSplashGone(true), 4000);
    return () => window.clearTimeout(safety);
  }, [loading, quoteList.length]);

  return (
    <>
      <Splash hidden={splashGone} />
      <div className="app">
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/detail/:ref" element={<Detail />} />
          <Route path="/chart" element={<ChartPage />} />
          <Route path="/news" element={<News />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Home />} />
        </Routes>
        <Toasts />
      </div>
    </>
  );
}
