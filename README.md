# KabuSys — 日本株自動売買システム

軽量な日本株自動売買/リサーチ基盤のコアモジュール群を含むリポジトリ。  
ポートフォリオ構築、ポジションサイジング、監視（Monitoring）、Execution エンジン、AI を使ったニュースセンチメント／レジーム判定、分析用 DuckDB スキーマ操作などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・ユーティリティ）
- 主要環境変数
- ディレクトリ構成（抜粋）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買システムの核となるライブラリ／スクリプト群です。
- 発注周り（ExecutionEngine）と監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析/レジーム判定、運用ヘルパーツールを含みます。
- 設定は環境変数（`.env`）で管理され、`.env` の初期作成を支援する対話式ウィザードと設定検証ツールが付属します。

---

主な機能
- Execution エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレード（完全分離された SQLite DB を使用）
  - BrokerClientFactory により本番ブローカー／Mock ブローカーを切替え
  - 停止フラグ / PID 管理
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 注文の滞留・異常チェック（trade_logs 等）
  - RiskMonitor: ドローダウン・ポジション上限などのリスク監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine: 各 Monitor の統合ポーリング
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、等金額・スコア加重配分、セクターキャップ、レジーム乗数、株数計算（単元丸め）
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量解析、IC 計算、将来リターン計算など
- AI（ai モジュール）
  - news_nlp: raw_news を元に OpenAI（gpt-4o-mini 等）で銘柄センチメント算出 → ai_scores へ書き込み
  - regime_detector: ETF とマクロ記事を合成して market_regime を判定・永続化
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

セットアップ手順（開発環境向け）
1. リポジトリをクローン、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例: pip install -r requirements.txt）
   - 本コードベースでは次が必要になる可能性があります:
     - duckdb
     - psutil
     - openai（AI 機能を利用する場合）
     - PyYAML（validate_config の YAML 検証を使う場合）
4. 初期 .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成された .env を確認・編集してください（絶対に Git にコミットしないでください）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

注: 自動で .env を読み込むロジックがあります（プロジェクトルートに .env / .env.local があれば読み込み）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

使い方（主要コマンド例）

1. Execution エンジン起動
- フォアグラウンド実行:
  - python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書き出します。

2. Monitoring（監視）起動
- python -m kabusys.run_monitoring
- 補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使って監視 DB を更新します。
  - 停止は data/stop_requested.flag の作成で行います。

3. Paper Trading 検証レポート
- 期間指定してレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4. AI の実行（例）
- news_nlp / regime_detector は DuckDB 接続と OpenAI API キーが必要です。コード内の関数を呼び出して使用します。
- 環境変数 OPENAI_API_KEY を設定するか、関数引数で api_key を渡してください。

ログ
- 共通ログセットアップは kabusys.utils.logging_setup.setup_logging を使用します。
- 標準では logs/<app_name>.log に日次ローテーション（30 日保持）で出力されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

停止・Kill Switch
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は監視側から Execution を停止するために書き込まれます（KillSwitch）。
- Execution 側は起動時に kill flag をクリアする動作をオプションで行えます（KILL_FLAG_CLEAR_ON_START=1）。本番では 0 を推奨。
- 手動でプロセスを停止させたい場合は data/stop_requested.flag を作成すると run_* スクリプトが検知して終了します。

---

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — Execution の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- ログ
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。default 60）
- Paper Trading
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必要）
- その他
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定読み込みロジック
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — 監視用 DB 層（SQLite）
    - system_monitor.py
    - trade_monitor.py        — 注文監視（存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — アラート送信管理（存在）
  - execution/                — Execution 関係（Engine、OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は主要ファイルの抜粋です。実装に応じて他のモジュール／サブパッケージが含まれます）

---

運用上の注意 / ベストプラクティス
- 本番稼働前に必ず python -m kabusys.validate_config で設定を検証してください。KABUSYS_ENV=live の場合は設定ミスによるリスクが大きくなります。
- .env をバージョン管理に含めないでください。README 内のサンプル値や .env.example を参照してローカルで作成してください。
- OpenAI など外部 API を用いる処理は API 失敗時のフォールバックが組まれているものの、API コストや利用制限に注意してください。
- run_execution / run_monitoring はサービス（systemd）や監視下で起動することを想定しています。ログは logs/ に出力され、日次ローテーションされます。
- process priority の設定は psutil を通じて行われます。権限不足で警告が出る場合があります（無害）。
- データベース（SQLite / DuckDB）のパスは .env で指定できます。paper_trading は本番 DB と分離することを強く推奨します。

---

追加情報 / トラブルシュート
- ログディレクトリ作成に失敗するとコンソール出力のみになります（エラーメッセージが標準エラーに出ます）。
- MONITOR_POLL_INTERVAL の値が不正（整数でない、1 未満など）の場合はデフォルト 60 秒にフォールバックします。
- Monitoring は監視用 SQLite に対してマイグレーションを自動で適用します（列追加等）。

---

貢献／開発
- 小さな改善やバグ修正は PR を歓迎します。大きな機能追加は Issue で議論をお願いします。
- モジュール単位でユニットテストを追加するとマージがスムーズです（特に AI 呼び出し部分はモック化を推奨）。

---

以上が本リポジトリの README です。必要であれば、.env のサンプルテンプレートや systemd ユニット例、運用フロー（例: 起動手順、緊急停止手順、バックアップ方針）を追加で作成します。どの情報が欲しいか教えてください。