# KabuSys

日本株向け自動売買システムの一部を抜粋したコードベースです。ポートフォリオ構築、発注管理、監視、Paper Trading の検証・レポート、ニュース NLP / レジーム判定などの機能を含みます。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成されています。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine（ブローカー連携による発注、リスク管理、リコンサイル）
- 監視（System / Trade / Risk）とアラート（LINE）
- Paper Trading 用の検証レポート生成ツール
- ニュースを LLM で解析して銘柄別スコアを生成する AI モジュール
- Streamlit による監視ダッシュボード

設計方針は「副作用を最小化した純粋関数」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時の安全フォールバック）」などです。

---

## 主な機能一覧

- portfolio
  - 銘柄候補の選定（score / rank に基づくソート）
  - 重み付け（等分配・スコア加重）
  - 単元・最大ポジション考慮した株数決定（risk_based / equal / score）
  - セクター集中制限の適用、レジーム乗数
- research
  - モメンタム / ボラティリティ / バリュー等ファクターの DuckDB ベース計算
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- execution
  - OrderManager、Reconciler による発注フロー管理とクラッシュ復旧処理
  - Broker クライアント抽象化（本番 / Paper 用の切替）
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor：滞留注文や約定価格異常の検出
  - RiskMonitor：ドローダウン／ポジション上限の監視と alert 発行
  - KillSwitch：致命的条件で ExecutionEngine を停止させるフラグ書き込み
  - AlertManager：LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り）
- ai
  - news_nlp: raw_news をまとめて LLM に投げ、銘柄毎の ai_score を生成・書き込み
  - regime_detector: ETF（1321）MA200 とマクロ記事の LLM センチメントを合成し市場レジーム判定

---

## セットアップ手順

1. Python（3.9+ 推奨）を用意してください。

2. 必要パッケージをインストール（プロジェクトに requirements.txt は含まれていませんが、主な依存は以下です）:

   pip install duckdb psutil openai requests streamlit

   （環境によっては追加で型ライブラリ等を導入してください。）

3. プロジェクトルートに .env または .env.local を配置可能。自動読み込みはデフォルトで有効（起動時に .env → .env.local の順で読み込み、OS 環境変数は保護されます）。自動読み込みを無効化する場合:

   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ（デフォルト）:

   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db

   必要に応じて環境変数で上書きできます（例は下記参照）。

5. 必須環境変数（利用機能に応じて設定してください）:

   - JQUANTS_REFRESH_TOKEN — J-Quants API（research 用）
   - KABU_API_PASSWORD — kabuステーション API（実取引連携）
   - OPENAI_API_KEY — OpenAI（news_nlp / regime_detector）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動モード（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBroker を使用し Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込む。
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定挙動（instant | partial | never | reject）（デフォルト: instant）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。run_monitoring で利用（デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視周りの設定
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

注意: Settings クラスは起動時に値検証を行います。無効な値や未設定の必須項目は例外を投げます。

---

## 使い方

以下は代表的な実行例です。

1. 監視ループの起動（SystemMonitor を単独で実行するスクリプト）:

   python -m kabusys.run_monitoring

   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
   - 起動直後にプロセス優先度を "high" にセットします。
   - 停止: プロジェクトルート/data/stop_requested.flag を配置するとループは終了します。

2. ExecutionEngine の起動（発注エンジン）:

   python -m kabusys.run_execution

   - KABUSYS_ENV=paper_trading を設定すると、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
   - 起動時に execution.pid が data/ に書かれます。停止は data/stop_requested.flag を作成するか、エンジン内部の kill.flag によって行われます。

3. Paper Trading 検証レポート（コマンドラインツール）:

   python -m kabusys.tools.paper_verification_report \
       --from 2026-04-01 --to 2026-04-11 \
       --db data/paper_trading.db

   - 引数 --from / --to は YYYY-MM-DD 形式。--db が優先、なければ環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db。

4. Streamlit ダッシュボード（監視用、read-only 推奨）:

   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - 読み取り専用で DB を開くため、MonitoringEngine が動作中であることが望ましいです。

5. AI 関連（ニューススコア / レジーム判定）:

   - news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY 必須
   - regime_detector.score_regime(conn, target_date, api_key=None) — OPENAI_API_KEY 必須

   これらは DuckDB 接続を受け取り、対象日を引数で渡す設計です（datetime.today() を参照しない）。

---

## 停止・Kill フロー

- run_monitoring.py と run_execution.py はプロジェクトルート/data/stop_requested.flag を監視して安全に終了します。
- KillSwitch はリスク条件（ドローダウン超過、ポジション上限等）を満たした場合に data/kill.flag に理由を書き込みます。ExecutionEngine は kill.flag を検出して停止します。
- KillSwitch は冪等（既に存在する場合は書き直しません）。ExecutionEngine 起動時に kill.flag を消去するオプション設定があります（Settings.kill_flag_clear_on_start）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールとファイル構成の要約です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定読み込み、Settings 定義
  - run_monitoring.py                 — SystemMonitor の起動スクリプト
  - run_execution.py                  — ExecutionEngine の起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数算出・スケーリング
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 将来リターン・IC・統計
  - ai/
    - news_nlp.py                     — ニュース NLP（OpenAI 連携）
    - regime_detector.py              — レジーム判定（ma200 + macro LLM）
  - monitoring/
    - monitoring_db.py                — SQLite スキーマ & 永続化ラッパ
    - system_monitor.py               — システム / データ鮮度監視
    - trade_monitor.py                — 注文滞留 / 約定異常監視
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - kill_switch.py                  — kill.flag の作成 / 管理
    - alert_manager.py                — LINE 通知
    - monitoring_engine.py            — 各 Monitor の統合ポーリング
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py                — 発注 API 周りのステートマシン
    - reconciler.py                   — 再起動時の照合・復旧
    - (その他 broker_factory 等 — 抜粋された実装が存在)
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - data/                              — 実行時に生成される（DB、pid、flag 等）

---

## 注意事項 / 運用メモ

- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB とは分離され、data/paper_trading.db にのみ書き込みます。テスト・検証では必ずこのモードを使用してください。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライとフェイルセーフを備えていますが、レート制限等の影響を受けます。
- Monitoring 用 SQLite は run_monitoring や ExecutionEngine のログ／ダッシュボードに使用されます。init_monitoring_db によりテーブル・マイグレーションが実行されます。
- process priority の設定は psutil に依存します。権限不足や未対応 OS ではスキップされますがログで通知されます。
- Settings に定義されたプロパティは起動時にバリデーションを行います。不正な値は ValueError を投げるため .env を整備してください。

---

以上が README の概要です。運用や導入について具体的な .env.example、requirements.txt、起動ユニット（systemd など）のテンプレートが必要であれば、利用環境に合わせて追加で作成します。必要であればサンプル .env.example を作成しますか？