README — KabuSys
=================

概要
----
KabuSys は日本株自動売買のためのモジュール化されたコードベースです。  
主な目的は「シグナルの研究・ファクター計算」「ポートフォリオ構築」「発注実行（本番/ペーパートレード）」「システム監視・リスク監視」「ニュースを使った AI スコアリング」などの機能を提供することです。  
モジュール群は独立性を意識して設計されており、DB（DuckDB / SQLite）や外部 API（kabuステーション、J-Quants、OpenAI）と連携します。

主な特徴
--------
- 発注実行エンジン（ExecutionEngine）を本番／ペーパートレードで分離して動作可能
- 監視コンポーネント（SystemMonitor、TradeMonitor、RiskMonitor）による自動監視と Kill Switch（データ/フラグによる停止）
- DuckDB を利用したファクター計算・リサーチ（momentum / volatility / value など）
- ニュースを用いた LLM（OpenAI）によるセンチメントスコアリング（ai.news_nlp）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム乗数）
- ログ・プロセス優先度設定など運用を意識したユーティリティ（logging_setup、process_priority）
- 対話式 .env セットアップと設定検証ツール（config_setup、validate_config）
- ペーパートレード検証レポート生成ツール

必要条件
--------
- Python 3.10 以上（型アノテーション、Union 表記等を利用）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML の検証を行う場合）
- （任意）外部サービスの資格情報:
  - JQUANTS_REFRESH_TOKEN（J-Quants）
  - KABU_API_PASSWORD（kabuステーション）
  - OPENAI_API_KEY（OpenAI：ニュース/レジーム判定機能を利用する場合）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合は個別インストール）
   - pip install duckdb psutil openai pyyaml

3. （オプション）開発インストール
   - pip install -e .

環境変数 / 設定
---------------
設定は .env ファイルまたは環境変数で行います。代表的なキー:

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用系
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
  - paper_trading のときは MockBroker を使用し、別 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

DB パス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

その他
- OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp, ai.regime_detector）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"0"/"1"）

.env の作成・検証
-----------------
対話式ウィザードで .env を作成:
- python -m kabusys.config_setup

作成内容を検証:
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit code 1）

使い方（主要なスクリプト）
--------------------------

1) Execution（発注エンジン）を起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag があると起動しません
  - 実行中に stop flag を作成するとエンジンを停止します
  - 起動時、プロセス優先度を high に設定します

2) Monitoring（監視ループ）を起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照）
  - data/stop_requested.flag を検知するとループを終了します

3) ペーパートレード検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能
  - 稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL を判定

4) AI スコアリング / レジーム判定（プログラム呼び出し）
- OpenAI API キーが必要（OPENAI_API_KEY）
- Python から直接呼び出す例（簡易）:
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, datetime.date(2026, 4, 10))
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, datetime.date(2026, 4, 10))

運用メモ / フラグ
-----------------
- 停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ
  - data/kill.flag — KillSwitch が書き込む（Execution 停止のため）
- PID ファイル:
  - data/execution.pid（デフォルト。Settings.pid_file_path で変更可能）
- ログ:
  - デフォルト logs/<app_name>.log に日次ローテートで出力
  - setup_logging を各起動スクリプトで呼んで統一的に設定

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の自動ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite の監視 DB 永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注関連の監視（滞留注文検出等）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — アラート送信（LINE 等）（実装先による）
  - execution/
    - broker_factory.py      — BrokerClient の生成（本番 / Mock 切替）
    - execution_engine.py    — 発注セッション実行ロジック
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（発注周りの実装）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケール調整
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py — IC / forward returns / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py     — ETF MA + マクロニュースで市場レジーム判定

注意事項 / 運用ガイド
--------------------
- KABUSYS_ENV=paper_trading を使うと実際発注を行わずペーパートレード用 DB に記録します。テスト時はこのモード推奨。
- .env ファイルは絶対にリポジトリへコミットしないでください（秘密情報含む）。
- OpenAI 利用時は API レート制限やエラーに対してリトライやフェイルセーフ処理が組み込まれていますが、コストやプライバシーに注意してください。
- monitoring は production sqlite_path を参照します。テスト環境で monitoring を動かす場合は Settings を調整するか環境を分けてください。
- process_priority はプラットフォーム依存（Windows / POSIX）です。権限が必要な場合は設定に失敗することがあります（ログに警告）。

貢献 / 開発
------------
- 新しい依存を追加したら requirements.txt を更新してください。
- 単体テスト・統合テストはモジュールごとに用意することを推奨します（AI 呼び出し部はモック化）。
- duckdb のスキーマ変更（prices_daily, raw_financials など）を行う際は研究・予測モジュールとの整合性を確認してください。

ライセンス / バージョン
-----------------------
- 現行バージョン: 0.1.0（kabusys.__version__）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（プロジェクトに設定されている場合）。

付録：よく使うコマンド例
---------------------
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要構成・運用方法をまとめたものです。詳細な実装や追加の運用手順は各モジュールの docstring / コメントを参照してください。