README.md

KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究用ライブラリ兼実行基盤です。  
価格データ集計（DuckDB）、監視・ログ（SQLite）、発注エンジン（ExecutionEngine）、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価などの機能を備えています。  
このリポジトリはライブラリ部分と起動用スクリプト群を含み、ローカル開発・ペーパートレード・本番環境に対応した設定が可能です。

主な機能
--------
- ExecutionEngine：注文管理・ブローカークライアント連携・リスク管理を行う実行エンジン
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、本番 DB と分離（data/paper_trading.db）
- 監視（Monitoring）
  - System / Trade / Risk 各種監視器と Kill Switch、通知機構（AlertManager）
  - 監視ログは SQLite に永続化（data/monitoring.db）
- ポートフォリオ構築
  - 候補選定、等分配・スコア加重、ポジションサイズ算出（単元丸め、集約キャップ）
  - セクター上限やレジームに応じた調整
- 研究モジュール（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - 将来リターン、IC（Spearman）計算、ファクター統計
- AI モジュール
  - ニュース NLP（OpenAI）による銘柄センチメント集計（ai_scores への書き込み）
  - レジーム判定（ETF MA とマクロセンチメントの合成）
- 運用ユーティリティ
  - .env 対話式セットアップ（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

前提・依存
----------
（プロジェクトで使用する主要パッケージ例）
- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml 検証時）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil openai
   - （設定検証で YAML を使うなら）pip install PyYAML

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants / kabuAPI / DB パスなどを入力します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK と表示されます。--strict を付けると警告も失敗扱いになります。

主要な環境変数（主なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- PAPER_FILL_MODE（ペーパートレードの約定モード: instant|partial|never|reject）
- OPENAI_API_KEY（AI モジュールを使う場合に必要）
- LOG_LEVEL, LOG_DIR（ログ設定）

基本的な使い方
--------------

.env 作成・検証
- .env を作成：
  - python -m kabusys.config_setup
- 設定検証：
  - python -m kabusys.validate_config [--strict]

ExecutionEngine の起動
- 実行（デフォルト動作は Settings に従う):
  - python -m kabusys.run_execution
- 動作のポイント：
  - プロセス優先度を "high" に設定します（プラットフォーム依存で失敗しても続行）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop を要求するにはプロジェクトルートの data/stop_requested.flag を作成してください（run_execution はこのフラグを監視してエンジン停止を促します）。

Monitoring の起動
- 実行：
  - python -m kabusys.run_monitoring
- 動作のポイント：
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は本番用 sqlite_path を環境にかかわらず使用します（監視ログは常に monitoring DB に入る設計）。
  - 監視は data/stop_requested.flag を見て自分自身を終了できます。

Paper Trading 検証レポート
- 生成：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を明示する場合：
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 簡易的に稼働率・成功率・P95 レイテンシ等を算出し PASS/FAIL を表示します。

AI モジュール（プログラムからの利用例）
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数か引数で指定）
- 例（Python REPL やスクリプト内）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

ログ設定
- ログはデフォルトで logs/<app_name>.log（日次ローテート）と stdout に出力されます。
- 環境変数 LOG_DIR、LOG_LEVEL で出力先・レベルを調整可能。
- 例: export LOG_LEVEL=DEBUG

停止・Kill Switch
- 強制停止や運用停止シグナル:
  - data/stop_requested.flag — 起動スクリプト（execution／monitoring）はこれを見て自己終了します（手動停止要求用）。
  - KillSwitch（監視コンポーネント）が条件を満たした場合、Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。運用ルールに合わせて kill.flag を監視する仕組みを組み込んでください。
- フラグをクリアするにはファイルを削除:
  - rm data/stop_requested.flag
  - rm data/kill.flag

注意点・運用上のヒント
--------------------
- paper_trading は本番 DB と分離されています。テストデータが本番 DB に影響することはありません（paper_trading 用 SQLite を使用）。
- AI 呼び出しは API エラーに対してリトライやフォールバック処理を含みますが、API キーやクォータには注意してください。
- DuckDB / SQLite のパスやログディレクトリの親ディレクトリが存在しない場合、validate_config が警告を出します。必要なディレクトリは起動時に自動作成されるケースが多いですが、事前作成して権限を確認することを推奨します。
- process priority / cpu affinity 設定は psutil を使用します。アクセス権限により設定できない場合は警告ログが出てスキップされます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py              — 環境変数/設定読み込みロジック
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 起動前設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — Monitoring 起動スクリプト

- execution/              — 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
- monitoring/             — 監視コンポーネント（system_monitor, trade_monitor, risk_monitor, monitoring_db, kill_switch, monitoring_engine, alert_manager 等）
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
- portfolio/              — 銘柄選定・配分・サイズ計算（portfolio_builder, position_sizing, risk_adjustment）
- research/               — ファクター計算・特徴量探索（factor_research, feature_exploration）
- ai/                     — AI 関連（news_nlp, regime_detector）
- tools/                  — ユーティリティスクリプト（paper_verification_report 等）
- data/                   — 実行時生成データ（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag, ...）
- utils/                  — ロギング設定・プロセス優先度等のユーティリティ（logging_setup, process_priority）

主要スクリプト（起動コマンド）
----------------------------
- .env 作成:       python -m kabusys.config_setup
- 設定検証:        python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証:      python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

最後に
-----
この README はコードベースから抽出した主要機能・運用手順の概要を示します。実運用前には必ず python -m kabusys.validate_config による検証と、.env の内容確認を行ってください。開発者向けの詳細設計（PortfolioConstruction.md や StrategyModel.md 等）が別途ある場合はそちらに従ってください。