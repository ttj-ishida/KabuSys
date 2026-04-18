README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部です。本リポジトリは以下の主要機能を含みます:

- 実行エンジン (ExecutionEngine) の起動スクリプトと周辺コンポーネント（注文管理、リスク管理、ブローカー抽象化）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と監視ループ起動スクリプト
- DuckDB を用いたファクター・リサーチモジュール（momentum / volatility / value 等）
- ニュースを LLM で評価する AI モジュール（OpenAI 経由のニュース NLP、レジーム判定）
- ペーパートレード用検証レポート生成ツール
- 環境設定ウィザード (.env 作成補助) と設定検証 CLI

設計上のポイント:
- .env / 環境変数で設定管理（自動ロード機能あり）
- 本番とペーパートレードで DB を分離（paper_trading 環境時は data/paper_trading.db を使用）
- ログは標準出力 + 日次ローテートファイル出力 (logs/<app>.log)
- LLM 呼び出し（OpenAI）を用いる機能は API キーが必要。失敗時はフォールバック挙動を持つよう安全設計

機能一覧
--------
主な機能（モジュール）:

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（停止フラグで終了）
- 設定管理
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 環境変数・config/*.yaml の起動前検証
  - config.py — Settings クラス（環境変数のラッパ）
- 監視
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマ & DB 操作
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py — 監視ロジック
  - monitoring/kill_switch.py — Kill Switch（flag ファイル書き込みで ExecutionEngine 停止）
  - monitoring/monitoring_engine.py — 各 Monitor を束ねるランナー
- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py, risk_adjustment.py, position_sizing.py
- リサーチ（DuckDB を利用）
  - research/factor_research.py, feature_exploration.py
- AI（OpenAI 経由）
  - ai/news_nlp.py — ニュースを LLM でスコアリングして ai_scores に格納
  - ai/regime_detector.py — マクロ + ETF MA200 を用いたレジーム判定
- ユーティリティ
  - utils/logging_setup.py — 統一的なログ設定
  - utils/process_priority.py — プロセス優先度設定（Windows / POSIX を吸収）
- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成

セットアップ手順
--------------
1. クローン / コピー
   - リポジトリをクローンまたは取得し、プロジェクトルートに移動します。

2. Python 環境
   - Python 3.9+ を推奨。仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリインストール（例）
   - 必要なパッケージ（少なくとも以下）をインストールしてください。
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （このリポジトリに requirements.txt がある場合はそちらを使ってください。）

4. 環境変数 (.env) の準備
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で .env を作成してください。
   - 主要な環境変数（最低必須）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - LOG_DIR（ログ格納ディレクトリ、デフォルト logs/）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）

   - 自動読み込み:
     - config.py はプロジェクトルートに .env / .env.local があれば自動で読み込みます（既存 OS 環境変数を上書きしません）。
     - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ
   - デフォルトでは data/ 下に DB などを作成します。必要に応じてパーミッションやパスを確認してください。

基本的な使い方
--------------

設定検証
- .env を作成したら設定を検証します:
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする場合:
    - python -m kabusys.validate_config --strict

ExecutionEngine を起動
- 実行（本番 / ペーパーは KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
- 注意:
  - ペーパートレード (KABUSYS_ENV=paper_trading) の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) に記録されます。
  - ExecutionEngine は起動時に PID ファイルを data/execution.pid に作成します（Settings.pid_file_path で変更可）。
  - data/stop_requested.flag が存在すると起動を中止 / 既存スレッドを停止します。

Monitoring を起動
- SystemMonitor のポーリングループ:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は監視用 SQLite（Settings.sqlite_path: data/monitoring.db デフォルト）を使用します（Monitoring は常に本番 sqlite_path を使用する仕様）。

Paper Trading 検証レポート
- ペーパートレード DB から検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も優先度として使えます。

AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
- news_nlp.score_news / regime_detector.score_regime をモジュール経由で呼び出して利用できます。
  - 例: Python REPL で duckdb 接続を渡して利用する
- API 呼び出しはリトライや失敗時フォールバックを備えていますが、API キーは必須です。

停止・Kill Switch
- Monitoring の Kill Switch は monitoring/kill_switch.py で実装されています。Kill Switch がトリガーされると data/kill.flag が書き込まれ、ExecutionEngine 停止要求が送られます。
- 手動で停止したい場合は data/stop_requested.flag を作成するとループが検知して終了します。
- 再起動前に Kill Flag を手動で削除するか、KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（本番では 0 を推奨）。

ログ
- logging_setup.py によりルートロガーは stdout と日次ローテートファイル（logs/<app>.log）に出力します。
- LOG_DIR 環境変数でログ保存先を変更可能。ディレクトリ作成に失敗した場合はコンソールのみになります。

サンプル .env（最小例）
-------------------
以下は最小構成の例（実際の値は実運用に合わせて変更してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

ディレクトリ構成
----------------
主要なファイル・ディレクトリ（src/kabusys 以下を基準）:

- kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 一元ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (アラート管理は実装ファイル群に含まれます)
  - execution/                — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/                — ポートフォリオ構築（builder / sizing / risk_adjustment）
  - research/                 — DuckDB ベースのファクター計算・解析
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                     — デフォルト DB / フラグファイル配置想定（プロジェクトルートに data/ を作る）

トラブルシューティング
---------------------
- .env が読み込まれない:
  - config.py はプロジェクトルート（.git or pyproject.toml を検出）を起点に .env を読み込みます。パッケージ配置や CWD により期待通りに動かない場合は環境変数を明示的にセットしてください。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ログファイルが作れない:
  - 権限やパスを確認。LOG_DIR を書き込み可能なディレクトリに変更できます。ファイル出力に失敗してもコンソールログは出力されます。

- OpenAI 呼び出しで失敗:
  - OPENAI_API_KEY の設定を確認、API の利用制限（レート制限）に注意。ライブラリのバージョン差異がある場合はエラー観察ログを確認してください。news_nlp / regime_detector はリトライ戦略を持ち、失敗時はフォールバックしますが、結果は欠落する可能性があります。

開発向けメモ
-------------
- validate_config.py により起動前に一般的な設定不備を検出できます。
- monitoring_db.init_monitoring_db は既存 DB に対して冪等にマイグレーション（カラム追加など）を行います。
- ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境の影響を制御できます。

ライセンス・貢献
----------------
- 本リポジトリ固有のライセンス情報や貢献ポリシーがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

以上。必要があれば、README に記載するコマンド例の追加や、各モジュールのより詳細なドキュメント（API 使用例、設定項目一覧、DB スキーマ詳細など）を作成します。どの部分を優先して展開すればよいか教えてください。