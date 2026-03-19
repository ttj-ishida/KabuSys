# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。新規リリース 0.1.0 はパッケージ内部の主要機能実装に相当する初回リリースです。

全体方針:
- DuckDB をデータ層に用いる設計（Raw / Processed / Feature / Execution の 3 層構造を想定）
- 本番発注 API にはアクセスしない Data / Research 層と、発注/監視のためのモジュール境界を明確化
- セキュリティと堅牢性を重視（RSS の SSRF 対策、XML パースの安全化、API のリトライ/トークン刷新、.env の安全な読み込みなど）
- 外部依存は最小限（標準ライブラリ中心、ただし duckdb / defusedxml を利用）

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン定義（__version__ = "0.1.0"）。
  - export されるサブパッケージ一覧（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py を追加
    - .env と .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
    - POSIX 形式の .env パース機能（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート）。
    - Settings クラスで主要設定値をプロパティ経由で提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- Data レイヤー
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔レートリミッタ（120 req/min）実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。429 時は Retry-After を尊重。
    - 401 受信時の自動トークンリフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の取得関数（fetch_daily_quotes, fetch_financial_statements）。
    - JPX マーケットカレンダー取得（fetch_market_calendar）。
    - DuckDB への永続化関数（save_daily_quotes, save_financial_statements, save_market_calendar）により冪等性を確保（ON CONFLICT DO UPDATE）。
    - JSON/HTTP のデコードや数値パースを安全に行うユーティリティ（_to_float, _to_int）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードの取得と前処理、raw_news への冪等保存（INSERT ... RETURNING を用いる設計）。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の防御）。
      - SSRF 対策: リダイレクト先のスキーム検証とプライベート IP 判定（_SSRFBlockRedirectHandler / _is_private_host）。
      - URL スキーム制限（http/https のみ）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査。
      - トラッキングパラメータ除去と URL 正規化（_normalize_url）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes）とニュース記事と銘柄の紐付け保存（news_symbols 保存機能）。
    - バルクインサート用チャンク処理とトランザクション管理により高効率な DB 保存を実装。

  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - raw_prices / raw_financials / raw_news / raw_executions 等の初期 CREATE TABLE DDL を定義（Raw Layer のテーブル定義を実装）。
    - スキーマ初期化用の基盤を用意（テーブルの整合性制約や主キー定義含む）。

- Research（特徴量・ファクター計算）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)：指定日から複数ホライズンの将来リターンを DuckDB で一度に取得する実装。
    - IC（Information Coefficient）計算 (calc_ic)：ファクターと将来リターンのスピアマンランク相関を計算。データ不足時は None を返す。
    - 基本統計サマリー (factor_summary)：count/mean/std/min/max/median を算出。
    - ランク計算ユーティリティ (rank)。
    - 性能と数値安定性を考慮した実装（丸め誤差対策、欠損/非有限値の除外）。
  - src/kabusys/research/factor_research.py
    - モメンタム計算 (calc_momentum)：1M/3M/6M リターン、200日移動平均乖離率を計算。
    - ボラティリティ / 流動性計算 (calc_volatility)：20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - バリュー計算 (calc_value)：raw_financials から直近の財務データを取得して PER/ROE を計算（EPS 欠損や 0 対策あり）。
    - DuckDB の窓関数を活用した効率的な SQL ベース実装。
  - src/kabusys/research/__init__.py で研究用関数群をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, および external zscore_normalize の参照）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- RSS パーサと HTTP クライアント周りで以下を考慮:
  - defusedxml による安全な XML パース。
  - SSRF 対策: リダイレクト先の検査、プライベート IP 拒否、スキームの制限。
  - レスポンスサイズ上限と gzip 解凍後の再検査（Gzip Bomb 対策）。
- J-Quants クライアントでの認証トークン管理と 401 トークンリフレッシュの自動化により誤認証時の安全な再試行を実現。

### Notes / Limitations
- strategy, execution, monitoring サブパッケージは __all__ に定義されているものの、今回は基盤のみ（__init__.py が存在）で詳細な発注ロジックや監視機能の実装は含まれていません。
- research/__init__.py は kabusys.data.stats の zscore_normalize を参照していますが、その実装（data.stats）はこの差分に含まれていません。実運用では統計ユーティリティの追加が必要です。
- DuckDB スキーマ定義は Raw 層の主要テーブルを含みますが、Processed / Feature / Execution 層の細部 DDL は今後の拡張対象です。
- J-Quants クライアントは urllib を使った実装であり、高度な非同期用途や大量同時リクエストには別途検討が必要です（ただしレート制限を組み込んでいるため一般的なバッチ取得は想定済み）。

---

今後の予定（例）
- 発注/約定管理（execution）とポジション管理の実装
- モニタリング/アラート（Slack 通知等）の実装
- data.stats（zscore 等）の提供と Research の追加指標
- DuckDB スキーマの拡張（Feature 層、Processed 層の DDL 完成）
- 単体テストと CI 設定の追加

もし CHANGELOG に追記してほしい観点（リリース日変更、より詳しい技術的注記、既知のバグ一覧など）があれば教えてください。