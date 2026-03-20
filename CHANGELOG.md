# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加（kabusys v0.1.0）。
  - パッケージ公開情報: __version__ = "0.1.0"。トップレベル __all__ に data, strategy, execution, monitoring を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサはコメント行・export プレフィックス・クォート文字列（エスケープ対応）・インラインコメント処理に対応。
  - protected（OS 環境）キーを尊重した上書き制御（override パラメータ）。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティ。
    - env / log_level の値検証（許容値チェック）。
    - is_live/is_paper/is_dev の利便性プロパティ。
  - 必須環境変数未設定時は明確な ValueError を投げる _require を実装。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。
    - 401 受信時はトークン自動リフレッシュを行い再試行（ただし無限再帰を避ける設計）。
    - ページネーション対応とモジュールレベルの ID トークンキャッシュ。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存ユーティリティを提供（冪等実装: ON CONFLICT / DO UPDATE または DO NOTHING を利用）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - fetched_at は UTC で記録（Look-ahead バイアス対策）。
  - HTTP/レスポンス/データ変換ユーティリティを実装:
    - 安全な JSON デコードエラー報告、Retry-After ヘッダ処理、ネットワーク例外処理。
    - _to_float / _to_int による堅牢な型変換（空文字や不正値は None）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ冪等保存する仕組みを実装。
    - デフォルトソースに Yahoo Finance のビジネス RSS を含む。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や defusedxml による XML 攻撃対策を導入。
    - 記事ID は URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - トラッキングパラメータ（utm_*, fbclid など）を除去する URL 正規化、スキームホワイトリスト、SSR F対策を想定。
    - バルク INSERT チャンク化による性能配慮（_INSERT_CHUNK_SIZE）。

- リサーチモジュール（kabusys.research）
  - ファクター計算・探索用ユーティリティ群を追加。
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。
      - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA のデータ不足時は None）。
      - Volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、volume_ratio。
      - Value: per（株価 / EPS）、roe（raw_financials から最新レコードを参照）。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照し外部依存を持たない設計。
  - feature_exploration:
    - calc_forward_returns: target_date から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - horizons のバリデーション（正の整数かつ <= 252）。
    - calc_ic: スピアマンのランク相関（IC）を実装。サンプル数が 3 未満の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count, mean, std, min, max, median）を計算。
    - 外部ライブラリに依存しない純正 Python 実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した raw ファクターをマージ・フィルタ・正規化して features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 >= 5 億円。
    - 正規化: zscore_normalize を用いて指定列を Z スコア化し ±3 でクリップ（外れ値抑制）。
    - 処理は日付単位の置換（DELETE + bulk INSERT）で冪等性・原子性を保証（トランザクション）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し最終スコア（final_score）を計算、BUY / SELL シグナルを生成して signals テーブルへ保存する処理を実装（generate_signals）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を算出。
      - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均。
      - value: PER を 20 を基準に変換（PER→0 に近づくほど高スコア）。
      - volatility: atr_pct の Z スコアを反転してシグモイド変換（低ボラティリティが高スコア）。
      - liquidity: volume_ratio のシグモイド。
      - news: ai_score をシグモイド変換（未登録は中立）。
    - 欠損コンポーネントは中立値 0.5 で補完（不当な降格を防止）。
    - デフォルト重みや閾値を定義（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60）。
    - ユーザーからの weights は検証・フィルタリングされ、合計が 1.0 になるよう再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつ十分なサンプル数（>=3）なら BUY を抑制。
    - SELL 条件（実装済み）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score が閾値未満
      - （未実装）トレーリングストップや時間決済は positions に追加情報が必要で保留。
    - signals テーブルへの書き込みは日付単位の置換（トランザクション + bulk INSERT）で冪等性を保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パースに defusedxml を使用、受信バッファ制限や URL 正規化など SSRF / XML-Bomb 対策を導入。
- API クライアントでトークン・リトライ処理を厳格に制御し認証フローの誤用を防止。

### Notes / Migration
- DuckDB 側のテーブルスキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar / raw_news 等）は本パッケージの関数群が参照・更新する前提で整備しておく必要があります。  
- news_collector の ID は URL 正規化後のハッシュを使用するため、既存システムと互換性を持たせる際は正規化ロジックを合わせてください。  
- generate_signals や build_features は target_date 時点のデータのみを利用する（ルックアヘッドバイアス対策）。運用時は prices_daily / raw_financials / ai_scores のタイムラインを適切に管理してください。

---

（初回リリース — 主要なデータ取得、前処理、ファクター計算、シグナル生成のワークフローを実装）