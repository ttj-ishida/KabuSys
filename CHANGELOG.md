# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-25

初回リリース。主要な機能の実装と CLI / ユーティリティ群を追加しました。

### 追加 (Added)
- 実行エントリ・運用スクリプト
  - run_execution.py
    - ExecutionEngine をデーモン的に起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離をサポート（paper_trading 時は PAPER_TRADING_SQLITE_PATH／data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。
    - 起動時・実行中に data/stop_requested.flag を検知して安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring 用 DB は実行環境にかかわらず本番 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了をサポート。

- 設定関連
  - config.py
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - Settings クラスを提供し、環境変数を高レベル API として取得可能に（各種パス、閾値、paper_trading 用設定、env/log_level 検証など）。
    - PAPER_FILL_MODE の検証や各種閾値（CPU/MEM/DISK など）の取得を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 入力のヒント、既存 .env の読み込み、シークレット値のマスク表示、確認後の書き込みを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無・プレースホルダチェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けのガード検査（LINE 通知設定や Kill Switch の自動クリア設定）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）の設定を行う共通ユーティリティを追加。
    - ログレベル／ログディレクトリの解決順序を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する安全設計。
  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定を実装（Windows の priority class / POSIX の nice 値を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加。
    - 権限不足や非対応 OS に対するフォールバック・警告処理を備える。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレーク条件付き）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中度チェックによる候補除外（sell_codes を考慮）、レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した発注株数計算を実装。
    - 損切り・リスク許容度・単元株丸め（lot_size）・1銘柄上限・aggregate cap（利用可能現金内にスケールダウン）・cost_buffer を考慮した安全な調整ロジックを実装。
    - aggregate スケールダウン後の端数処理で残余キャッシュを使った追加配分ロジックを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99% 等）に基づいて PASS/FAIL 判定を出力。
    - DB パスは引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュール（Momentum / Value / Volatility / Liquidity 設計）を追加。momentum 計算のための定数や関数枠組みを実装（実装途中の箇所あり）。

### 変更 (Changed)
- logging の標準出力を stdout に統一
  - 起動時のログが Task Scheduler / cron 等でリダイレクトされる想定のため、StreamHandler を stdout に向けるように変更。
- .env の自動ロード挙動
  - プロジェクトルート検出（.git / pyproject.toml）を起点に .env/.env.local を自動読み込み（既存 OS 環境変数を保護）。これにより CWD に依存しない安定した設定読み込みを実現。

### 修正 (Fixed)
- logging_setup の堅牢化
  - ログディレクトリの作成に失敗した場合にファイルハンドラ作成をスキップしてもアプリが継続するように修正。
- process_priority の例外ハンドリング強化
  - psutil での権限不足や未実装 API 呼び出し時に警告を出してスキップするように改善。
- config パーサの堅牢化
  - クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの扱いを改善し、.env ファイルの柔軟な記述をサポート。

### 既知の制約 / 注意点
- research/factor_research.py はモジュールの骨組みを実装していますが、ファイル末尾でコードが未完（生成途中）であるため、momentum 計算の続きを実装する必要があります。
- 一部の機能は psutil / duckdb / PyYAML 等の外部依存が必要です。validate_config の YAML 検証は PyYAML が見つからない場合にスキップされます。
- run_monitoring/run_execution は監視用・実行用の SQLite / DuckDB を直接開くため、適切なファイルパスと権限を確認してください。特に paper_trading 環境では DB が本番 DB と分離される点に注意してください。

### ドキュメント
- 各モジュールに詳細な docstring を追加し、CLI の使い方・環境変数・デフォルト値・設計意図（PortfolioConstruction.md, StrategyModel.md 等参照）を明記しました（ドキュメント参照箇所はコード内コメントに記載）。

---

今後の予定（例）
- research/factor_research の完成および単体テスト追加
- ExecutionEngine / Monitoring のエンドツーエンド統合テスト
- 設定ガイド・運用手順書の整備（デプロイ / モニタリング運用について）