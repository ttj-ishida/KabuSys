# KabuSys

軽量な日本株自動売買システムのコードベース（ドキュメント版）。このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニューススコアリングなどを含むモジュール群で構成されています。

以下はこのコードベースの概要、機能、セットアップ手順、主要な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した小規模なシステムです。主な機能群は以下のとおりです。

- Execution Engine：ブローカークライアントを介した発注・注文状態管理・リコンシリエーション
- Monitoring：システム状態・注文滞留・リスク（ドローダウン、ポジション上限）を継続監視し、ログ保存・アラート・Kill Switch を提供
- Portfolio Construction：シグナルに基づく候補選定、重み付け、ポジションサイズ決定、セクター制約など
- Research：DuckDB を使ったファクター計算、将来リターン、IC 計算などの統計実験
- AI モジュール：OpenAI を用いたニュースのセンチメントスコアリング（ai.news_nlp）、市場レジーム判定（ai.regime_detector）
- ツール：Paper Trading の検証レポート生成スクリプトなど
- ユーティリティ：プロセス優先度や CPU affinity の設定など

設計のポイント：
- DuckDB / SQLite をデータ層として使用（ローカル DB ファイル）
- モジュールはテストしやすい純粋関数／小さなクラス単位で実装
- 環境変数と .env ファイルによる設定管理（自動読み込み）
- Paper Trading（モックブローカー）を本番 DB と分離可能

---

## 機能一覧（主なもの）

- 起動スクリプト
  - run_monitoring.py：SystemMonitor のポーリングループ
  - run_execution.py：ExecutionEngine の起動（KABUSYS_ENV により paper_trading モードあり）
- 監視
  - SystemMonitor：CPU・メモリ・ディスク・実行プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定価格の異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringDB：SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch：リスク条件で `data/kill.flag` を書き込み Execution を停止させる仕組み
  - AlertManager：LINE Messaging API 経由の通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用）
- Execution（発注）
  - OrderManager / OrderRepository / Reconciler：注文作成、同期、再起動時のリコンシリエーション
  - BrokerFactory：環境に応じたブローカークライアント生成（paper_trading モードで MockBroker）
- Portfolio
  - 候補選定・重み付け（等金額・スコア加重）/ セクター上限適用 / ポジションサイズ計算（ロット丸め・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン / IC / 統計サマリー
- AI
  - news_nlp.score_news：ニュース記事を OpenAI に送って銘柄別スコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを併合して市場レジーム判定を market_regime テーブルへ書き込み
- ツール
  - tools/paper_verification_report.py：Paper Trading DB を解析して検証レポートを標準出力に出す

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（typing の | 記法等を使用）
- Git

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt が無い場合は主な依存を個別に）
   - pip install duckdb psutil requests openai streamlit

   追加の依存は環境や利用機能により必要になることがあります（例: sqlite3 は標準ライブラリ）。

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既存の OS 環境変数は上書きされません）。
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   最低限設定が推奨される変数（用途に応じて）：
   - JQUANTS_REFRESH_TOKEN（J-Quants API） — 必須プロパティ参照箇所あり
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト instant）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager を使うとき）

   例 .env（最小）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリ
   - デフォルトではデータは data/ 以下に作られます（DB、PID/flag ファイルなど）。
   - 必要に応じて手動で data/ を作成してください（実行時に自動作成される場合もあります）。

---

## 使い方（主要な起動・操作）

1. 監視ループ（SystemMonitor）を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。無効な値は 60 秒にフォールバックします。
   - このスクリプトはプロセス優先度を "high" に設定し、SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）へ接続して監視ログを記録します。
   - 停止は Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成することでループが終了します。

2. ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient（実取引を行わない）を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 起動前に data/kill.flag が存在する場合は起動を中止します。
   - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します。
   - 実行中は data/execution.pid に PID が書かれます（PID ファイルの stale 判定、監視が実装されています）。

3. Streamlit ダッシュボード（監視用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視データを読み取り、Overview / Positions / Orders / System を表示します。監視プロセス実行中にデータを参照する想定です。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。
   - デフォルト DB は data/paper_trading.db

5. AI 機能（ニューススコア・レジーム判定）
   - ai.news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY を環境変数または api_key で渡してください。
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 両者は OpenAI API（gpt-4o-mini 等）を呼び出します。API キー未設定時は例外やフェイルセーフ動作（score_regime は macro_sentiment=0.0）になります。

6. 停止・Kill フラグ
   - Monitoring 側の KillSwitch は条件が揃うと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を記したファイルを書き込みます。ExecutionEngine はこれを検出して安全に停止する設計です。
   - 明示的に Execution を停止したい場合は data/kill.flag を作成するか data/stop_requested.flag を作成してください。run_monitoring/run_execution は stop_requested.flag を監視します。

---

## 主要な設定項目（抜粋）

- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - paper_trading モードは MockBroker を使用し、本番 DB と分離します。
- MONITOR_POLL_INTERVAL: 監視ループの秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の mock 約定挙動
  - instant / partial / never / reject
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能実行に必須）

Settings クラス（kabusys.config.Settings）により環境変数のバリデーションとアクセスが提供されています。不正な値は例外を投げます。

---

## ディレクトリ構成（主要ファイルの説明）

（ルートは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 自動読み込み / Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py — ETF MA と LLM による市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続層（init_monitoring_db, MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定価格異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書き込み・管理
    - alert_manager.py — LINE Push 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once と本番 run）
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - execution_engine.py — 実際のエンジン（起動/セッション管理）※詳細実装ファイルは存在
    - broker_factory.py — ブローカー（実/モック）生成
    - broker_api.py — ブローカー API 抽象
    - order_manager.py — Order 管理 API（作成／同期／キャンセル等）
    - order_repository.py — SQLite ベースの Order 永続化
    - reconciler.py — 再起動時のリコンシリエーション
    - order_record.py — OrderRecord, OrderState などのモデル

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出（ロット丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py

  - data/  (実行時に使用 / 生成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid / stop_requested.flag / kill.flag

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

---

## 実運用上の注意点

- DB の migration：monitoring_db.init_monitoring_db は必要テーブルといくつかのカラム追加（マイグレーション）を行いますが、複雑なスキーマ変更は別途管理してください。
- OpenAI API：大量呼び出しやレート制限に注意。news_nlp と regime_detector はリトライ・バックオフロジックを備えていますが、API キー・コスト管理は利用者責任です。
- Paper Trading：paper_trading モードは本番 DB とは分離するよう設計されています。KABUSYS_ENV=paper_trading を忘れると本番 DB に書き込む可能性がありますので注意してください。
- Kill Switch：KillSwitch が kill.flag を書き込むと ExecutionEngine による発注が停止します。kill.flag の操作は慎重に行ってください。
- 権限：プロセス優先度の変更や CPU affinity 設定は権限不足で失敗する場合があり、その場合はワーニングになります（動作に致命的影響はない想定）。

---

## 連絡先・貢献

この README はコードベースの主要な機能と使い方をまとめたものです。実装の詳細や追加機能の提案・バグ修正は Pull Request を送ってください。ドキュメントやテストの追加も歓迎します。

---

README は以上です。必要であれば、サンプル .env.example の雛形や requirements.txt を作成するお手伝いもできます。どの形式がよいか教えてください。