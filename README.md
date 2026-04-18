KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。システム監視、発注実行、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を用いたセンチメント評価）などを含むモジュール群で構成されています。設計方針としては「本番用 DB とペーパートレードの完全分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に管理」「フェイルセーフ（API失敗や部分失敗時にシステムを壊さない）」を重視しています。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB に記録します。
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）監視。
- 監視ループ（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して監視ログを SQLite に保存。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用（監視用 DB は環境に依存しない）。
- 監視永続化層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを提供。自動でスキーマ更新を行うマイグレーション処理あり。
- リスク監視（risk_monitor.py）
  - ドローダウン監視、ポジション上限監視、必要に応じてダッシュボード更新とリスクログ登録。
- トレード監視（trade_monitor.py）
  - 滞留注文チェック（stale orders）、約定価格異常チェック（price anomaly）。
- Kill Switch（kill_switch.py）
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送出。
- ポートフォリオ構築（portfolio/**）
  - 候補選定、重み計算（等金額 / スコア加重）、ポジションサイズ計算（リスクベース等）、セクター制約、レジーム乗数。
- 研究用モジュール（research/**）
  - DuckDB を使ったファクター計算（momentum/value/volatility）、将来リターン計算、IC 計算、統計サマリ。
- AI（LLM）統合（ai/**）
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）に問い合わせ、銘柄ごとのセンチメントを ai_scores に書き込む。
  - regime_detector: ETF の MA200 とマクロニュースセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定する。
- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・注文成功率・レイテンシなどの検証レポートを生成。
  - config_setup: 対話式に .env を生成・更新するウィザード。
  - validate_config: .env と config/*.yaml の妥当性チェック（--strict で警告も FAIL 扱い）。

前提（推奨）
------------
- Python 3.10 以上（型注釈に | を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行いたい場合）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、Kabu API パスワード、データベースパス、KABUSYS_ENV などを設定します。
   - .env は絶対に Git 等にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - エラーや警告に従って設定を修正します。
   - --strict を付けると警告もエラー扱いになります。

環境変数（主なもの）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注処理は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録される
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番環境では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ループの秒数（run_monitoring で使用、デフォルト 60）

基本的な使い方
-------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 成功すると exit code 0、エラーがあれば 1 を返します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使います。
  - 実行中は data/execution.pid に PID が書き込まれます。停止は停止フラグの作成（data/stop_requested.flag）または適切な API 経由。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を参照します（環境に依存せず監視DBは共通）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

重要なファイル・フラグ
--------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が存在を検知するとループを停止します（外部からの停止シグナル）。
- data/execution.pid
  - ExecutionEngine 起動時に書かれる PID ファイル。SystemMonitor はこの PID を監視してプロセスの生存を確認します。
- data/kill.flag
  - KillSwitch が条件を満たすとここに理由を書き込みます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を参照してクリアするかどうかを決めます。
- .env
  - 環境変数設定ファイル（絶対にコミットしないでください）
- config/*.yaml
  - 各種設定ファイル（存在しない場合は警告、PyYAML があればパース検証を実施）

ディレクトリ構成
----------------
（主要なファイルを抜粋した構成）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数ロード / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングし ai_scores に書込
    - regime_detector.py     — マクロ+MA200 を合成してレジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマと DB アクセス層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 滞留注文・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション制限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （アラート送信の抽象化。実装はプロジェクト固有）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（リスク制限・丸め）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Value / Volatility ファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/... （上記参照）
  - execution/... （発注系モジュール群。OrderRepository, Engine 等へ依存）

注意点・トラブルシューティング
------------------------------
- OPENAI_API_KEY が未設定のまま ai 機能を呼ぶと例外になります。AI 機能を使う場合は必ず設定してください。
- PyYAML がインストールされていないと config/*.yaml のパースはスキップされます（validate_config は警告を出します）。
- run_monitoring は常に Settings.sqlite_path（本番 sqlite）を使用します。監視用 DB を切り替えたい場合は Settings の環境変数を変更してください。
- データファイル（data/）や親ディレクトリが存在しない場合、validate_config は警告を出しますが多くの起動スクリプトは起動時に必要なディレクトリを自動作成します。
- MONITOR_POLL_INTERVAL に 0 や負値を設定すると無効値として 60 秒にフォールバックします（ログに警告が出ます）。
- process_priority.set_process_priority は OS によって挙動が異なります（権限不足で失敗する場合はログに警告が出ます）。

開発／運用のワークフロー例
--------------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ（DuckDB / SQLite）を準備
4. ローカルでペーパートレード実行（KABUSYS_ENV=paper_trading）
   - python -m kabusys.run_execution
5. 監視を別プロセスで起動
   - python -m kabusys.run_monitoring
6. 定期的に paper_verification_report を実行して検証
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

最後に
-----
この README はリポジトリ内の主要モジュールと起動スクリプト群の挙動をまとめた概要です。実運用やデプロイ前には必ず python -m kabusys.validate_config による検証と、.env の機密情報管理（Git へのコミット禁止）を徹底してください。

必要であれば、この README をベースに「運用手順」「ログ監視手順」「デプロイ手順」「アラート設定の詳細」などの追加ドキュメントを作成します。どのセクションを詳細化したいか指示してください。