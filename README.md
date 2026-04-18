KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリは以下の主要機能を含みます。

- 発注・ExecutionEngine（実発注 / ペーパートレード対応）
- 監視（System / Trade / Risk のポーリングと Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特性探索）
- AI 統合（ニュースセンチメント、マーケットレジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主要な設計方針
- 本番/ペーパートレードのデータ分離（paper_trading 用 DB が独立）
- DB（SQLite / DuckDB）への冪等的な初期化、実行スクリプトから自動作成
- AI 呼び出しは OpenAI API を利用（失敗時はフェイルセーフ）
- ロギングは統一インターフェース（コンソール + 日次ローテートファイル）
- ルックアヘッドバイアスを避ける設計（日時の参照に注意）

機能一覧
---------
- 実行系
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - Broker クライアント分離（本番 / Mock）
  - リスク管理（最大ポジション割合・利用率・ドローンダウン等）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine によるポーリング・アラート送出
  - Kill Switch（条件で data/kill.flag を書き込む）
  - 監視用 DB（SQLite）へのログ永続化
- ポートフォリオ
  - 候補選定、等金額・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリー
  - DuckDB を使った高速集計
- AI
  - ニュースセンチメント（news_nlp.score_news）
  - レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 等）をバッチ的に呼び出し、結果を DuckDB に書き込み
- ツール / CLI
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要パッケージ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml の構文チェックを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを使ってください。

4. 環境変数の準備
   - プロジェクトルートに .env を作成するか、環境変数を直接設定します。
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨・例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. 初回 DB（監視用）初期化
   - 実行スクリプト起動時に自動でテーブルが作られます（init_monitoring_db を使用）。

使い方
-------
共通の注意:
- ログ設定: kabusys.utils.logging_setup.setup_logging を各スクリプトで呼んでいます。ログは stdout と logs/<app_name>.log に出力されます。ログディレクトリは LOG_DIR 環境変数で変更可能（デフォルト: logs）。

起動スクリプト（代表例）
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し data/paper_trading.db を使います。
  - 停止は data/stop_requested.flag の作成で制御（または kill.flag による停止判定）。
  - 実行時に data/execution.pid を生成します。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能。
  - 監視は本番 sqlite_path（KABUSYS_ENV に関係なく sqlite_path）を使用します。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーを必要とします（引数または OPENAI_API_KEY 環境変数）。
- AI 呼び出しはレート制限や一時エラーに対して指数バックオフでリトライしますが、APIキー未設定の場合は例外になります。

監視・Kill Switch
- KillSwitch は RiskMonitor / SystemMonitor / TradeMonitor の判定に基づき data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ディレクトリ構成（抜粋）
------------------------
以下は主要ファイル・パッケージの概観（src/kabusys 配下）。実際にはさらにサブモジュールがあります。

- src/kabusys/
  - __init__.py               — パッケージ初期化（__version__）
  - config.py                 — 環境変数 / Settings クラス（.env 自動ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン等の監視ロジック
    - kill_switch.py          — kill.flag 書込みロジック
    - monitoring_engine.py    — 各モニタの束ね
    - (trade_monitor, alert_manager 等は同階層に存在する想定)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・スケーリング（lot 単位）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

サンプル .env（最小例）
----------------------
以下は .env の最低限の例（実運用では秘密情報は必ず安全に管理してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

運用上の注意
-------------
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config.py は live 時に複数の警告を出します）。
- kill.flag / stop_requested.flag / data/execution.pid などのフラグ管理に注意してください。特に KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- OpenAI API を使うモジュールはトークンの漏洩・課金に注意してください。テストではキーを設定せずに API 呼び出しをモックすることを推奨します。
- DuckDB / SQLite のファイルはデータサイズが増加する可能性があるためバックアップやディスク運用に注意してください。

貢献・拡張
-----------
- strategy / execution の詳細実装（ブローカー実装、ExecutionEngine の振る舞い）は拡張ポイントです。
- テストの充実（ユニット・統合）を推奨します。AI 呼び出しはモック化してテスト実行してください。
- 将来的な改善例:
  - 銘柄ごとの lot_size をマスタに持たせる
  - ポートフォリオ構築における取引コストのより精密な扱い
  - モニタリングのメトリクス可視化（Grafana 連携など）

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = 0.1.0
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

問い合わせ
---------
不明点や実行時エラーが発生した場合は、ログ（logs/ 配下）を確認してください。設定関連はまず python -m kabusys.validate_config を実行して問題を検出してください。

--- 
以上が本リポジトリの主要な README 内容です。README に追記したい具体的なコマンド例や、requirements.txt の内容があれば提供してください。