# Changelog

すべての重要な変更をこのファイルに記録します。
形式は「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

最新: [Unreleased] — まだリリースなし

## [Unreleased]
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-17

初回公開リリース。リポジトリ内の主要機能群を実装・統合しました。

### 追加 (Added)
- コア
  - パッケージ初版「kabusys」を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB / SQLite を利用したローカルデータ処理基盤を統合（設定経由でパス指定）。
- 設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルート自動検出、OS 環境変数保護）。
  - 複雑な .env パースに対応（export プレフィックス、クォート内エスケープ、インラインコメント処理）。
  - 必須環境変数取得ヘルパ `_require()` と各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル等）を実装。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーションを追加。
- 実行系 (execution)
  - ExecutionEngine 起動スクリプト（run_execution.py）を追加。
  - BrokerClientFactory を介した実ブローカー / モックブローカーの切替（KABUSYS_ENV=paper_trading で Mock を使用）。
  - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせた実行パイプラインの組立て。
  - Paper trading 用に本番 DB と分離された専用 SQLite（data/paper_trading.db）をサポート。
  - エンジンの PID 管理と stop フラグ（data/stop_requested.flag）による安全停止処理を実装。
- 監視系 (monitoring)
  - SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）を追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
  - 監視用 DB テーブル初期化 util（init_monitoring_db）呼び出しを統合。
  - 監視処理は環境に関わらず本番の sqlite_path を使用する仕様。
- ポートフォリオ構築 (portfolio)
  - 銘柄選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights。
  - セクター集中制限とレジーム乗数: apply_sector_cap, calc_regime_multiplier（レジーム別乗数マップ実装）。
  - ポジションサイズ計算: calc_position_sizes（risk_based / equal / score 対応、単元株丸め、aggregate cap スケールダウン実装）。
  - 設計ドキュメント（参照）に基づく純粋関数群として実装（副作用無し、DB 参照なし）。
- リサーチ / ファクター (research)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB の prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank。
  - 統計ユーティリティとして zscore_normalize をエクスポート。
- ニュース NLP（AI）
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングし ai_scores に書き込む設計の実装開始（score_news, calc_news_window 等）。
  - バッチ処理、最大記事数/文字数トリム、結果バリデーション、スコアクリッピング、リトライ（指数バックオフ）などの堅牢化方針を実装。
- ツール
  - Paper Trading 用検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 >= 99%、Fill >= 90%、Send >= 95%、P95 <= 200ms）。
- ユーティリティ (utils)
  - プロセス優先度設定ユーティリティ（set_process_priority）を追加。Windows / POSIX の差を吸収。
  - CPU affinity 設定関数（set_cpu_affinity）を追加。
  - 上記は psutil を利用しており、権限不足や非対応 OS の場合は警告を出して安全にスキップ。

### 変更 (Changed)
- 設計上の留意点をコード内 docstring とコメントで明確化：
  - ニューススコアリングはルックアヘッドバイアスを避けるため現在時刻参照を避ける設計。
  - ポートフォリオ/サイズ計算は DB 参照を行わず純粋関数で実装（テスト容易性重視）。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

### 修正 (Fixed)
- 環境変数パースの堅牢化：
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント扱いなどに対応。
  - 無効な MONITOR_POLL_INTERVAL 値で起動時に例外を投げず警告してデフォルト 60 秒へフォールバックするように修正。
- ExecutionEngine 起動時に監視テーブルが存在しないケースを想定して init_monitoring_db を呼び出し、冪等性を確保。

### 既知の問題 / 注意点 (Known issues / Notes)
- ai/news_nlp.py は大枠の処理設計と多くのハンドリング（バッチ、リトライ、レスポンス検証）を実装していますが、外部 API 呼び出し周辺（実際の HTTP 呼び出しループや最終的な DB 書き込みロジック）の一部が継続実装を要する可能性があります（ファイル末端の未完了断片を含む場合あり）。
- Paper trading は本番 DB と完全分離されますが、データパスや環境変数の設定ミスにより想定通りに分離されない可能性があるため、デプロイ時に PAPER_TRADING_SQLITE_PATH の確認を推奨します。
- set_process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、期待通りに動作しない場合はログでフォールバックされます。

### 環境変数の主な一覧（初期設定 / デフォルト）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — paper_trading のモック約定挙動（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（news_nlp で必要）
- KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN 等 — 外部 API 用トークン（必須設定時は _require() で例外）

---

セマンティックバージョニングやリリース方針に関する質問や、変更点の詳細（例えば各関数の入力/出力の厳密仕様、テストカバレッジなど）をご希望であればお知らせください。