"use client";
import { useState } from "react";
import Image from "next/image";
import Link from 'next/link';
import api from "@/utils/api"; // Import your axios instance
import { Manager } from "@/types/manager";
import { Specialist } from "@/types/specialist";


const managersList = [
  { name: "" },
  { name: "" },
  { name: "" },
  { name: "" },
  { name: "" },
  { name: "" },
  { name: "" },
  { name: "" },
];

const CardLayout = () => {
  const [selectedManager, setSelectedManager] = useState<Manager | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCardClick = async (managerName: string) => {
    setLoading(true);
    try {
      const response = await api.get(`/overlooker-data?manager=${encodeURIComponent(managerName)}`);
      const managerData = response.data.result[managerName];
      if (managerData) {
        setSelectedManager({
          ...managerData,
          specialists: managerData.specialists.map((specialist: Specialist) => ({
            ...specialist,
            image: "/images/users/user-02.png", // Placeholder image; replace with real data if available
          })),
        });
      }
    } catch (error) {
      console.error("Failed to fetch manager data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleBackClick = () => {
    setSelectedManager(null);
  };

  if (loading) {
    return <p>Carregando...</p>;
  }

  return (
    <div className="rounded-sm border border-stroke bg-white shadow-default dark:border-strokedark dark:bg-boxdark">
      <div className="px-4 py-6 md:px-6 xl:px-7.5 flex justify-between items-center">
        <div className="flex flex-col">
          <h4 className="text-xl font-semibold text-black dark:text-white">
            {selectedManager ? selectedManager.name : "Gerentes"}
          </h4>
          {selectedManager && (
            <>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                Total de Transcrições: {selectedManager.transcriptions}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                Performance Média da Equipe: {selectedManager.performance}
              </p>
            </>
          )}
        </div>
        
        {selectedManager && (
          <button
            onClick={handleBackClick}
            className="text-sm bg-meta-4 text-white py-2 px-4 rounded hover:bg-red"
          >
            Ver todos os gerentes
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-2 p-4">
        {selectedManager
          ? selectedManager.specialists.map((specialist, key) => (
            <Link
              href={`/specialists/${specialist.name}`}
              key={key}
            >
              <div
                className="flex flex-col sm:flex-row items-center border border-stroke p-4 rounded-lg dark:border-strokedark dark:bg-boxdark hover:shadow-lg hover:bg-gray transition-shadow"
              >
                <div className="flex flex-col flex-1 sm:order-1">
                  <h5 className="text-lg font-bold text-black dark:text-white">
                    {specialist.name}
                  </h5>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    {specialist.role}
                  </p>
                  <div className="flex justify-between items-center mt-auto">
                    <p className="text-sm text-black dark:text-white">
                      {specialist.transcriptions} Transcrições
                    </p>
                    <p className="text-sm text-black dark:text-white">
                      Pontuação Média: {specialist.performance.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            </Link>
          ))
          : managersList.map((manager, key) => (
              <div
                className="flex flex-col sm:flex-row items-center border border-stroke p-4 rounded-lg dark:border-strokedark dark:bg-boxdark hover:shadow-lg hover:bg-gray transition-shadow"
                key={key}
                onClick={() => handleCardClick(manager.name)}
              >
                <div className="sm:order-2 sm:ml-4">
                  <Image
                    src="/images/user/best-manager.png"
                    width={100}
                    height={100}
                    alt={manager.name}
                    className="rounded-lg"
                  />
                </div>
                <div className="flex flex-col flex-1 sm:order-1">
                  <h5 className="text-lg font-bold text-black dark:text-white">
                    {manager.name}
                  </h5>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    Gerente
                  </p>
                </div>
              </div>
            ))}
      </div>
    </div>
  );
};

export default CardLayout;