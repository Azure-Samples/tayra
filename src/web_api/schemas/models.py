"""

"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class EvaluationItem(BaseModel):
    item: str
    sub_item: str
    descricao: str
    peso: int


class Evaluation(BaseModel):
    items: List[EvaluationItem]
    pontuacao_total: int
    classificao: str
    sugestoes_melhoria: str


class AditionalEvaluation(BaseModel):
    cliente: str = Field(
        default="Não Identificado",
        description="""
        Nome do cliente, caso este seja identificado na transcrição.
        """,
    )

    tema_da_conversa: Optional[str] = Field(
        ...,
        description="""
        O tema da conversa, tratando como PESSOAL, DÚVIDA, ATENDIMENTO ou OUTRO.
        """,
    )

    propensao: Optional[str] = Field(
        ...,
        description="""
        Valida se o cliente tem ou não interesse em seguir com a sugestão, e o que, na conversa, indica que essa seria a ação.
        """,
    )


class HumanEvaluation(BaseModel):
    avaliador: str
    classificao: str
    items: List[EvaluationItem]


class UnitaryEvaluation(BaseModel):
    tipo: str
    prompt: str
    transcription: str


class TranscriptionImprovementRequest(BaseModel):
    transcription_data: str


class Transcription(BaseModel):
    id: str
    manager: str
    assistant: str
    filename: str
    transcription: str
    evaluation: Evaluation
    is_valid_call: str


class Specialist(BaseModel):
    name: str
    role: str
    transcriptions: List[Transcription]

    def total_transcriptions(self) -> int:
        return len(self.transcriptions)

    def performance(self) -> float:
        if not self.transcriptions:
            return 0.0
        total_score = sum(t.evaluation.pontuacao_total for t in self.transcriptions)
        return total_score / len(self.transcriptions)


class Manager(BaseModel):
    name: str
    role: str
    specialists: List[Specialist]

    def transcriptions(self) -> int:
        return sum(
            specialist.total_transcriptions()
            for specialist in self.specialists
        )

    def performance(self) -> float:
        total_transcriptions = sum(
            specialist.total_transcriptions()
            for specialist in self.specialists
        )
        if total_transcriptions == 0:
            return 0.0
        total_score = sum(
            specialist.performance() * specialist.total_transcriptions()
            for specialist in self.specialists
        )
        return total_score / total_transcriptions


class SubItem(BaseModel):
    sub_item: str = Field(default=None, description="Sub item avaliado")
    descricao: str = Field(default=None, description="Descrição do sub item avaliado")
    score: int = Field(default=None, description="Nota atribuída ao sub item")
    justificativa: str = Field(default=None, description="Justificativa para a nota atribuída")


class Item(BaseModel):
    item: str = Field(..., description="Nome do Item avaliado")
    descricao: str = Field(..., description="Descrição do item avaliado")
    score: int = Field(..., description="Nota atribuída ao item")
    justificativa: str = Field(..., description="Justificativa para a nota atribuída")
    sub_item: List[SubItem] = Field(..., description="Lista dos sub itens avaliados")
