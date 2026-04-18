# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
このファイルはコードベースの現在の状態（バージョン 0.1.0）から推測して作成した変更履歴です。各項目は該当するモジュール・ファイル名を併記しています。

なお、実装から推測した挙動や注意点を含みます（実際のコミット履歴ではありません）。

## [Unreleased]
- （今後の変更記載用）

## [0.1.0] - 初期リリース
初回リリース。以下の主要機能とユーティリティを実装しています。

### 追加（Added）
- 実行スクリプト
  - 実行エンジン起動スクリプト: run_execution.py  
    - ExecutionEngine の起動フローを実装。スレッドでエンジンを起動し、data/stop_requested.flag による停止制御を実装。
    - 環境に応じて paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離する挙動をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト: run_monitoring.py  
    - SystemMonitor をポーリングで起動。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全に終了（src/kabusys/run_monitoring.py）。

- 環境設定関連
  - Settings クラス（src/kabusys/config.py）を実装。環境変数経由の設定取得をラップし、各種プロパティ（env, is_live/is_paper/is_dev, DB パス、PID/kill flag パス、しきい値など）を提供。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を起点）。.env と .env.local の読み込み順を実装し、OS 環境変数の保護（上書き禁止）を考慮。
  - .env パーサを堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント扱いの仕様（src/kabusys/config.py）。

- 設定支援 CLI
  - 対話式環境設定ウィザード: config_setup.py  
    - .env の初期作成・更新を対話的にサポート。秘密値マスク表示、選択肢・デフォルト、保存確認など（src/kabusys/config_setup.py）。
  - 設定検証 CLI: validate_config.py  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）。本番（live）環境向けの追加警告も実装（src/kabusys/validate_config.py）。

- ロギング & プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ: setup_logging()（src/kabusys/utils/logging_setup.py）  
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/ に app_name.log）をルートロガーに設定。
    - ログレベル/ログディレクトリの解決順を実装。ディレクトリ作成失敗時はファイル出力をスキップして console のみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ: set_process_priority(), set_cpu_affinity()（src/kabusys/utils/process_priority.py）  
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する実装。権限不足や未対応 OS では警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群、DBアクセスなし）
  - 候補選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定・丸め・投下制御: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）  
    - 単元（lot_size）で丸め、aggregate cap のスケーリング処理、cost_buffer を用いた保守的なコスト見積り、リスクベース配分や等配分/スコア配分に対応。

- Paper Trading 用検証ツール
  - paper_verification_report.py（src/kabusys/tools/paper_verification_report.py）  
    - SQLite の paper_trading DB を参照し、稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計して判定（PASS/FAIL）を出力。閾値はファイル内で定義（例: 稼働率 99%、P95 200ms など）。

- 研究用ファクターモジュール（着手）
  - factor_research.py（src/kabusys/research/factor_research.py）にてモメンタムや MA200、ATR、出来高等を計算する方針・定数が実装（DuckDB 接続を受け取る設計）。※ファイル途中までの実装。

### 変更（Changed）
- ログ出力先のポリシー: stdout を標準出力に使用する方針を明確化（cron/Task Scheduler でのリダイレクトを想定）（src/kabusys/utils/logging_setup.py）。
- 環境変数自動読み込みの挙動: OS 環境変数は保護され .env.local が .env を上書きできる実装（src/kabusys/config.py）。
- Execution/Monitoring の DB 利用ポリシー:
  - 監視側は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（run_monitoring.py）。
  - 実行側は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離する（run_execution.py）。

### 修正（Fixed）
- 無効な MONITOR_POLL_INTERVAL の扱いを安全化（負数や非数はデフォルトにフォールバックして警告ログ）（src/kabusys/run_monitoring.py）。
- .env パーサのクォート内エスケープ、インラインコメント処理を改善してより一般的な .env 記法に対応（src/kabusys/config.py）。
- ログディレクトリ作成失敗時にハンドラ作成が失敗しても、プロセスがクラッシュせずにコンソール出力のみで継続するように堅牢化（src/kabusys/utils/logging_setup.py）。
- process_priority / cpu_affinity で権限不足や未対応機能が発生した際に警告を出して処理を継続する安全策を追加（src/kabusys/utils/process_priority.py）。
- config/ YAML 検証は PyYAML がインストールされていない場合にスキップし、警告を出すようにして起動環境に依存しない（src/kabusys/validate_config.py）。

### ドキュメント（Documentation）
- 各モジュールに docstring と使用例を追加。設定ウィザード・検証ツール・実行・監視・各ユーティリティで使い方の説明を充実（各ファイルの先頭 docstring）。

### 注意（Notes）
- Settings による必須環境変数取得は未設定時に ValueError を投げる仕様（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。validate_config.py で起動前に検出することを推奨。
- run_execution の RiskConfig で initial_portfolio_value を broker.get_available_cash() から取得しており、Broker クライアント実装に依存する。
- position_sizing の価格欠損（price が 0 や未設定）の場合はスキップする実装。将来的なフォールバック価格（前日終値等）の導入が TODO に記載されている。
- factor_research.py は DuckDB と prices_daily / raw_financials を前提にしており、実データ準備が必要。

---

参照: Keep a Changelog（慣例に従いセクションを分けて記載）。この CHANGELOG はコードを静的に解析して作成した推測に基づくため、実際のコミット履歴や開発ノートと相違がある可能性があります。必要に応じて日付・コミット SHA・追加のリリースノートを補完してください。