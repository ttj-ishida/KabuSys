# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルにはパッケージ kabusys の初期リリース（v0.1.0）で導入された主要機能、実装上の注意点、移行/設定の手順やセキュリティに関する注記を日本語でまとめています。

現在のバージョン: 0.1.0 - 初回リリース

## [Unreleased]
（将来の変更点をここに記載）

## [0.1.0] - 2026-03-19

### Added
- パッケージ基本情報
  - パッケージ初期化: src/kabusys/__init__.py にて __version__="0.1.0"、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
    - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env のパースは export プレフィックス、クォート、インラインコメント、escaped 文字列などに対応。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得時の _require() と複数のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、データベースパス、ログ・環境種別判定など）を提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証（不正値は ValueError を送出）。
- データ取得 / 保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API 向けクライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）で API 呼び出しを制御。
    - HTTP リトライロジック（指数バックオフ、最大 3 回）。429 の場合は Retry-After を優先。
    - 401 エラー時にリフレッシュトークンを用いて id_token を自動更新して再試行する仕組み。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar）を実装。ON CONFLICT で更新することで重複を排除。
    - ユーティリティ _to_float / _to_int により入力変換を厳密に扱う。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース取得と DuckDB への保存機能を実装。
    - XML パーサに defusedxml を利用して XML 攻撃耐性を確保。
    - URL 正規化（トラッキングパラメータ除去、クエリソート）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト先のスキーム・ホスト検証を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカルの場合はアクセスを拒否（DNS 解決して A/AAAA をチェック）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10 MiB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - RSS のパースに失敗した場合はログ出力して安全にスキップ。
    - raw_news へ INSERT ... RETURNING を使って新規挿入された記事IDを取得する save_raw_news、news_symbols への紐付け保存を行う save_news_symbols/_save_news_symbols_bulk を実装。
    - テキスト前処理（URL 削除、空白正規化）と、本文から銘柄コード（4桁数字）の抽出ユーティリティ extract_stock_codes を提供。
    - run_news_collection で複数ソースの収集を行い、個別ソースの失敗が全体に影響しないように設計。
- 研究用ファクター / 特徴量探索
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づく定量ファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。NULL 管理に注意した実装。
      - calc_value: raw_financials から直近の財務データを取得し PER（EPS が 0/欠損なら None）、ROE を計算。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照するように設計（外部APIアクセスなし）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定日から将来ホライズン（デフォルト [1,5,21]）のリターンを一括 SQL で取得する実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。レコード不足（<3）や同一値分散ゼロの場合は None を返す。
    - rank: タイ（同値）は平均順位で扱うランク化ユーティリティ（丸め誤差対策に round(v,12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー関数。
    - 研究モジュールは標準ライブラリのみで実装されるように意図されている（pandas 等に依存しない）。
  - src/kabusys/research/__init__.py で主要関数を公開（calc_momentum 等、zscore_normalize は kabusys.data.stats から）。
- スキーマ定義 / 初期化
  - src/kabusys/data/schema.py
    - DuckDB 向けのテーブル DDL（Raw Layer を中心に raw_prices / raw_financials / raw_news / raw_executions 等の定義）を追加。
    - DataSchema.md に沿った Raw / Processed / Feature / Execution の多層構造を想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集モジュールにおける複数のセキュリティ対策を導入:
  - defusedxml による XML パース（XML Bomb や外部エンティティ攻撃への対策）。
  - SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト時の検査）。
  - レスポンスサイズ制限・gzip 解凍後の検証（メモリ DoS / Gzip bomb 対策）。
- J-Quants クライアントはトークン自動リフレッシュと厳格なリトライ/レート制御を備え、API レート制限と認証失敗に対処。

### Notes / Migration / Usage
- 環境変数
  - 本システムを動作させるために次の環境変数が必須です（設定されていない場合は Settings のプロパティアクセスで ValueError が発生します）:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - デフォルトの DB パス:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
  - 自動 .env ロードを抑止する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定する必要があります（小文字でも可）。不正な値は ValueError。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか（大文字へ正規化）。不正な値は ValueError。
- DuckDB スキーマ初期化
  - schema モジュールに DDL が定義されています。初期化時にはこれらの DDL を用いてテーブルを作成してください（既存データがある環境では ON CONFLICT やバックアップに留意してください）。
- 研究モジュールの注意
  - calc_* 関数群は prices_daily / raw_financials といった DuckDB テーブルに依存します。関数は外部 API を呼ばないため、オフラインな解析環境でも使用可能です。
  - 研究用関数は pandas 等に依存せず標準ライブラリで実装されているため、性能要件に応じて一部処理（大規模データの集計）を最適化する余地があります。
- News Collector
  - RSS フィードの URL は必ず http/https を使用してください。非許可スキームやプライベートホストはスキップされます。
  - 記事ID生成は URL 正規化後の SHA-256 を用いるため、同一記事の重複保存が起こりにくいですが、同一記事の URL が大幅に変化するケースでは重複判定を保証できない場合があります。
- J-Quants クライアント
  - API レート制限を守るため内部で固定間隔スロットリングを行います。大規模な一括取得を行う場合、処理時間が増加する点に留意してください。
  - 401 が発生した場合は id_token を自動でリフレッシュします（ただしリフレッシュに失敗するとエラーになります）。

### Known limitations
- schema.py は Raw Layer を中心に DDL を提供していますが、Processed / Feature / Execution 層の完全な DDL はプロジェクトの仕様に応じて追加・拡張が必要です。
- 研究モジュールは標準ライブラリのみで記述しているため、大規模データ処理においては pandas や numpy を併用する方が簡潔かつ高速な場合があります（現状は依存を増やさない設計優先）。
- news_collector の私製ルール（記事IDの先頭32文字等）は運用上の要件に応じて変更の余地があります。

---

貢献・バグ報告・改善提案は Issue を通じて歓迎します。