from __future__ import annotations


class DomainError(Exception):
    """Base para erros de dominio."""


class PoolNotFoundError(DomainError):
    """Pool solicitada nao existe."""


class AllocationInputError(DomainError):
    """Parametros de alocacao invalidos."""


class PriceLookupDomainError(DomainError):
    """Nao foi possivel obter preco para os tokens."""


class PoolPriceInputError(DomainError):
    """Parametros invalidos para consulta de preco da pool."""


class PoolPriceNotFoundError(DomainError):
    """Nao foi possivel obter preco atual da pool."""


class LiquidityDistributionInputError(DomainError):
    """Parametros invalidos para distribuicao de liquidez."""


class LiquidityDistributionNotFoundError(DomainError):
    """Nao foi possivel montar a distribuicao para a pool."""


class MatchTicksInputError(DomainError):
    """Parametros invalidos para match de ticks."""


class DiscoverPoolsInputError(DomainError):
    """Parametros invalidos para busca no discover."""


class InvalidSimulationInputError(DomainError):
    """Parametros invalidos para simulacao de APR."""


class SimulationDataNotFoundError(DomainError):
    """Dados insuficientes para simular APR."""


class PoolVolumeHistoryInputError(DomainError):
    """Parametros invalidos para historico de volume da pool."""
