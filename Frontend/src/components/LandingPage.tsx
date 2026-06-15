import React, { useState } from "react";
import { BookOpen, Activity, Scale, BellRing, ArrowRight, ChevronRight, CheckCircle, Sparkles, Search } from "lucide-react";
import { motion } from "motion/react";

interface LandingPageProps {
  onSelectSuggestion: (text: string) => void;
  setTab: (tab: string) => void;
  setPreSelectedDocType: (type: string | null) => void;
}

export default function LandingPage({
  onSelectSuggestion,
  setTab,
  setPreSelectedDocType,
}: LandingPageProps) {
  const [queryInput, setQueryInput] = useState("");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (queryInput.trim()) {
      onSelectSuggestion(queryInput);
    }
  };

  const handleCardClick = (tabId: string, filterType?: string) => {
    if (filterType) {
      setPreSelectedDocType(filterType);
    }
    setTab(tabId);
  };

  return (
    <div className="flex-1 bg-[#f8f9fa]">
      {/* Hero Section */}
      <section className="relative min-h-[580px] flex flex-col items-center justify-center px-4 md:px-16 py-16 text-center select-none overflow-hidden bg-[radial-gradient(circle_at_top_right,_#1a428a_0%,_#0D2D5E_70%)]">
        {/* Abstract atmospheric grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,_transparent_1px),_linear-gradient(90deg,_rgba(255,255,255,0.02)_1px,_transparent_1px)] bg-[size:40px_40px] pointer-events-none opacity-50" />
        
        {/* Glow vector effect */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-[#C8971A]/10 rounded-full blur-[140px] pointer-events-none" />

        <div className="relative z-10 w-full max-w-4xl flex flex-col items-center">
          {/* Tag */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 bg-[#C8971A]/10 border border-[#C8971A]/30 rounded-full px-4 py-1.5 mb-8 animate-pulse"
          >
            <span className="w-2 h-2 rounded-full bg-[#C8971A]" />
            <span className="text-[#C8971A] font-sans font-bold text-xs uppercase tracking-wider">
              Nouveau — Intelligence Artificielle
            </span>
          </motion.div>

          {/* Heading */}
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="font-sans text-white text-3xl md:text-5xl font-extrabold tracking-tight mb-6 leading-tight max-w-3xl"
          >
            Accédez au patrimoine financier avec l'
            <span className="text-[#C8971A]">Assistant IA</span> de la BEAC
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.22 }}
            className="font-sans text-white/70 text-base md:text-lg mb-10 max-w-2xl leading-relaxed"
          >
            Une interface conversationnelle de pointe pour interroger les bases de données institutionnelles, les rapports économiques et les réglementations monétaires de la zone CEMAC.
          </motion.p>

          {/* Search Box */}
          <motion.form
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            onSubmit={handleSearchSubmit}
            className="w-full max-w-2xl bg-white rounded-xl p-2 shadow-2xl flex items-center border border-white/10"
          >
            <div className="flex-1 flex items-center px-4">
              <Search className="text-black/40 w-5 h-5 flex-shrink-0" />
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Posez une question sur l'économie de la zone CEMAC..."
                className="w-full border-none focus:outline-none focus:ring-0 text-black placeholder:text-black/40 py-3 pl-3 font-sans text-sm md:text-base bg-transparent font-medium"
              />
            </div>
            <button
              type="submit"
              className="bg-[#C8971A] text-[#0D2D5E] w-12 h-12 flex items-center justify-center rounded-lg hover:bg-[#F2B824] transition-all cursor-pointer shadow-md select-none shrink-0"
              title="Envoyer la question à l'Assistant"
            >
              <Sparkles className="w-5 h-5" />
            </button>
          </motion.form>

          {/* Quick suggestions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.9, delay: 0.44 }}
            className="flex flex-wrap justify-center gap-3 mt-8"
          >
            {[
              "Taux d'inflation actuel",
              "Réglementation bancaire",
              "Rapports annuels 2023",
            ].map((text, idx) => (
              <button
                key={idx}
                onClick={() => onSelectSuggestion(text)}
                className="bg-white/5 backdrop-blur-md border border-[#C8971A]/20 hover:border-[#C8971A]/50 text-white/90 hover:bg-white/10 px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all duration-300 flex items-center gap-1.5 focus:outline-none focus:ring-1 focus:ring-[#C8971A]/50 cursor-pointer"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#C8971A]/60" />
                {text}
              </button>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Access Cards Grid */}
      <section className="max-w-[1280px] mx-auto px-4 md:px-16 py-20">
        <div className="flex justify-between items-end mb-12 flex-wrap gap-4">
          <div>
            <h2 className="font-sans text-[#0D2D5E] text-2xl md:text-3xl font-extrabold tracking-tight mb-2">
              Accès Rapide
            </h2>
            <p className="text-black/60 font-sans text-sm font-medium">
              Explorez nos ressources institutionnelles certifiées et restez informé des évolutions macroéconomiques.
            </p>
          </div>
          <button
            onClick={() => handleCardClick("bibliotheque")}
            className="text-[#C8971A] hover:text-[#F2B824] font-semibold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all select-none hover:underline cursor-pointer group"
          >
            Voir tout{" "}
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 - Bibliothèque */}
          <div
            onClick={() => handleCardClick("bibliotheque")}
            className="bg-white p-8 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] transition-all duration-300 group cursor-pointer relative overflow-hidden flex flex-col justify-between hover:shadow-lg hover:shadow-[#0d2d5e]/5"
          >
            <div>
              <div className="w-12 h-12 bg-[#C8971A]/10 text-[#C8971A] flex items-center justify-center mb-6 rounded-lg transition-all duration-300 group-hover:scale-110 group-hover:bg-[#C8971A]/20">
                <BookOpen className="w-6 h-6 stroke-[2]" />
              </div>
              <h3 className="font-sans text-[#0D2D5E] text-lg font-bold mb-3">
                Bibliothèque Numérique
              </h3>
              <p className="text-black/60 font-sans text-xs line-clamp-3 leading-relaxed mb-6">
                Accédez aux archives historiques, statistiques monétaires consolidées et documents officiels de la Commission Bancaire et de la Banque Centrale.
              </p>
            </div>
            <div className="flex items-center text-[#C8971A] font-bold text-xs tracking-wider uppercase gap-1 group-hover:underline mt-auto">
              Explorer <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Card 2 - Indicateurs */}
          <div
            onClick={() => handleCardClick("dashboard")}
            className="bg-white p-8 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] transition-all duration-300 group cursor-pointer relative overflow-hidden flex flex-col justify-between hover:shadow-lg hover:shadow-[#0d2d5e]/5"
          >
            <div>
              <div className="w-12 h-12 bg-[#0D2D5E]/10 text-[#0D2D5E] flex items-center justify-center mb-6 rounded-lg transition-all duration-300 group-hover:scale-110 group-hover:bg-[#0D2D5E]/15">
                <Activity className="w-6 h-6 stroke-[2]" />
              </div>
              <h3 className="font-sans text-[#0D2D5E] text-lg font-bold mb-3">
                Indicateurs Économiques
              </h3>
              <p className="text-black/60 font-sans text-xs line-clamp-3 leading-relaxed mb-6">
                Visualisez les données macroéconomiques, l'historique d'inflation sectorielle et les agrégats de politique monétaire de la zone CEMAC.
              </p>
            </div>
            <div className="flex items-center text-[#C8971A] font-bold text-xs tracking-wider uppercase gap-1 group-hover:underline mt-auto">
              Analyser <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Card 3 - Cadre réglementaire */}
          <div
            onClick={() => handleCardClick("bibliotheque", "Réglementation")}
            className="bg-white p-8 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] transition-all duration-300 group cursor-pointer relative overflow-hidden flex flex-col justify-between hover:shadow-lg hover:shadow-[#0d2d5e]/5"
          >
            <div>
              <div className="w-12 h-12 bg-[#C8971A]/10 text-[#C8971A] flex items-center justify-center mb-6 rounded-lg transition-all duration-300 group-hover:scale-110 group-hover:bg-[#C8971A]/20">
                <Scale className="w-6 h-6 stroke-[2]" />
              </div>
              <h3 className="font-sans text-[#0D2D5E] text-lg font-bold mb-3">
                Cadre Réglementaire
              </h3>
              <p className="text-black/60 font-sans text-xs line-clamp-3 leading-relaxed mb-6">
                Consultez les textes fondamentaux de l'UMAC, les règlements de la COBAC, et les décisions réglementaires régissant la liquidité bancaire régionale.
              </p>
            </div>
            <div className="flex items-center text-[#C8971A] font-bold text-xs tracking-wider uppercase gap-1 group-hover:underline mt-auto">
              Consulter <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Card 4 - Notifications / Actualités */}
          <div
            onClick={() => handleCardClick("bibliotheque", "Communiqués")}
            className="bg-white p-8 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] transition-all duration-300 group cursor-pointer relative overflow-hidden flex flex-col justify-between hover:shadow-lg hover:shadow-[#0d2d5e]/5"
          >
            <div>
              <div className="w-12 h-12 bg-[#0D2D5E]/10 text-[#0D2D5E] flex items-center justify-center mb-6 rounded-lg transition-all duration-300 group-hover:scale-110 group-hover:bg-[#0D2D5E]/15">
                <BellRing className="w-6 h-6 stroke-[2]" />
              </div>
              <h3 className="font-sans text-[#0D2D5E] text-lg font-bold mb-3">
                Actualités &amp; Avis
              </h3>
              <p className="text-black/60 font-sans text-xs line-clamp-3 leading-relaxed mb-6">
                Restez informé des derniers communiqués de presse, annonces d'appels d'offres hebdomadaires et rapports du Comité de Politique Monétaire.
              </p>
            </div>
            <div className="flex items-center text-[#C8971A] font-bold text-xs tracking-wider uppercase gap-1 group-hover:underline mt-auto">
              Lire la suite <ChevronRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      </section>

      {/* Feature Spotlight Section */}
      <section className="bg-[#edeeef] py-20 border-t border-b border-[#c4c6d0]/30 select-none">
        <div className="max-w-[1280px] mx-auto px-4 md:px-16 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="relative rounded-2xl overflow-hidden shadow-2xl aspect-video border border-[#c4c6d0]/50 bg-white">
            <img
              className="w-full h-full object-cover"
              referrerPolicy="no-referrer"
              alt="Dashboard de données de la BEAC"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAYkB_V7mxaErTHKoGuUkMYV3hC3W-6z1YebPQ9ZSQ7011iqmubz_hwRZWGAbdFnNR5ae6fTZ9aXRoKKJ4KvksGICT26jq4pgG3akd2sVAH024i3-6QW4Y_h_SlZcGgyo9BaAdD0PQ_F_PVLwKn1-PfEpF0V9Fi3hokIQ-uYHggpQE9bCm8WhqyoLX0-fWebsF-pQ30LUE4ZxdYMHbqxg4pQwgX8sDtbmqcNjNzOuKypJRAKfHprzXjq8DqbNa6CSzTMuO0pOfJf7c"
            />
            <div className="absolute inset-0 bg-[#0D2D5E]/10" />
            <div className="absolute bottom-4 left-4 right-4 p-4 md:p-6 bg-white/5 backdrop-blur-md rounded-xl border border-white/20 shadow-lg shadow-black/10">
              <div className="text-[#C8971A] font-sans font-bold text-[10px] md:text-xs uppercase tracking-wider mb-1">
                Technologie de pointe
              </div>
              <div className="text-white font-sans font-extrabold text-sm md:text-base leading-tight">
                Analyse sémantique des données monétaires régionales
              </div>
            </div>
          </div>

          <div>
            <h2 className="font-sans text-[#0D2D5E] text-2xl md:text-3xl font-extrabold tracking-tight mb-6">
              Une Intelligence au service de la Zone CEMAC
            </h2>
            <p className="font-sans text-black/70 text-sm md:text-base mb-8 leading-relaxed">
              L'Assistant IA de la BEAC n'est pas seulement un chatbot. C'est un moteur d'analyse sémantique instruit sur des décennies de rapports macroéconomiques régionaux, conçu pour offrir une clarté et une rigueur technique sans précédent.
            </p>

            <ul className="space-y-4 mb-10">
              {[
                "Précision institutionnelle garantie par les bases documentaires BEAC.",
                "Support multilingue et sémantique pour l'unification monétaire régionale.",
                "Disponibilité permanente 24h/24 et 7j/7 pour vos recherches stratégiques."
              ].map((text, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <CheckCircle className="text-[#C8971A] w-5 h-5 stroke-[2.5] shrink-0 mt-0.5" />
                  <span className="font-sans text-sm text-black/85 font-medium leading-tight">
                    {text}
                  </span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleCardClick("chat")}
              className="bg-[#0D2D5E] hover:bg-[#00183e] text-white font-sans font-bold text-xs uppercase tracking-wider px-8 py-4 rounded-lg transition-all active:scale-[0.98] shadow-md flex items-center gap-2 cursor-pointer"
            >
              Lancer l'Assistant IA
              <Sparkles className="w-4 h-4 text-[#C8971A] fill-current" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
