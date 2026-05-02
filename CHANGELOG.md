# CHANGELOG

すべての重要な変更履歴をここに記録します。フォーマットは「Keep a Changelog」準拠です。  
（注: 以下はコードベースの内容から推測して作成した変更履歴です）

## [Unreleased]
- なし

## [0.1.0] - 2026-05-02
初回リリース（推測）。以下の主要機能と改善を含みます。

### 追加 (Added)
- CLI エントリポイント群を追加
  - run_monitoring: SystemMonitor のポーリングループを実行する起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番の sqlite_path を使用する仕様。
  - run_execution: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）に記録する。
  - run_intraday_monitor: ザラ場中監視用 CLI。単発実行 / watch モードをサポートし、監視ステータスの整形出力を行う。
  - run_signal_queue_report, run_position_reconciliation_report, run_pre_market_report, run_market_close_report, run_performance_report: 各種レポート生成用 CLI（--date / --save / --json / --watch などのオプションを提供）。
  - validate_config: .env や config/*.yaml の検証を行う CLI。--strict オプションで警告を FAIL 扱いにできる。
  - config_setup: 対話式ウィザードによる .env ファイルの生成・更新をサポートするツール。
  - tools/paper_verification_report: ペーパートレーディングの検証レポート生成スクリプト（稼働率、注文成功率、レイテンシなどの指標を算出）。

- 環境設定モジュール (kabusys.config)
  - プロジェクトルート自動検出 (_find_project_root) に基づき .env / .env.local を自動読み込み（OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の柔軟なパース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを導入し、各種環境変数（J-Quants, kabu API, LINE, DB パス, モニタ閾値, 実行環境 等）をプロパティとして提供。
  - paper_trading 用の個別設定（PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE）をサポート。

- リスク設定読み込み・検証
  - risk_config.yaml を読み込み、型変換および値域チェック（max_position_pct / max_utilization / max_drawdown は (0,1]、レート制限等は >=1）を行う RiskConfig 作成ロジックを追加。
  - run_execution 起動時に initial_portfolio_value を計算し、RiskManager に渡すフローを実装。

- DB 初期化 / 接続
  - monitoring 用の SQLite テーブルを初期化する init_monitoring_db の呼び出しを導入（冪等な保証）。
  - duckdb 接続を各種レポート / 実行コンポーネントで使用。

- プロセス管理・停止フラグ
  - PID ファイルの作成/削除、stop_requested.flag（停止フラグ）の検知による安全な停止処理を導入。
  - プロセス優先度を設定するユーティリティ（set_process_priority）を起動直後に呼び出すようにしている。

- レポートのフォーマットと保存機能
  - CLI 出力（コンソール用の整形、JSON 出力）や artifacts ディレクトリへの保存をサポート。
  - 各レポートは終了コードで状態を反映（例: READY かどうか、BLOCKED/STATUS_DISCREPANCY 等）。

- 実行エンジンと注文処理
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組み立てと起動シーケンスを実装。起動時にリコンシリエーションを実行し、Startup Summary を生成して保存/表示する流れを追加。
  - Engine.run_session を別スレッドでデーモン起動し、停止フラグ検知で安全終了する仕組み。

- インストゥルメント / ユーティリティ
  - intraday snapshot 集計、position reconciliation、signal queue、pre-market、market-close、performance 集計ロジックに対応する collector/report モジュールを利用する CLI を提供。
  - paper_verification_report では uptime, fill rate, send rate, latency(P95) 等の指標を算出するロジックを実装。

### 変更 (Changed)
- 設定読み込みの優先度を明確化
  - 読み込み優先度: OS 環境 > .env.local > .env（.env.local は上書き）
- run_execution にて paper_trading 環境時には paper_sqlite_path を使用するよう分岐（本番 DB と完全分離）。

### 修正 (Fixed)
- .env パースの堅牢化
  - クォート・エスケープ・コメント処理を改善し、より多様な .env 構文に対応。
- ポーリング間隔のバリデーション
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を警告してデフォルトにフォールバックする処理を追加。
- データベース接続時の読み取り専用 URI 利用（report/monitoring CLI で read_only 接続を利用するケースを追加）。
- PID ファイルの存在管理（起動時の書き込み、終了時の削除を確実にする try/finally ブロック）。

### ドキュメント (Documentation)
- 各 CLI スクリプト冒頭に使用例を追加し、使い方（オプション）を明記。
- config_setup による .env 生成時のテンプレート／コメントを整備。

### セキュリティ (Security)
- .env を Git にコミットしない旨の注記を config_setup のテンプレートに明記。
- 機密値はウィザードでマスク表示する等の扱いを採用（表示は ****）。

### 既知の制限 / 注意事項
- run_monitoring は Monitoring のために「環境にかかわらず本番 sqlite_path を使用する」仕様になっているため、paper_trading 環境で監視 DB を分離したい場合は注意が必要（意図的な設計か確認推奨）。
- 一部機能は外部ライブラリ（PyYAML、duckdb 等）に依存するため、未インストール時は YAML 検証等がスキップされる箇所がある。
- KABUSYS_ENV=live では追加の警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険性等）が出力される。運用時は該当設定を確認のこと。

---

参照:
- パッケージバージョン: kabusys.__version__ == "0.1.0"（初期リリース相当）
- 日付はコード解析時点の日付（2026-05-02）を使用しています。実際のリリース日で調整してください。