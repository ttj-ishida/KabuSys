# KabuSys

日本株向け自動売買システムのコアライブラリ／ランタイム群（README）。  
このドキュメントはリポジトリ内の主要モジュールに基づき、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な役割は以下のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 監視（MonitoringEngine）とアラート（LINE Push）
- ポートフォリオ構築（候補選定・配分・株数決定）
- ファクター計算 / 研究用ユーティリティ（DuckDB ベース）
- ニュース NLP によるセンチメント評価（OpenAI）
- 市場レジーム判定（MA + LLM の組合せ）
- 再起動時のリコンシリエーション（注文・ポジションの同期）

設計方針として、DB（SQLite / DuckDB）をローカルファイルで扱い、外部 API 呼び出しや実行時の挙動は環境変数で切替可能（開発 / paper_trading / live）。

---

## 主な機能一覧

- Execution
  - Signal を読み発注（OrderManager / ExecutionEngine）
  - 発注後の同期・再接続時のリコンシリエーション（Reconciler）
  - リスクゲート（Rate limit / Circuit breaker / ドローダウン制御）
  - paper_trading モード（MockBroker を利用し本番 DB と分離）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定異常の検出
  - ダッシュボード（Streamlit）表示
  - Kill switch（フラグファイルにより ExecutionEngine を停止）
  - LINE によるアラート通知（AlertManager）
- Portfolio
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクター上限適用、レジーム乗数
  - 株数（単元）決定・aggregate cap 計算
- Research / Data
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン / IC（情報係数）計算、特徴量サマリー
- AI
  - ニューステキストを集約し OpenAI GPT 系モデルで銘柄別センチメントを算出・保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定

---

## セットアップ手順（ローカル実行向け）

前提:
- Python 3.10+ を推奨（型注釈・構文互換のため）
- SQLite（stdlib）、DuckDB、外部ライブラリが必要

1. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートに移動

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   必要最小限（例）:
   - pip install duckdb psutil openai requests streamlit
   （プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須項目（使用する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用、必須の箇所あり）
     - KABU_API_PASSWORD（kabu API 用、必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - KABUSYS_ENV = development | paper_trading | live（default: development）
     - PAPER_FILL_MODE = instant | partial | never | reject（paper_trading 向け）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH 等

   例 (.env):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   PAPER_FILL_MODE=instant
   ```

5. データディレクトリの準備
   - data/ 配下に DB を配置（なければモジュールが初回に作成することも多い）
   - 例: mkdir -p data

---

## 使い方（実行例）

※ Python パッケージとしてインストールせずにソース直下から実行する想定（module run が可能なら `python -m kabusys.<module>` でも可）。

- 監視ループ起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト: 60）
  - 実行:
    - python src/kabusys/run_monitoring.py
    - または python -m kabusys.run_monitoring
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（Settings.sqlite_path）を使用します。
    - プロセス起動時に set_process_priority("high") を試みます（権限により失敗することがあります）。

- 発注エンジン起動（ExecutionEngine）
  - デフォルト: KABUSYS_ENV=development（変更する場合は環境変数を export）
  - Paper Trading（Mock Broker）で実行する例:
    - export KABUSYS_ENV=paper_trading
    - python src/kabusys/run_execution.py
  - Live 実行:
    - export KABUSYS_ENV=live
    - python src/kabusys/run_execution.py
  - 注意:
    - paper_trading の場合、専用 SQLite（Settings.paper_sqlite_path、デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
    - ExecutionEngine は起動時に PID ファイル（Settings.pid_file_path）や kill.flag を参照します。起動時に KILL_FLAG_CLEAR_ON_START を有効にすると古い flag をクリアできます。

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開き、ポジション / 注文 / システムステータス / リスクログを表示します。

- AI（ニューススコアリング / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を programmatically 呼び出し、DuckDB 接続と target_date を渡して実行します（OpenAI API キーが必要です）。

環境変数の主な切替
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant/partial/never/reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

Kill switch / PID
- KillSwitch は設定された flag_path（デフォルト data/kill.flag）に理由を書き込むことで ExecutionEngine 停止を誘発します。
- ExecutionEngine は起動時に pid_file_path を利用して稼働中プロセスの存在を確認します（SystemMonitor も同様に stale PID を検出して削除）。

ログ/優先度
- 起動時に set_process_priority("high") を試行します（プラットフォーム差異は kabusys.utils.process_priority が吸収）。
- logging.basicConfig(level=logging.INFO) が基本。LOG_LEVEL 環境変数で設定可能（Settings.log_level）。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリ内の `src/kabusys` を基準に抜粋：

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス。.env 自動ロードロジック、必須チェックあり。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV により paper_trading 判定。
  - utils/
    - process_priority.py — プラットフォーム差分を吸収するプロセス優先度・CPU affinity ユーティリティ。
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化・永続化アクセス層（MonitoringDB）。
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視。
    - trade_monitor.py — 注文滞留・約定異常検出。
    - risk_monitor.py — ドローダウン・ポジション上限監視。
    - kill_switch.py — kill.flag 操作・評価。
    - alert_manager.py — LINE push でアラート送信。
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン（テスト run_once / run）。
    - streamlit_dashboard.py — Streamlit ベースの監視 UI（read-only）。
  - execution/
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン等の本体）。
    - order_manager.py — 発注用 API（state machine の外側インターフェース）。
    - reconciler.py — 起動時の注文・ポジション再同期（自動復旧）。
    - order_repository.py, order_record.py, broker_factory.py, broker_api.py など（発注周り DB/API 抽象）。
    - risk_manager.py — 実行時ゲート（Gate1..3）・レート制限・サーキットブレーカ等。
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート。
    - position_sizing.py — 株数（単元）決定、aggregate cap スケーリング。
    - risk_adjustment.py — セクター上限・レジーム乗数。
  - research/
    - factor_research.py — Momentum/Volatility/Value 等の DuckDB ベースのファクター計算。
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等。
  - ai/
    - news_nlp.py — raw_news を OpenAI に送って銘柄別センチメント算出・ai_scores に保存。
    - regime_detector.py — ETF(1321) MA200 とマクロニュースの LLM センチメントを合成して市場レジームを判定。
  - data/ (既定のデータ格納先 / DB ファイル)
    - kabusys.duckdb (DUCKDB_PATH デフォルト: data/kabusys.duckdb)
    - monitoring.db (SQLITE_PATH デフォルト: data/monitoring.db)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db)

---

## 補足・運用上の注意

- DB マイグレーション: init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（例: dashboard.peak_value の追加）を行います。
- paper_trading モードは本番 DB と分離するため、テストや検証に安全です（ただし実装上の差異を理解の上で利用してください）。
- OpenAI 利用時は API のレート制限やエラーを考慮し、内部で指数バックオフ処理が実装されています。またレスポンスは JSON モードを想定していますが、パース失敗時にフェイルセーフな挙動（スコア 0.0 など）があります。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine が DB を維持していることを確認してください。
- 自動で .env をロードしますが、CI／テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御することを推奨します。

---

必要があれば「開発者向けセットアップ（テストラン・デバッグの方法）」「主要なクラスの API ドキュメント」「.env.example の完全なサンプル」を追記します。どの情報が欲しいか教えてください。