KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ用ライブラリ群と実行・監視スクリプトを含むプロジェクトです。  
主に以下の責務を持ちます。

- 発注エンジン（ExecutionEngine）とその周辺コンポーネント（OrderManager, RiskManager, Reconciler 等）
- 監視サブシステム（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch 等）
- ポートフォリオ構築ユーティリティ（銘柄選定、重み付け、ポジションサイズ算出）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 支援モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 開発支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
-------
- 実行環境モード：KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading モードでは MockBrokerClient を使い、発注データは paper_trading.db に分離
- モジュール化された監視系：監視ログは SQLite に永続化（monitoring.db）
- DuckDB を用いた分析・研究処理（prices_daily, raw_financials 等を参照）
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント & レジーム判定（API キー必要）
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）
- プロセス優先度や CPU affinity のユーティリティを提供（psutil 必須）
- 設定ウィザード & 検証 CLI により起動前チェックを容易化

セットアップ
-----------
前提
- Python 3.10+
- SQLite（標準ライブラリで可）
- 任意の DB ファイル保存用の書き込み権限（data/ ディレクトリ等）

推奨パッケージ（最低限）
- duckdb
- psutil
- openai (AI モジュールを使う場合)
- PyYAML（設定ファイルの検証を行う場合）

例（pip）
```
pip install duckdb psutil openai pyyaml
```

環境変数 / .env
- プロジェクトルートに .env を置くと自動読み込みされます（.env.local は上書き）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/…、デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュール利用時に必要)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止制御関連）

例 .env（簡易）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

設定ウィザード / 検証
- .env の対話式作成:
  python -m kabusys.config_setup
- 設定検証（.env と config/*.yaml のチェック）:
  python -m kabusys.validate_config
  オプション: --strict で警告も失敗扱いにする

ログ
----
- setup_logging() によりルートロガーが設定されます。
- デフォルトログディレクトリ: logs/
- ログはコンソール（stdout）および日次ローテーションファイル（logs/<app_name>.log）へ出力されます。
- LOG_DIR 環境変数で出力先を変更可能。

実行方法
--------
起動スクリプト（パッケージモードで実行可能）

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に発注ログを記録する（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop をかけるには data/stop_requested.flag を作成してください（実行スレッドが検出して停止します）。
  - PID ファイル: data/execution.pid（デフォルト）

- 監視ループ起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring

  特記事項:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト: 60）。
  - 監視は常に settings.sqlite_path（監視 DB）を使用します（環境に依らず本番 sqlite_path を参照する設計）。
  - 監視プロセスも stop_requested.flag を検出して停止します。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

  デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- 研究・分析スクリプト / AI スコアリング（モジュール直接呼び出し）
  - AI ニューススコア: kabusys.ai.score_news を呼ぶ（DuckDB 接続と target_date を渡す）。
  - レジーム判定: kabusys.ai.regime_detector.score_regime を直接モジュールから呼べます（OpenAI API キー必須）。
  （CLI エントリポイントは提供されていないものの、スクリプトやジョブからインポートして利用します）

監視と停止制御（Kill Switch / Flags）
----------------------------------
- stop_requested.flag: run_execution / run_monitoring がループを終了するために参照する "停止要求" 用ファイル（data/stop_requested.flag）。
- kill.flag: KillSwitch による ExecutionEngine 停止シグナル。KillSwitch はリスクやドローダウン超過等の条件でこのファイルを書き込み、ExecutionEngine 側は Settings.kill_flag_path を監視して処理を停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ディレクトリ構成（要点）
---------------------
以下は src/kabusys 以下の主要ファイルとサブパッケージ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・資金配分ロジック
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — モメンタム等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC 等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI と MA を合成）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - system_monitor.py      — システム監視（CPU / メモリ / データ鮮度 等）
    - trade_monitor.py       — 注文監視（滞留注文等）※ソース内にあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込みロジック
    - monitoring_engine.py   — 複数モニタの束ね（ポーリング制御）
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

使い方の例
-----------
1) .env を対話式で作る:
   python -m kabusys.config_setup

2) 設定検証:
   python -m kabusys.validate_config
   （--strict を付けると警告も失敗として exit code 1）

3) 実行エンジン（例: ペーパートレード）を起動:
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution

4) 監視プロセスを起動:
   python -m kabusys.run_monitoring
   （MONITOR_POLL_INTERVAL=30 で 30 秒間隔に変更可能）

5) ペーパートレード検証レポート:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意事項 / トラブルシューティング
---------------------------------
- process_priority.set_process_priority() は権限が必要な場合があります（Linux の nice 負の値や Windows のプロセス優先度）。失敗しても警告が出るだけで続行します。
- DuckDB や OpenAI API 呼び出しはネットワーク・バージョン互換性に依存します。AI モジュールではリトライやフォールバック（無効時はスコア 0.0）を実装していますが、API キーの設定は必須です。
- logs/ と data/ ディレクトリは起動時に作成されますが、権限により作成できない場合はコンソールログのみになります。
- .env は絶対にコミットしないでください（機密情報を含むため）。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__version__ で管理（現在 0.1.0）。
- ライセンス情報はこのリポジトリの LICENSE ファイルに従ってください（存在する場合）。

さらに
------
この README はコードベースの主要機能を要約したものです。より詳細な設計指針（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている想定です。運用・本番導入時は config/*.yaml やドキュメントを参照し、設定検証（python -m kabusys.validate_config）と十分なテストを行ってください。

ご要望があれば、README に含めるサンプル .env、systemd ユニット / Supervisor 設定例、デプロイ手順（Docker/systemd/cron など）も作成します。