KabuSys
=======

日本株向けの自動売買 / リサーチ基盤ライブラリです。  
このリポジトリには、実行エンジン（ExecutionEngine）／監視（Monitoring）／ポートフォリオ構築／リサーチ／AI（ニュースNLP・レジーム判定）など、取引運用に必要な主要コンポーネントが含まれています。

概要
----
- 目的: 日本株向けの自動売買システムおよび研究ツールの骨組みを提供する。
- 設計方針:
  - 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替。
  - データ永続化に DuckDB（分析） / SQLite（監視・発注ログ）を使用。
  - OpenAI を利用したニュースセンチメント評価やレジーム判定をサポート（APIキー必須）。
  - .env による設定管理、対話式ウィザードと検証ツールを提供。

主な機能一覧
-------------
- 実行エンジンの起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード専用 DB に分離。
  - ブローカークライアント・オーダー管理・リスク管理・リコンサイル機能の組立てと実行スレッド運用。
- 監視ループ（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてログ保存・アラートや Kill Switch 評価を行う。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず "本番" の sqlite_path を使用する仕様。
- 監視 DB 層（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・読み書きユーティリティ。
- リスク監視（risk_monitor）
  - ドローダウン・ポジション数超過の検出と risk_logs / dashboard 更新、Kill Switch トリガーの補助。
- ポートフォリオ構築ユーティリティ（portfolio）
  - 候補選定、等金額／スコア重み配分、セクター上限チェック、ポジションサイズ計算（単元株対応）などの純粋関数群。
- リサーチ（research）
  - DuckDB 上でのファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン計算、IC 計算、統計サマリ。
- AI（ai）
  - ニュース記事を LLM（OpenAI）で評価して ai_scores に保存する news_nlp。
  - ETF とマクロ記事を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定する regime_detector。
- ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
  - ペーパートレードの検証レポート出力スクリプト（tools/paper_verification_report）
- ユーティリティ
  - 一貫したログ設定（utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
  - Settings（環境変数のラッパ）および自動 .env ロード機能

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML があると validate_config が YAML のパースを検証できます: pip install PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、上記は最低限の例です。実行環境に合わせて追加してください。

4. 環境変数の初期化
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定（news_nlp / regime_detector で使用）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
---------------------
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御:
    - development: 開発（発注なし）
    - paper_trading: ペーパートレード（MockBroker、PAPER_TRADING_SQLITE_PATH を使用）
    - live: 本番（実口座）
  - ExecutionEngine は data/execution.pid を使い、data/stop_requested.flag により停止を監視します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止用フラグ:
    - data/stop_requested.flag を作成するとループは次のポーリングで終了します。
    - Kill Switch（監視結果により data/kill.flag を書込み）により ExecutionEngine に停止シグナルを送れます。
  - 監視は監視用 SQLite（settings.sqlite_path）にログを永続化します（監視は環境にかかわらず本番 sqlite_path を使用します）。

- .env の作成／更新ウィザード
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - --strict: 警告を FAIL 扱いにする

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI モジュール（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キー（api_key 引数 or OPENAI_API_KEY 環境変数）が必要です。

環境変数（主なもの）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（テスト用）

重要な挙動・注意点
-----------------
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番の監視 DB）を使用する実装になっています。環境を分離したい場合は sqlite_path を個別に設定してください。
- ペーパートレードでは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に履歴を記録し、本番 DB と分離します。
- OpenAI を使った処理は外部 API 呼び出しを行うため、API レート制限やネットワーク障害に対するリトライ処理が組み込まれていますが、API キーやコストに注意してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup も README にもその旨の注記があります）。
- kill.flag / stop_requested.flag による停止はファイルベースのシンプルな仕組みです。運用上適切に管理してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロード / Settings
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

subpackages:
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（OpenAI）
  - regime_detector.py     — 市場レジーム判定（ETF + マクロ）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化・永続化 API
  - system_monitor.py      — CPU/MEM/DISK/データ鮮度/プロセス監視
  - trade_monitor.py       — （発注ログ監視: 参照用）
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — data/kill.flag 書込みユーティリティ
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信: 参照用）
- execution/
  - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
  - execution_engine.py    — ExecutionEngine 本体（セッション実行）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- monitoring/              — 上記 monitoring の実装
- tools/
  - __init__.py
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ロギング初期化ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity
  - __init__.py

補足（運用ヒント）
-----------------
- ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で変更可。
- 実行プロセスの優先度は set_process_priority("high") で可能ですが、権限により設定に失敗することがあります（警告のみ）。
- validate_config の YAML 検証は PyYAML の有無に依存します。config/*.yaml を使う場合は PyYAML を入れておくと良いです。
- Paper Trading の成績評価は tools/paper_verification_report.py を参照。P95 レイテンシや成功率などの閾値が組み込まれています。

ライセンス / バージョン
-----------------------
パッケージのバージョンは src/kabusys/__init__.py の __version__ で管理されています（例: 0.1.0）。ライセンス情報はリポジトリのルートに置いてください（本 README には含めていません）。

問題が発生した場合
-----------------
- 設定関連の問題: python -m kabusys.validate_config を実行して診断してください。
- DB スキーマ問題: monitoring_db.init_monitoring_db は冪等的にテーブルを作成・マイグレーションを試みます。
- AI 関連のエラー: OPENAI_API_KEY の設定と API 利用制限を確認してください。ログに詳細が出ます。

---
この README はコードベースを参照して要点をまとめたものです。実行環境や運用方針に応じて .env の設定や DB パスなどを適切に調整してください。