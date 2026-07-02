import { useState } from "react";
import { Bell, User, Search, Sparkles, Menu, X } from "lucide-react";
import beacLogo from "../../assets/logo_BEAC.png";

interface HeaderProps {
  currentTab: string;
  setTab: (tab: string) => void;
  onOpenAdminLogin: () => void;
  isAdminLoggedIn: boolean;
  onLogoutAdmin: () => void;
}

export default function Header({
  currentTab,
  setTab,
  onOpenAdminLogin,
  isAdminLoggedIn,
  onLogoutAdmin,
}: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const handleNavClick = (tab: string) => {
    setTab(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="fixed top-0 w-full z-50 flex justify-between items-center h-16 bg-[#0D2D5E] border-b border-[#C8971A]/20 px-4 md:px-8 lg:px-16 transition-all duration-200">
      {/* Left items - Logo & Nav */}
      <div className="flex items-center gap-6">
        <button
          onClick={() => handleNavClick("accueil")}
          className="flex items-center gap-2 md:gap-3 text-left focus:outline-none focus:ring-2 focus:ring-[#C8971A]/30 p-1 rounded"
        >
          <div className="w-20 h-20 flex items-center justify-center">
            <img src={beacLogo} alt="Logo BEAC" className="w-full h-full object-contain" />
          </div>
          <div className="flex flex-col leading-tight select-none">
            <span className="font-sans font-bold text-base md:text-lg text-[#C8971A] tracking-tight">BEAC</span>
            <span className="text-[9px] md:text-[10px] text-white/70 tracking-widest font-semibold font-sans">Assistant IA</span>
          </div>
        </button>

        {/* Desktop Navigation Links */}
        <nav className="hidden lg:flex gap-6 ml-8">
          {[
            { id: "accueil", label: "Accueil" },
            { id: "chat", label: "Chat" },
            { id: "bibliotheque", label: "Bibliothèque" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={`font-sans text-sm font-medium transition-all duration-200 pb-1 cursor-pointer relative ${
                currentTab === item.id
                  ? "text-[#C8971A] font-semibold"
                  : "text-white/80 hover:text-[#C8971A]"
              }`}
            >
              {item.label}
              {currentTab === item.id && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#C8971A] rounded-full animate-fade-in" />
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Right items - Search, Actions, Profile */}
      <div className="flex items-center gap-4">
        {/* Desktop Search */}
        <div
          className={`hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 border transition-all duration-300 ${
            searchFocused ? "bg-white/15 border-[#C8971A]/50 w-72" : "border-transparent w-48"
          }`}
        >
          <Search className="text-white/60 w-4 h-4" />
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="bg-transparent border-none text-white focus:outline-none placeholder:text-white/40 text-xs w-full py-0"
          />
        </div>

        {/* AI Assistant shortcut */}
        <button
          onClick={() => handleNavClick("chat")}
          className="bg-[#C8971A] text-[#0D2D5E] font-semibold text-xs py-2 px-3 lg:px-4 rounded-lg hover:bg-[#F2B824] transition-all active:scale-95 flex items-center gap-1.5 shadow-lg shadow-[#C8971A]/20 cursor-pointer animate-fade-in"
        >
          <Sparkles className="w-3.5 h-3.5 fill-current" />
          <span className="hidden lg:inline">Assistant IA</span>
        </button>

        {/* Notifications & Admin Area */}
        <div className="flex items-center gap-2 text-white/80 border-l border-white/10 pl-3">
          <button className="text-white/80 hover:text-[#C8971A] transition-colors p-1.5 rounded relative cursor-pointer">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-[#C8971A] rounded-full" />
          </button>

          {isAdminLoggedIn ? (
            <div className="flex items-center gap-2 pl-1 select-none">
              <button
                onClick={() => handleNavClick("dashboard")}
                className="w-7 h-7 rounded-full bg-[#C8971A]/20 border border-[#C8971A]/40 flex items-center justify-center font-bold text-xs text-[#C8971A]"
                title="Tableau de bord administration"
              >
                AD
              </button>
              <button
                onClick={onLogoutAdmin}
                className="hidden lg:block text-[11px] text-white/60 hover:text-[#C8971A] underline transition-colors cursor-pointer"
              >
                Déconnexion
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAdminLogin}
              className="text-white/80 hover:text-[#C8971A] transition-colors p-1.5 rounded cursor-pointer"
              title="Accès Administrateur"
            >
              <User className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Mobile menu toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden text-white/80 hover:text-[#C8971A] p-1.5 transition-colors cursor-pointer"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer menu */}
      {mobileMenuOpen && (
        <div className="absolute top-16 left-0 right-0 bg-[#0D2D5E] border-b border-[#C8971A]/30 py-4 px-6 flex flex-col gap-4 shadow-xl z-50 lg:hidden animate-slide-down">
          {[
            { id: "accueil", label: "Accueil" },
            { id: "chat", label: "Assistant IA" },
            { id: "bibliotheque", label: "Bibliothèque" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={`text-left font-sans py-2 text-sm font-semibold transition-colors ${
                currentTab === item.id ? "text-[#C8971A]" : "text-white/85 hover:text-[#C8971A]"
              }`}
            >
              {item.label}
            </button>
          ))}
          {!isAdminLoggedIn ? (
            <button
              onClick={() => {
                onOpenAdminLogin();
                setMobileMenuOpen(false);
              }}
              className="text-left font-sans py-2 text-sm font-semibold text-white/60 hover:text-[#C8971A] border-t border-white/10 pt-4"
            >
              Se Connecter (Administration)
            </button>
          ) : (
            <button
              onClick={() => {
                onLogoutAdmin();
                setMobileMenuOpen(false);
              }}
              className="text-left font-sans py-2 text-sm font-semibold text-red-400 hover:text-red-300 border-t border-white/10 pt-4"
            >
              Se déconnecter (Admin: DSI)
            </button>
          )}
        </div>
      )}
    </header>
  );
}
