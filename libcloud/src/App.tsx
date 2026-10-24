import { useState } from 'react'
import './App.css'
import { ArrowDownWideNarrow, Palette, Share2, Hash } from 'lucide-react'

export function GithubIcon({ className = "w-4 h-4 text-black" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

function App() {
  const [maxCount, setMaxCount] = useState<string>("");
  const [username, setUsername] = useState<string>("");
  const [order, setOrder] = useState<string>("max-frequency");
  const [_clickGenerate, setClickGenerate] = useState<boolean>(false);
  const [shareVia, SetShareVia] = useState<string>("");
  const [theme, setTheme] = useState<string>("Minimal");

  // Dropdown open states
  const [openOrder, setOpenOrder] = useState<boolean>(false);
  const [openTheme, setOpenTheme] = useState<boolean>(false);
  const [openShare, setOpenShare] = useState<boolean>(false);

  const orderOptions = [
    { label: "Max frequency", value: "max-frequency" },
    { label: "Min frequency", value: "min-frequency" },
    { label: "tf-idf", value: "tf-idf" },
  ];

  const themeOptions = ["Minimal", "Futuristic", "ReadME", "Neon"];
  const shareOptions = [
    { label: "Share Via Link", value: "link" },
    { label: "Embed in ReadMe", value: "readme" },
    { label: "Image for Portfolio", value: "portfolio" },
    { label: "Share in Social Media", value: "social" },
  ];

  const closeAllDropdowns = () => {
    setOpenOrder(false);
    setOpenTheme(false);
    setOpenShare(false);
  };

  const handleGenerate = () => {
    if (maxCount.trim() === "" || parseInt(maxCount) < 0 || parseInt(maxCount) > 500) {
      alert("please enter a valid number");
      return;
    }
    if (username.trim() === "") {
      alert("please enter a valid username");
      return;
    }
    setClickGenerate(true);
  };

  return (
    <>
      <section className="mt-4 flex m-2 p-6 justify-center items-center">
        <div className="flex justify-center items-center gap-3">
          
          {/* username input */}
          <div className="relative flex items-center">
            <GithubIcon className="absolute left-3 w-4 h-4 text-black pointer-events-none" />
            <input
              className="pl-9 pr-3 py-2 border-2 rounded-lg border-black bg-white"
              placeholder="Enter username"
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          {/* max-icons input (compact width) */}
          <div className="relative flex items-center">
            <Hash className="absolute left-2.5 w-4 h-4 text-black pointer-events-none" />
            <input
              className="pl-8 pr-2 py-2 border-2 rounded-lg border-black bg-white w-20 text-center"
              placeholder="Max"
              onChange={(e) => setMaxCount(e.target.value)}
            />
          </div>

          {/* order by (icon-only button with floating menu below) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenOrder(!openOrder);
                setOpenTheme(false);
                setOpenShare(false);
              }}
              className="flex items-center justify-center w-10 h-10 border-2 rounded-lg border-black bg-white hover:bg-zinc-100 transition cursor-pointer"
              title={`Order: ${orderOptions.find(o => o.value === order)?.label || order}`}
            >
              <ArrowDownWideNarrow className="w-4 h-4 text-black" />
            </button>

            {openOrder && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div className="absolute left-0 top-full mt-2.5 w-40 bg-white border-2 border-black rounded-lg shadow-lg z-20 py-1">
                  {orderOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer hover:bg-zinc-100 flex items-center justify-between ${
                        order === opt.value ? "font-bold bg-zinc-50" : ""
                      }`}
                      onClick={() => {
                        setOrder(opt.value);
                        setOpenOrder(false);
                      }}
                    >
                      {opt.label}
                      {order === opt.value && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* theme (icon-only button with floating menu below) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenTheme(!openTheme);
                setOpenOrder(false);
                setOpenShare(false);
              }}
              className="flex items-center justify-center w-10 h-10 border-2 rounded-lg border-black bg-white hover:bg-zinc-100 transition cursor-pointer"
              title={`Theme: ${theme}`}
            >
              <Palette className="w-4 h-4 text-black" />
            </button>

            {openTheme && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div className="absolute left-0 top-full mt-2.5 w-36 bg-white border-2 border-black rounded-lg shadow-lg z-20 py-1">
                  {themeOptions.map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer hover:bg-zinc-100 flex items-center justify-between ${
                        theme === t ? "font-bold bg-zinc-50" : ""
                      }`}
                      onClick={() => {
                        setTheme(t);
                        setOpenTheme(false);
                      }}
                    >
                      {t}
                      {theme === t && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* share (icon-only button with floating menu below) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenShare(!openShare);
                setOpenOrder(false);
                setOpenTheme(false);
              }}
              className="flex items-center justify-center w-10 h-10 border-2 rounded-lg border-black bg-white hover:bg-zinc-100 transition cursor-pointer"
              title={`Share: ${shareVia || 'Choose option'}`}
            >
              <Share2 className="w-4 h-4 text-black" />
            </button>

            {openShare && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div className="absolute right-0 top-full mt-2.5 w-52 bg-white border-2 border-black rounded-lg shadow-lg z-20 py-1">
                  {shareOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer hover:bg-zinc-100 flex items-center justify-between ${
                        shareVia === opt.value ? "font-bold bg-zinc-50" : ""
                      }`}
                      onClick={() => {
                        SetShareVia(opt.value);
                        setOpenShare(false);
                      }}
                    >
                      {opt.label}
                      {shareVia === opt.value && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* generate button */}
          <button
            className="bg-black text-white px-4 py-2 rounded-lg hover:bg-zinc-800 transition cursor-pointer"
            onClick={handleGenerate}
          >
            Generate
          </button>

        </div>
      </section>

      <div className="ticks"></div>
      <section id="spacer"></section>
    </>
  );
}

export default App;
