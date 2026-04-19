KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主な機能は以下の通りです：戦略のためのリサーチ / ファクター計算、ポートフォリオ構築、ポジションサイジング、実際の発注を行う ExecutionEngine（本番／ペーパートレード切替対応）、およびシステム監視・アラート機能を備えています。  
コードはモジュール化されており、CLI ツール（環境設定ウィザード・設定検証・検証レポート等）や OpenAI を使った NLP モジュールも含まれます。

主な特徴
--------
- ExecutionEngine（本番 / paper_trading 切替）
  - KABUSYS_ENV により development / paper_trading / live を選択可能
  - paper_trading 時は MockBrokerClient を使用しデータを data/paper_trading.db に分離
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全停止（Kill Switch）と stop_requested.flag による外部停止指示
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重配分、セクターキャップ、レジーム乗数
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
- リサーチ（research）
  - DuckDB 上で動くファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、統計サマリ
- AI モジュール（ai）
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントを score → DuckDB に保存
  - 市場レジーム判定（ETF MA + マクロ記事センチメントの合成）
- ユーティリティ
  - ログ設定、プロセス優先度／CPU affinity 設定ユーティリティ
  - .env 作成ウィザード、設定検証 CLI、ペーパートレード検証レポート生成ツール

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <project_root>

2. Python 環境（推奨: venv）作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合はそれを使用してください。なければ最低限次を入れてください:
     - duckdb, psutil, openai, pyyaml (設定検証の YAML チェック用)
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定（ai モジュールで必要）
   - 必要に応じて DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV 等を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う

6. データディレクトリの作成（.env のパスに合わせる）
   - デフォルト: data/ と logs/ は自動作成されますが、パーミッション等に注意してください。

使い方
------
起動スクリプト
- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し MockBrokerClient を利用
    - KABUSYS_ENV=live のときは本番 sqlite_path を使用（本番 DB への書き込みに注意）
    - 起動時に stop_requested.flag が存在すると起動せず終了
    - 起動中は data/execution.pid に PID を書きます

- Monitoring（システム監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor をポーリング（間隔デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可
    - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず本番 DB を監視）
    - stop_requested.flag を検知するとループを終了

ログ
- setup_logging により stdout と 日次ローテートファイル（logs/<app_name>.log）に出力
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御

監視・安全停止
- Kill Switch:
  - RiskMonitor が DRAWDOWN / POSITION_LIMIT を検出すると data/kill.flag に理由を書き込みます
  - ExecutionEngine は kill.flag の存在により安全に停止できます
- 外部強制停止:
  - data/stop_requested.flag を作成すると run_* スクリプトが次のポーリングで安全停止します

AI / OpenAI
- ai.news_nlp と ai.regime_detector は OpenAI API を呼び出します
- 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください
- API 呼び出しはリトライやフォールバック処理を含み、失敗時はフェイルセーフ（スキップや中立スコア）になります

便利な CLI / ツール
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db 、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI モジュールで必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env の自動ロードと Settings
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI）と ai_scores 書き込み
  - regime_detector.py            — 市場レジーム判定（ETF MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py              — SQLite テーブル初期化・CRUD ラッパー
  - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py              — （トレード監視ロジック）
  - risk_monitor.py               — ドローダウン・ポジション数監視
  - kill_switch.py                — kill.flag 管理
  - monitoring_engine.py          — 各 Monitor を束ねる
  - alert_manager.py              — （アラート送信管理）
- execution/
  - execution_engine.py           — ExecutionEngine（セッション実行）
  - order_manager.py              — 注文管理
  - order_repository.py           — 注文永続化レイヤ
  - reconciler.py                 — ブローカー照合ロジック
  - broker_factory.py             — Broker クライアント生成（Mock/実ブローカー切替）
  - risk_manager.py               — リスク管理（rate limit 等）
- portfolio/
  - portfolio_builder.py          — 候補選定 / 重み付け
  - position_sizing.py            — 株数決定 / aggregate cap
  - risk_adjustment.py            — セクターキャップ / レジーム乗数
- research/
  - factor_research.py            — モメンタム/バリュー/ボラティリティ計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート出力
- utils/
  - logging_setup.py              — ログ設定ユーティリティ
  - process_priority.py           — プロセス優先度 / CPU affinity
  - その他ユーティリティ

注意事項 / 運用上の留意点
------------------------
- 本番運用（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START 設定等に注意してください。
  validate_config は本番向けのガードを出力します。
- paper_trading モードは本番 DB と完全に分離するよう設計されていますが、.env のパス設定を必ず確認してください。
- OpenAI キーや API 使用はコストが発生します。ai モジュールは外部 API 依存があるため運用ポリシーを設けてください。
- ログディレクトリ・DB ファイルのディスク容量に注意（DuckDB / ログの蓄積）。

開発者向け補足
--------------
- モジュール間は明確に分離されています（例: ai モジュールの呼び出しは明示的）。
- DuckDB 接続を受け取る設計でリサーチ機能は副作用を持ちません（テストが容易）。
- 監視 DB のスキーマは monitoring_db.init_monitoring_db で冪等に初期化されます。  

その他
-----
ご不明点や追加の使い方（例: ExecutionEngine の詳細な設定、ブローカープラグイン実装方法など）があればお知らせください。README を運用ポリシーやデプロイ手順に合わせて拡張できます。