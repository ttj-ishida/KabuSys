# Changelog

すべての注記は Keep a Changelog に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴です。

※ バージョン/日付はコードの内容から推測して記載しています。実際のリリース日やバージョン運用に合わせて適宜編集してください。

## [Unreleased]

### Added
- 環境設定の自動ロード強化
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む機能を追加。OS 環境変数を保護する仕組み（protected）を導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。

- .env パーサの強化
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理などをサポート。
  - 無効行やキーなし行を安全にスキップする処理を導入。

- 実行エントリ / モニタリング
  - run_execution: ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用する仕組みをサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視用 DB は環境に依存せず本番 sqlite_path を使用する旨を明示。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level) で Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定を行う。アクセス権限や未対応 OS では安全にスキップしてログ出力。
  - set_cpu_affinity(cpu_count) によるプロセスのコア固定機能を提供。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定: select_candidates（スコア降順、signal_rank によるタイブレーク）
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化。全スコア 0 の場合は等分配にフォールバック）
  - セクター集中制限: apply_sector_cap（既存保有・当日売却予定を考慮したセクター上限フィルタ）
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に基づく乗数、未知レジームは警告の上 1.0 でフォールバック）
  - 株数算出: calc_position_sizes（risk_based / equal / score の allocation_method、lot_size 単位で丸め、aggregate cap によるスケールダウン）

- 研究（Research）モジュール
  - factor_research: momentum、volatility、value ファクター計算（DuckDB を用いた SQL 実行）
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリ、ランク変換ユーティリティ
  - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計（外部 API に依存しない）

- AI ニュース NLP スコアリング
  - ai/news_nlp: raw_news と news_symbols からニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ書き込む処理を実装。
  - 処理の特徴: 銘柄ごと最大記事数・文字数のトリム、最大バッチサイズ、JSON レスポンス検証、±1.0 でスコアクリップ、429/ネットワーク/5xx に対する指数バックオフリトライ、部分失敗時の既存スコア保護（対象コードに絞って置換）。
  - ニュース収集ウィンドウ計算ユーティリティ（JST基準から UTC naive datetime を返す calc_news_window）を提供。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading 用 SQLite DB を解析して検証レポートを標準出力に出力する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、閾値に基づく PASS/FAIL 判定を行う。

### Changed
- 環境設定の取り扱い
  - .env / .env.local の読み込み順を OS 環境変数 > .env.local > .env と明確化。OS 側の環境変数は保護され、上書きされない。

- DB 接続方針
  - 監視系（run_monitoring）は KABUSYS_ENV に依存せず、常に本番用 sqlite_path を使用する方針を明確化。
  - 実行系（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。

### Fixed
- 入力値の堅牢性向上
  - MONITOR_POLL_INTERVAL が不正（0 以下や非数）の場合は警告を出しデフォルト（60 秒）にフォールバック。
  - PAPER_FILL_MODE の値検証を追加（instant/partial/never/reject のいずれかでない場合は ValueError）。
  - Settings の env / log_level 等で不正値検出時に明確なエラーメッセージを出すよう改善。

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出。キーの扱いは環境変数経由を想定。

---

## [0.1.0] - 2026-04-11

初回公開（コードベースから推測された主要機能のまとめ）。

### Added
- コア機能
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の実行系コンポーネントを実装。
  - SystemMonitor と監視用 DB 初期化ユーティリティ（init_monitoring_db）を実装。
  - DuckDB / SQLite を用いたデータ基盤接続を標準化。

- 設定管理
  - Settings クラスで主要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH など）をラップして提供。
  - pid_file_path / kill_flag_path 等の監視関連設定を追加。

- ポートフォリオ・構築ロジック
  - PortfolioConstruction に基づく純粋関数群（選定・重み付け・リスク調整・ポジションサイズ算出）を実装。

- 研究・ファクター算出
  - Momentum / Volatility / Value の定量ファクター計算を DuckDB ベースで実装。
  - 将来リターン計算・IC 計算・ファクター統計サマリを提供。

- ユーティリティ
  - process_priority、CPU affinity 設定ユーティリティを実装（psutil 依存）。
  - run_* スクリプト（run_execution, run_monitoring）とツール群（paper_verification_report）を提供。

### Changed
- プロジェクト初期版として、モジュール分割と public API（kabusys パッケージの __all__）を定義。

### Fixed
- 初期実装段階での基本的な入力検証と例外ハンドリングを追加（DB 存在チェック、SQL 実行時の OperationalError ハンドリングなど）。

---

注記:
- 上記はソースコードの構造・ドキュメンテーション文字列・実装から推測して作成した変更履歴です。実際のリリースノートはコミット履歴・リリース日・プロジェクト方針に合わせて調整してください。