import React from "react";

export default function Footer() {
  return (
    <footer className="w-full py-8 px-6 md:px-16 mt-auto flex flex-col md:flex-row justify-between items-center bg-[#e1e3e4] border-t border-[#c4c6d0]">
      <div className="flex flex-col items-center md:items-start mb-6 md:mb-0 select-none text-center md:text-left">
        <span className="font-sans text-[#0D2D5E] font-bold text-lg tracking-wider">BEAC</span>
        <span className="text-xs text-black/60 font-medium mt-1">
          © 2024 - 2026 Banque des États de l'Afrique Centrale. Tous droits réservés.
        </span>
      </div>
      <div className="flex flex-wrap justify-center gap-6 md:gap-8">
        <a href="#mentions" className="text-xs font-semibold text-black/60 hover:text-[#0D2D5E] transition-colors">
          Mentions Légales
        </a>
        <a href="#privacy" className="text-xs font-semibold text-black/60 hover:text-[#0D2D5E] transition-colors">
          Politique de Confidentialité
        </a>
        <a href="#contact" className="text-xs font-semibold text-black/60 hover:text-[#0D2D5E] transition-colors">
          Contacter le Support
        </a>
      </div>
    </footer>
  );
}
