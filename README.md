README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための Python パッケージです。
主な機能は以下の通りです:

- 発注エンジン（ExecutionEngine）: 実口座 / ペーパートレード双方に対応
- 監視サブシステム: システム状態、注文ログ、リスクを定期チェックしてアラート・Kill Switch を管理
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- 研究モジュール: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索（IC 等）
- AI モジュール: ニュースのセンチメント評価（OpenAI）や市場レジーム判定
- 運用ツール: Paper Trading の検証レポート生成、.env ウィザード、設定検証 CLI
- ローカル永続化: SQLite（監視ログ等） / DuckDB（時系列・研究データ）

主な特徴
---------
- 環境に依存しない設定管理（.env / .env.local の自動読み込み）
- ペーパートレード時は本番 DB と分離（data/paper_trading.db）
- 監視は専用 SQLite を使用し、発注とは独立して稼働
- OpenAI（gpt-4o-mini 想定）連携によるニュース NLP / レジーム判定（API キー必要）
- ログは標準出力 + 日次ローテートファイル（logs/<app>.log）

動作環境（推奨）
----------------
- Python 3.10 以上（typing の | 記法を使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証を行いたい場合）

セットアップ手順
----------------
1. リポジトリをクローンして project root に移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（requirements.txt が無ければ手動で）
   - pip install duckdb psutil openai
   - もし YAML 検証を使うなら: pip install pyyaml
4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - またはプロジェクトルートに .env を手動作成
   - 自動ロード: プロジェクトルートに .env/.env.local があると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 推奨:
- KABUSYS_ENV: execution 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要エントリポイント）
-----------------------------

- 設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます
  - run_execution は data/stop_requested.flag を検知するとエンジンを停止します
  - 実行中は data/execution.pid に PID が書き出されます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能
  - 監視は本番の sqlite_path を常に使用（環境にかかわらず同一）
  - 監視は data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH より優先)
  - 期間内の稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出力します

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - raw_news を OpenAI に投げて ai_scores テーブルに書き込みます
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
    - ETF 1321 の ma200 乖離 + マクロニュースを合成して market_regime に書き込み

停止・Kill フラグ
-----------------
- 運用上の終了要求はフラグファイルを用いて行います:
  - data/stop_requested.flag: run_execution / run_monitoring がチェックする停止フラグ（起動前に存在すると起動をスキップ）
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に対する停止シグナルを表現します（KillSwitch は監視側で評価して書き込む）
- run_execution/run_monitoring はこれらのファイルを検知して安全に停止します

ロギング
--------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使って、
  - stdout（StreamHandler）
  - 日次ローテートファイル（logs/<app_name>.log、30日分保持）
  を設定します
- ログ出力レベルは LOG_LEVEL 環境変数や引数で制御できます

ディレクトリ構成（抜粋）
---------------------
以下はソースツリー（src/kabusys）内の主なモジュール・パッケージの一覧（本リポジトリ内に存在するファイルに基づく抜粋）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数/設定取得ユーティリティ（.env 自動読み込み）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコア付け
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義と DB ラッパー
    - monitoring_engine.py  — 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py     — システム状態 / データ鮮度監視
    - trade_monitor.py      — （注文監視: ソース未掲示だが存在を想定）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — KillSwitch（kill.flag 生成）
    - alert_manager.py      — （アラート管理: ソース未掲示だが存在を想定）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み付け
    - position_sizing.py    — 発注株数計算（リスク制限・ロット丸め）
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py    — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン計算・IC・統計サマリー
    - __init__.py
  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - __init__.py

（注）上記は実装済みファイルおよび参照される主要なモジュールを示しています。その他 Execution / Order 関連の詳細実装は別ファイル（execution/*.py 等）に分かれています。

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）、KILL_FLAG_CLEAR_ON_START の値等を十分に確認してください
- OpenAI を利用する機能は API キーと通信のコストが発生します。使用する際は api_key の設定とレート制御に注意してください
- DB ファイルはデフォルトで data/ 配下に格納されます。バックアップ・永続化の運用を検討してください
- run_execution はペーパートレード時に paper_trading 用 DB を使って本番 DB と分離します。KABUSYS_ENV を適切に設定してください

よくある操作例
---------------
1. .env を作成して設定を検証する:
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視プロセスを起動する（ポーリング間隔を 30 秒にする例）:
   - export MONITOR_POLL_INTERVAL=30
   - python -m kabusys.run_monitoring

3. ペーパートレード実行エンジンを起動する:
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

4. ペーパートレード検証レポートを作る:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - または DB を指定: --db /path/to/data/paper_trading.db

サポート・拡張
---------------
- config/*.yaml やマスタデータ、OrderManager / Reconciler / RiskManager の実装を差し替えることで戦略・発注ロジックを拡張できます
- AI 部分は OpenAI 呼び出し箇所をモック可能に設計されているためテストしやすく、他 LLM へ差し替えも比較的容易です

ライセンス・バージョン
--------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）

---

この README はコードベースの主要機能・運用フローをまとめたものです。追加の実行スクリプトやコンポーネントがある場合は、それらに合わせて README を更新してください。必要なら実際の起動例や systemd / supervisor / Docker などを用いたデプロイ手順のテンプレートも作成します。必要であれば教えてください。