# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。

このリポジトリは、システム監視・発注実行・ポートフォリオ構築・リサーチ・AI 補助機能等を含むモジュール群を提供します。設計方針として「本番ロジックと研究コードを分離」「外部 API 呼び出しは明示」「フェイルセーフ（API失敗はスキップ）」などを採用しています。

以下は本コードベースの概要、機能、セットアップ手順、使い方、主要ディレクトリ構成です。

---

## プロジェクト概要

- 実運用想定の自動売買コンポーネントと研究（research）/ポートフォリオ構築（portfolio）機能を含む。
- DuckDB を分析用 DB、SQLite を監視/注文ログ用 DB に使用。
- 実際の発注は kabuステーション API（Kabu API）や MockBroker（ペーパートレード時）を経由。
- OpenAI（gpt-4o-mini など）を用いたニュースの NLP スコアリングと市場レジーム判定機能を提供。
- 監視用モジュールは監視ループでシステム状態や注文状況・リスクを継続チェックし、必要に応じて Kill Switch（data/kill.flag）を作成して ExecutionEngine を停止可能。

---

## 主な機能一覧

- 実行/監視スクリプト
  - run_execution.py: ExecutionEngine 起動（本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 環境設定・検証
  - config_setup.py: .env の対話式ウィザードで初期作成・更新
  - validate_config.py: .env と config/*.yaml の検証 CLI
- データベース / 永続化
  - monitoring_db.py: SQLite における監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）テーブルの初期化と読み書きユーティリティ
- 監視
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager（アラート送信処理）
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（候補選定・重み・株数計算・セクター制限等）
- リサーチ
  - research/factor_research.py, research/feature_exploration.py（モメンタム・ボラティリティ・バリュー等のファクターや IC 計算）
- AI（OpenAI）連携
  - ai/news_nlp.py: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - ai/regime_detector.py: MA とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレードログから検証レポート生成（稼働率・成功率・レイテンシ等）
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに入る。

2. Python 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）:
   - duckdb
   - psutil
   - openai
   - （オプション）PyYAML（validate_config の YAML 検証）

   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそちらを利用）

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - またはプロジェクトルートに .env を手動で作成。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（一部とデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能利用時に必要
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか (0/1)

5. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - 問題があれば .env を修正後、再実行

6. データディレクトリ等は自動作成されますが、logs/ や data/ を手動で作る場合:
   - mkdir -p data logs

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動（本番または paper_trading は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用（環境に関係なく）。

- .env の対話式生成:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱いになります。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示することも可能。環境変数 PAPER_TRADING_SQLITE_PATH が使われます（優先度は CLI > 環境変数 > デフォルト）。

- AI / リサーチ関数（Python API）:
  - OpenAI キーを環境変数 OPENAI_API_KEY にセットしてから呼び出すか、api_key 引数を渡すことで実行。
  - 例（ニューススコアリング）:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - n = score_news(conn, target_date=datetime.date(2026,4,10), api_key=None)  # 環境変数がある場合 api_key=Noneで可
  - 例（レジーム判定）:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

- ログ:
  - ログは stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。
  - setup_logging() によりログディレクトリは自動作成が試みられます（失敗時はコンソールのみ）。

---

## 監視・停止フラグについて

- Kill Switch（強制停止）:
  - KillSwitch はリスク条件（ドローダウン・ポジション上限等）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
  - kill.flag が既に存在する場合は再書き込みしません（冪等）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- 停止要求フラグ:
  - data/stop_requested.flag が存在すると run_execution/run_monitoring は継続ループを抜けて終了します（安全停止用）。

- PID ファイル:
  - ExecutionEngine は data/execution.pid に PID を書込みます。

---

## 主要設定（Settings）について

config.py の Settings クラスから環境変数を参照します。主な設定：

- DB 関連:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live

- Paper Trading 挙動:
  - PAPER_FILL_MODE: instant | partial | never | reject

- 監視閾値:
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視モジュールで使用）

- ログ:
  - LOG_LEVEL, LOG_DIR

詳細は src/kabusys/config.py を参照してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートモジュールとしたツリーの要約）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前設定検証CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / IO
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （実装ファイル参照）
  - execution/                 — Execution／Order 関連（ファクトリ・エンジン等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記のうち execution 以下の詳細実装は README に抜粋していませんが、起動スクリプトと組み合わせて動作する設計です。

---

## 開発・デバッグのヒント

- 自動で .env を読み込む仕組み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env, .env.local を自動ロードします。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- ローカルでペーパートレードを試す場合:
  - KABUSYS_ENV=paper_trading とし、PAPER_TRADING_SQLITE_PATH を指定すると本番 DB と分離して発注ログが記録されます。

- 監視間隔の調整:
  - MONITOR_POLL_INTERVAL を秒数で指定（例: MONITOR_POLL_INTERVAL=30）。

- ログ出力先:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション・30世代保持）。

---

## よくあるトラブルシューティング

- 必須環境変数未設定エラー:
  - validate_config.py を実行すると不足項目を検出できます。JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須です。

- DuckDB / SQLite ファイルが存在しない:
  - 多くの初期処理は必要に応じてディレクトリ/ファイルを作成しますが、path の親ディレクトリが存在しない場合は警告が出ます。手動で data/ ディレクトリを作ると問題回避できます。

- OpenAI API 呼び出しが失敗する:
  - OPENAI_API_KEY を確認。レート制限や一時的なネットワーク障害は内部でリトライしますが、上限を超えるとスキップされます（fail-safe）。

---

README は必要に応じてプロジェクト特有の運用手順（systemd / cron / supervisor の設定、バックアップ方針、DB マイグレーション方針、テスト手順など）を追記してください。ソースの詳細実装は各ファイルの docstring / コメントを参照すると理解が早いです。