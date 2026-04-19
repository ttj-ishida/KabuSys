# KabuSys

日本株向けの自動売買・リサーチ基盤（ライブラリ＋起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・モニタリング・リサーチを目的とした小規模なシステム基盤です。  
主な役割は以下の通りです。

- ExecutionEngine（発注エンジン）: ブローカークライアントを介した発注管理、注文履歴の記録、リスク管理
- Monitoring（監視）: システムの健全性・注文状態・リスク指標をポーリングしログ化・アラート／Kill Switch を実行
- Portfolio construction / position sizing: 候補選定、重み付け、株数計算などの純粋関数群
- Research: DuckDB 上の過去データを用いたファクター計算・特徴量解析
- AI モジュール: ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI を利用）
- ユーティリティ: 設定ウィザード、設定検証、ペーパートレードの検証レポート生成 等

設計方針として、可能な限り副作用を抑えた純粋関数・DB 層の明確化、環境依存設定は .env で管理、Paper Trading と Live の分離がなされています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理 / ツール
  - config_setup.py: 対話式で .env を作成 / 更新
  - validate_config.py: 環境変数・config/*.yaml の検証 CLI
  - tools/paper_verification_report.py: ペーパートレード履歴から検証レポート作成
- 監視
  - monitoring_engine.py: System / Trade / Risk モニタを束ねてポーリング
  - monitoring_db.py: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - kill_switch.py: 条件により data/kill.flag を書き込み Execution を停止させる
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み計算、株数決定、セクター上限・レジーム補正
- リサーチ
  - research: ファクター計算（モメンタム・ボラティリティ・バリュー）、IC 計算、forward returns
- AI（OpenAI）
  - ai.news_nlp: ニュース記事のセンチメントを LLM により銘柄別スコア化して ai_scores に書き込み
  - ai.regime_detector: マクロニュース + ETF MA 乖離で市場レジームを判定して market_regime に書き込み
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

1. リポジトリをクローン / 配置
   - ソースは `src/kabusys` 配下にあります。プロジェクトルートを保持してください（.env 自動ロードが機能します）。

2. Python 環境の準備（例）
   - 推奨: Python 3.9+
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate (Linux/Mac) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 主に以下が必要です（環境によって追加で必要になる場合があります）。
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（validate_config で YAML のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成。
   - 主な環境変数（重要・必須）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading の場合の DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - MONITOR_POLL_INTERVAL (run_monitoring 用、秒) — 60 秒がデフォルト

5. ディレクトリ作成（任意）
   - data/ および logs/ は実行時に自動作成されますが、手動で事前作成しておくこともできます。

---

## 使い方（よく使うコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番 / ペーパートレードの切替は `KABUSYS_ENV` 環境変数で制御
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
  - 停止:
    - 実行スクリプトは `data/stop_requested.flag` の存在を検知して停止します。手動で停止フラグを作成すれば安全に停止できます（または Ctrl+C）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます。デフォルトは 60 秒。
  - run_monitoring は monitoring 用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番 path を参照）。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を環境変数に設定するか api_key を引数で渡してください。

ログの場所:
- デフォルトでは logs/<app_name>.log に日次ローテートで保存されます（30日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的にセットされています。

Kill / Stop の運用:
- ExecutionEngine 停止命令は `data/kill.flag`（Kill Switch）または `data/stop_requested.flag`（運用停止）で制御されています。
  - kill.flag は Monitoring 側の条件（ドローダウン、ポジション上限など）で書き込まれることがあります。
  - Execution 側は起動時に kill.flag を自動クリアするオプション（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨します。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数は上書きされません（デフォルト）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env 作成ウィザード（CLI）
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（__main__）
  - run_monitoring.py          — SystemMonitor 起動スクリプト（__main__）
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - execution/                 — 発注エンジン関連（OrderManager 等）
    - (ExecutionEngine / broker_factory / order_manager / risk_manager など)
  - monitoring/
    - monitoring_db.py         — SQLite 永続層（テーブル作成 / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （通知管理：LINE 等に送る想定）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI）
  - data/                      — 実行時データ（デフォルト path）
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - tools/
    - paper_verification_report.py

（上記は主要ファイルの抜粋です。細かい実装は src/kabusys 以下の各モジュールを参照してください。）

---

## 開発・運用上の注意

- Paper Trading と Live は DB を分離しています（PAPER_TRADING_SQLITE_PATH を使用）。本番 DB へ誤って書き込まないよう `KABUSYS_ENV` を正しく設定してください。
- OpenAI（AI 機能）を有効にする場合は API キーの管理に注意してください（.env を Git 管理しないこと）。
- run_monitoring は Monitoring 用 sqlite DB（Settings.sqlite_path）を参照します。モニタは本番 DB を参照してリスク判断を行うため、適切な DB パスを設定してください。
- ログはデフォルトで logs/ に出力されます。ログディレクトリの作成に失敗した場合はコンソールのみ出力されます。
- プロセス優先度設定は OS に依存し、権限不足等で失敗することがあります（警告ログのみ）。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、README に以下を追加で記載できます：
- requirements.txt の推奨リスト
- systemd / Supervisor 用のサンプルユニットファイル
- よくあるトラブルシュート（ログの読み方、kill.flag の扱い など）

どの追加情報が必要か教えてください。