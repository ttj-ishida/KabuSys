# KabuSys — 日本株自動売買システム（README）

この README はリポジトリ内の主要モジュールと起動手順、設定方法、ディレクトリ構成をまとめたものです。開発者・運用担当者向けに簡潔に使い方を示します。

※ 本プロジェクトは複数のサブシステム（ExecutionEngine・Monitoring・Research・AI 等）で構成され、設定は主に環境変数（.env）で行います。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（コマンド例）
- 主要環境変数（要/任意）
- 運用メモ（kill flag / paper_trading 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買・バックテスト・リサーチを想定したモジュール群です。
- 主な役割：
  - ExecutionEngine：発注・注文管理・リスク管理を行うエンジン（本番/ペーパートレード対応）
  - Monitoring：システム状態・注文状況・リスクを定期監視しアラート発火・Kill Switch を操作
  - Research：DuckDB を用いたファクター計算・特徴量解析
  - AI：ニュースの LLM によるセンチメント評価（OpenAI API を利用）
  - Portfolio：候補選定・ウェイト計算・ポジションサイズ決定ロジック
  - Tools：レポート生成など補助スクリプト

主な機能一覧
- 実行エンジン（run_execution.py）
  - 本番 / ペーパー（KABUSYS_ENV）に応じたブローカークライアント切替
  - リスク制御（RiskManager）、注文管理（OrderManager）、整合化（Reconciler）
  - PID ファイル出力 / 停止フラグ検出
- 監視（run_monitoring.py / monitoring/*）
  - CPU/メモリ/ディスク使用率・プロセス死活確認・データ鮮度チェック
  - Trade / Risk / System の監視とアラート発行、KillSwitch による停止制御
  - 監視ログは SQLite（monitoring.db）に永続化
- リサーチ（research/*）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）等の統計ユーティリティ
- AI（ai/*）
  - ニュース記事をまとめて OpenAI に投げ、銘柄毎のセンチメントを ai_scores に書き込む
  - マクロニュース + ETF 指標で市場レジーム判定
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重/スコア重み、リスク調整、株数算出（単元丸め、aggregate cap）
- ツール
  - paper_verification_report: ペーパートレード DB の検証レポート生成

前提・依存関係
- Python 3.9 以降（型アノテーションの構文や pathlib の利用を想定）
- 主な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に使用）
- （開発時）pip install -r requirements.txt を用いる想定（requirements.txt はプロジェクトに応じて用意してください）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 必要に応じて PyYAML などを追加（設定ファイル検証で利用）

3. .env を作成・設定
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env ファイルを作成（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須）
   - Settings モジュールはプロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合は --strict を付ける

5. データディレクトリの準備（任意）
   - デフォルトでは data/ ディレクトリ配下に DB やフラグファイルを置きます。必要なら作成:
     - mkdir -p data logs

使い方（代表的なコマンド）
- ExecutionEngine（本番または paper_trading に従う）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を使うと MockBrokerClient を有効にし、ペーパー用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。

- Monitoring
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（monitoring DB）を使う。モニタは常に本番設定の sqlite_path を参照します（環境に依らず）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 推奨/任意
  - KABUSYS_ENV : execution 環境 (development | paper_trading | live)（デフォルト: development）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL : ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY : OpenAI API キー（AI モジュール使用時必須）
  - PAPER_FILL_MODE : ペーパートレードの約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動で消すか（0/1）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）

運用メモ（Kill Switch / 停止制御 / ペーパートレード）
- Kill Switch
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込むと ExecutionEngine を停止させる仕組みがあります。
  - KillSwitch クラスは RiskMonitor 等の判定に基づいて kill.flag を作成します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では 0 推奨）。
- 停止フラグ（stop_requested.flag）
  - run_execution.py / run_monitoring.py は data/stop_requested.flag をチェックし、存在すればループを終了します。
- ペーパートレード
  - KABUSYS_ENV=paper_trading に設定すると、MockBrokerClient を利用して実際のブローカへ発注せず、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
  - データ・DB は本番と完全分離されます。

ログと監査
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- デフォルトログディレクトリは logs/、ファイルは日次ローテーションで保持（日数は BACKUP_COUNT、デフォルト 30 日）。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/               — 実行系（Engine, OrderManager, RiskManager 等）※詳細実装は同ディレクトリ
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — 通知管理（LINE 等）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マーケットレジーム判定（AI + ETF 指標）
  - monitoring/              — 監視関連（上記）
  - utils/
    - logging_setup.py
    - process_priority.py    — プロセス優先度 / CPU affinity
  - data/ (運用時に作成される想定)
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (runtime logs)

補足・運用上の注意
- Settings はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能です。
- Monitoring は「環境にかかわらず」Settings.sqlite_path を使って監視 DB を操作します（監視ログは常に本番用パスへ）。この点に注意して本番とテストの DB を分けてください。
- AI モジュールは OpenAI API を呼び出します。API 呼び出し失敗時はフォールバック動作（0.0）により安全側で処理しますが、API キーや利用量に注意してください。
- Docker 化や systemd でのデプロイを行う場合、ログディレクトリ・data ディレクトリの永続化と権限に注意してください。

---

README に記載の無い詳細実装（ExecutionEngine の内部や OrderRepository、BrokerFactory 等）はソース内の docstring とコメントを参照してください。起動・運用で不明点があれば該当モジュールの docstring（モジュール冒頭）を参照するか問い合わせてください。