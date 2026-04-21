KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。
主な目的は以下:

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）までの実行基盤
- システム監視（Monitoring）・リスク監視・Kill Switch による安全停止
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いたオフライン分析）
- ニュースの NLP によるセンチメントスコアリング（OpenAI API を利用）
- ペーパートレードモード（本番 DB と分離して安全に検証可能）

本リポジトリはモジュール化されており、実行コンポーネント（execution / monitoring）、リサーチ（research）、ポートフォリオ構築（portfolio）、AI（news_nlp / regime_detector）、ユーティリティ類を含みます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて paper_trading（MockBroker）/ live（実運用）を切替
  - Paper Trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用
  - 発注管理、リスク管理、再同期（reconciler）等の組立てを行う
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag を書き込む KillSwitch による ExecutionEngine 停止
  - 監視ログは SQLite（data/monitoring.db）へ保存。DuckDB と併用
- 監視 DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブル定義とマイグレーション
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等重／スコア重み）、ポジションサイズ計算（単元株丸め、aggregate cap）
  - セクター上限やレジーム乗数の適用
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
  - DuckDB を用いた SQL ベースの集計
- AI モジュール（ai）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を生成・書き込み
  - regime_detector: ETF の MA 乖離とマクロニュースを合成して市場レジーム判定
- ツール
  - config_setup.py: .env を対話式に生成/更新するウィザード
  - validate_config.py: .env / config/*.yaml の設定検証 CLI
  - tools/paper_verification_report.py: ペーパー検証レポート生成

動作環境と依存関係
------------------
- 推奨 Python: 3.10 以上（型アノテーションに union 演算子 `|` を使用しているため）
- 外部パッケージ（主に、本リポジトリで使われているもの）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML：config/*.yaml を内容検証する場合に必要
- DB: SQLite（標準ライブラリ）を永続化に使用。分析用に DuckDB を利用。

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （YAML 検証を行うなら）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env を用意
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   主な環境変数（デフォルト値は Settings クラスに記載）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - OPENAI_API_KEY: OpenAI API を使う機能で必要
   - PAPER_FILL_MODE（paper_trading 時の約定挙動）: instant / partial / never / reject
   - MONITOR_POLL_INTERVAL（秒）: 監視ループの間隔（デフォルト 60）

5. データディレクトリを作成
   - mkdir -p data logs

使い方
------
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）かつ MockBroker を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に停止させるには Kill Switch（kill.flag）や stop_requested.flag による制御、または ExecutionEngine の外部停止処理を用います。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は monitoring DB（Settings.sqlite_path）へ必ず書き込みます（環境に関わらず本番 monitoring DB を利用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - modules:
    - kabusys.ai.news_nlp.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

停止・Kill Switch の仕組み
-------------------------
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
- run_execution/run_monitoring では data/stop_requested.flag を検出するとループを終了します。
- ExecutionEngine は pid ファイル（data/execution.pid）を書きます。監視プロセスはこの pid ファイルを確認してプロセスの稼働検知を行います。

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ログ出力先は LOG_DIR 環境変数または setup_logging の引数で変更可能。
- ログレベルは LOG_LEVEL で制御します（DEFAULT: INFO）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証ツール
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- ai/
  - news_nlp.py            — ニュース NLP / OpenAI 連携
  - regime_detector.py     — レジーム判定ロジック

- portfolio/
  - portfolio_builder.py   — 候補選定 / 重み算出
  - position_sizing.py     — 発注株数計算・aggregate cap 処理
  - risk_adjustment.py     — セクターキャップ / レジーム乗数

- research/
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・アクセサ
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （実装参照）発注ログ監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — モニタリングの統合実行

- execution/
  - execution_engine.py    — ExecutionEngine 本体（EngineConfig / run_session 等）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py       — 統一ログ設定
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

その他の注意点・運用メモ
-----------------------
- 設定検証: 起動前に python -m kabusys.validate_config を実行して設定の欠落や明らかな問題を検出してください。
- 本番（KABUSYS_ENV=live）では特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。validate_config は live 時に追加警告を出します。
- Paper Trading は本番 DB と分離されるよう設計されています。デフォルトで data/paper_trading.db を使用します。
- OpenAI を使う処理は API 呼び出し制限やエラーに備え、リトライやフォールバック（失敗時はスコア 0 等）を実装していますが、実運用時は API コストやレート制限に注意してください。
- DuckDB / SQLite のファイルパスは Settings（または .env）で設定可能です。ログや DB ファイルは .env を .gitignore に登録してリポジトリにコミットしないでください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__（現在 0.1.0）。
- ライセンス情報が別途ある場合はリポジトリルートの LICENSE を参照してください。

問い合わせ
----------
実装上の質問や改善提案がある場合はリポジトリの issue を利用してください。

---  
この README はリポジトリ内のコード（config.py、run_execution.py、run_monitoring.py、monitoring/*、portfolio/*、research/*、ai/*、tools/* 等）を元に作成しています。実際の運用にあたっては .env の設定や外部サービス（kabuステーション、J-Quants、OpenAI など）の認証情報、ローカル環境のリソース（ディスク・CPU）にご注意ください。