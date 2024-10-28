"use client";
import { useRouter } from 'next/navigation';
import { useTranscriptionContext } from "@/utils/transcriptionContext";
import Breadcrumb from "@/components/Breadcrumbs/Breadcrumb";
import DefaultLayout from "@/components/Layouts/DefaultLayout";
import Transcription from '@/components/Transcriptions';

const TranscriptionPage: React.FC = () => {
  const { selectedTranscription } = useTranscriptionContext();
  const router = useRouter();

  const handleBack = () => {
    router.back();  // Volta para a página anterior
  };

  if (!selectedTranscription) {
    return (
      <DefaultLayout>
        <Breadcrumb pageName="Avaliar Transcrição" />
        <button
            onClick={handleBack} // Ação do botão de voltar
            className="mb-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
          Voltar
        </button>
        <div className="p-6 bg-white dark:bg-gray-800">
          <p>Transcrição Não Encontrada.</p>
        </div>
      </DefaultLayout>
    );
  }

  return (
    <DefaultLayout>
      <Breadcrumb pageName="Avaliar Transcrição" />
      <button
          onClick={handleBack} // Ação do botão de voltar
          className="mb-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
        Voltar
      </button>
      <div className="p-6 bg-white dark:bg-gray-800">
        <Transcription transcription={selectedTranscription} />
      </div>
    </DefaultLayout>
  );
};

export default TranscriptionPage;
