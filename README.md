# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的とした小規模なシステム群です。  
主要機能は次のとおりです。

- 発注エンジン（ExecutionEngine）とブローカー抽象化（実運用／ペーパートレード対応）
- 監視コンポーネント（システム稼働・注文ログ・リスク監視）
- ポートフォリオ構築（候補選定、重み算出、ポジション決定）
- リサーチ用ファクター計算（Momentum, Volatility, Value 等）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の要点：
- DB は DuckDB（分析用）と SQLite（監視・発注履歴用）を併用
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しはフェイルセーフ（API失敗時はスコア補正等で継続）

---

## 機能一覧

主要コンポーネントと機能：

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（実売買 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定関連
  - config_setup.py: .env を対話的に生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性検証（--strict オプションあり）
- 監視
  - monitoring_engine: System / Trade / Risk モニタの統合
  - monitoring_db: SQLite に保存する永続層（テーブル作成・マイグレーション含む）
  - kill_switch: ドローダウン等で ExecutionEngine に停止シグナルを送信
- 発注・リスク
  - ExecutionEngine、OrderManager、RiskManager（起動スクリプトから組み立て）
  - BrokerClientFactory：実ブローカー or MockBroker（paper_trading）を生成
- ポートフォリオ
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み付け・株数決定）
- リサーチ
  - research.factor_research: momentum/volatility/value の算出（DuckDB 経由）
  - research.feature_exploration: forward returns, IC, summary 等
- AI
  - ai.news_nlp: ニュースから銘柄毎のセンチメントを生成（OpenAI）
  - ai.regime_detector: ma200 + マクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポート出力

---

## 前提・依存

推奨 Python バージョン: 3.10 以降（型アノテーションの構文に依存）

主な依存パッケージ（インストールしてください）:
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合に必要）

例（pip）:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートに合わせる。

2. 依存パッケージをインストール:
   - pip install -r requirements.txt
   - もしくは個別に: pip install duckdb psutil openai PyYAML

3. 環境変数の準備:
   - 対話式で .env を生成する（推奨）:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成してプロジェクトルートに置く。
   - 自動ロード: config.Settings モジュールはプロジェクトルートに .env/.env.local があると自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用データベースのパス）

5. ログディレクトリ:
   - デフォルトは logs/。必要に応じて LOG_DIR 環境変数で変更。

注意:
- ペーパートレードモード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、発注ログは PAPER_TRADING_SQLITE_PATH に記録されるため本番データと分離されます。
- run_monitoring は常に本番用の sqlite_path を使用します（監視は本番 DB を参照）。

---

## 使い方（主要コマンド）

すべてプロジェクトルートから実行します。

- .env ウィザード（対話式）
  python -m kabusys.config_setup

- 設定検証（起動前のチェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  python -m kabusys.run_execution
  - 実行時、Settings に従って paper_trading モードなら MockBroker を使います。
  - 停止は data/stop_requested.flag を作成すると検知してシャットダウンします。
  - 実行中は data/execution.pid（デフォルト）に PID を出力します。

- Monitoring 起動（ポーリング）
  python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（秒）。
    例: export MONITOR_POLL_INTERVAL=30
  - 監視ループも data/stop_requested.flag を検知して終了します。

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア生成（ライブラリ API）
  - ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト
    - api_key: None の場合は環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- ログは logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。
- 起動スクリプトは起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合あり）。

停止・強制停止:
- ExecutionEngine を安全に止めるには、監視側（KillSwitch 等）やオペレータが data/kill.flag を書く設計になっています（KillSwitch は自動で flag を書くことがあります）。
- run_* スクリプトの強制終了は Ctrl+C（KeyboardInterrupt）で可能。

---

## 代表的な環境変数（一部）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1。production では 0 を推奨）

サンプル .env（抜粋）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

---

## ディレクトリ構成

主要なディレクトリ / ファイル（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 定義（自動 .env ロード含む）
  - config_setup.py                — .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py             — SQLite 永続層（テーブル作成・CRUD ラッパ）
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文滞留 / 約定異常監視（実装参照）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の管理
    - monitoring_engine.py         — 各モニタを束ねるエンジン
    - alert_manager.py             — LINE 等への通知（実装参照）
  - execution/
    - execution_engine.py          — 発注エンジン（EngineConfig 等）
    - broker_factory.py            — BrokerClientFactory（Mock/実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI 連携）
    - regime_detector.py            — 市場レジーム判定（LLM + ma200）
  - data/ (生成される DB やフラグファイル)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kill.flag / stop_requested.flag / execution.pid
  - tools/
    - paper_verification_report.py

（上記はコードベースの代表的な場所。細かいファイルはリポジトリ参照）

---

## 注意点・トラブルシューティング

- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- run_monitoring は MONITOR_POLL_INTERVAL が 0 や負の値の場合デフォルト 60 秒へフォールバックします。
- psutil によるプロセス優先度/affinity 設定は権限不足で失敗することがあります（警告を出してスキップ）。
- OpenAI 関連は API 利用制限やタイムアウトが発生するため、リトライ・フォールバック実装あり。API キー未設定時はエラー／例外になる関数があります（呼び出し前に OPENAI_API_KEY を設定してください）。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出します。実行時に自動生成されることが多いですが、権限やパス確認をしてください。
- Kill Switch / stop flag: data/kill.flag や data/stop_requested.flag による制御を行います。手動で停止させた場合は不要な残ファイルを削除してください。

---

## 開発・拡張メモ

- research モジュールは DuckDB 接続を受け取り SQL を駆使してファクターを算出する設計です。分析実行は DuckDB を通じて行ってください。
- portfolio/position_sizing は lot_size（単元）や cost_buffer を引数で与えられる柔軟設計。将来的な銘柄別単元対応が可能です。
- AI 周りは JSON モードを期待して厳密にパースしていますが、LLM の出力変化に対して堅牢性を持たせるための後処理が含まれます（部分失敗時は既存スコアを消さない書き込み戦略など）。

---

README は以上です。不明点や README に追加したい項目（例: サンプル .env 全項目、起動時のログ例、より詳しいディレクトリツリー等）があれば指示ください。