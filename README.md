KabuSys — 日本株自動売買システム
================================

以下はこのコードベースの README です。開発・起動に必要な概要、設定、実行方法、主要ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主な機能は以下を含みます。
- 発注エンジン（ExecutionEngine） — ブローカークライアント経由で注文を発行。paper_trading ではモックブローカーを使用し、本番 DB と分離。
- 監視（Monitoring） — システム状態、注文滞留、リスク（ドローダウン／ポジション数）を定期チェックし、ログ・アラート・Kill Switch を管理。
- ポートフォリオ構築（選定・重み付け・株数決定・セクター制限等） — 純粋関数群で計算を提供。
- 研究（factor / feature exploration） — DuckDB 上の時系列データからファクター計算、将来リターン・IC 計算などを行う。
- AI モジュール — OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- ツール類 — .env 対話ウィザード、設定検証、Paper Trading 検証レポート生成など。

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup）
  - .env の生成・更新を対話形式で実施
- 設定検証 CLI（kabusys.validate_config）
  - .env や config/*.yaml の基本チェック（PyYAML があれば YAML の構文検査も実施）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV による paper_trading / live 振る舞いの切替
  - paper_trading 時は専用 SQLite（data/paper_trading.db）に記録
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可、デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU/Mem/Disk、プロセス PID、データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringDB: SQLite に対する読み書きユーティリティ
- Portfolio（選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算、IC・統計サマリ）
- AI（ニューススコアリング・レジーム判定）
- ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提 / 必要パッケージ
-------------------
（実際の requirements.txt があればそれを参照してください。最低限必要な例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル YAML の構文チェックを行う場合）

pip 例:
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリをチェックアウトしてパッケージが import できるようにする
   - 開発中: プロジェクトルートに移動して仮想環境を作成・有効化
   - 必要パッケージをインストール（上記参照）

2. .env の作成（推奨）
   - 対話式ウィザードで生成:
     python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照すること）
   - ウィザードで設定される主要キー（抜粋）:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意, 通知)
     - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか

3. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付ける

4. DB 初期化
   - 主要スクリプトは起動時に monitoring DB 用テーブルの存在を保証（init_monitoring_db）するので通常は自動で作成されます。
   - DuckDB のスキーマは別途データ投入スクリプト等で準備する想定です。

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  # --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動（実行用）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動をキャンセルします。
  - エンジンは内部で PID ファイル（data/execution.pid）を書きます。

- Monitoring を起動（ポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60 秒）。
  - 監視は Settings が示す sqlite_path（monitoring DB）にログを書きます（環境にかかわらず本番 sqlite_path を使用する点に注意）。
  - 停止: data/stop_requested.flag または Ctrl-C。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルトを優先）

- AI モジュール（スクリプト的な直接呼び出し例）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB のコネクションを受け取り、DB の raw_news / prices_daily 等のテーブルに依存します。

停止・Kill switch 等
-------------------
- 手動停止フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag — 存在を検出すると monitoring/engine/Execution のループを停止します。
- KillSwitch（自動停止判定）
  - 監視が一定条件（例: ドローダウン閾値超過、ポジション数上限）を満たした場合に data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
- 起動時の Kill Flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で可能（本番では注意が必要）。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI を利用する場合必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）デフォルト 60
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

ディレクトリ構成
----------------
（src/kabusys 以下を簡略化して示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + 指数）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラートの送信管理、実装ファイルあり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - execution/                — 発注エンジン関連（OrderManager 等。ソースは一部参照あり）
  - data/                     — データファイル（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - その他: data/*.flag, data/*.pid を使用する運用用ファイル

開発メモ / 注意点
-----------------
- .env は決してコミットしないでください（ウィザードのヘッダーにも注意書きがあります）。
- validate_config は起動前チェックとして必ず実行することを推奨します（特に KABUSYS_ENV=live 時）。
- OpenAI API 周りはリトライや JSON バリデーションの実装が施されていますが、API キー・レート制限に留意してください。
- paper_trading は本番 DB と分離されるように設計されています。paper_trading の挙動を確認する際は PAPER_TRADING_SQLITE_PATH を利用してください。
- run_monitoring は監視ログを書き込みます。MONITOR_POLL_INTERVAL で間隔を調整できます（環境変数で上書き）。
- process priority / cpu affinity の設定はプラットフォーム依存で失敗することがあります（権限不足など）。ユーティリティは失敗時に警告を出してスキップします。

トラブルシューティング（よくある問題）
-------------------------------------
- "環境変数 XXX が設定されていません" エラー:
  - .env を作成して必要なキーを設定してください。config_setup を使うと簡単です。
- DuckDB / SQLite ファイルが見つからない:
  - デフォルトパスは data/kabusys.duckdb / data/monitoring.db / data/paper_trading.db です。環境変数で上書き可能。
- OpenAI の呼び出しが失敗する:
  - OPENAI_API_KEY が設定されているか、ネットワーク・レート制限を確認してください。モジュールはリトライしますが回復しない場合は 0 相当のフォールバックを行う箇所があります。

最後に
------
この README はコードベースの主要な利用方法・設定を網羅的にまとめたものです。詳細な挙動（内部ロジック、DB スキーマ、アルゴリズム）は各モジュールの docstring と実装を参照してください。追加で README に含めたい内容（例: デプロイ手順、CI 設定、より詳細な設定例）があれば教えてください。