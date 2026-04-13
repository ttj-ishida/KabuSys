# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼実行スクリプト群）。

このリポジトリは「戦略の研究・ファクター計算」「ポートフォリオ構築」「発注ロジックと実行」「監視・アラート」「AI を使ったニュースセンチメント・レジーム判定」などを目的とした複数コンポーネントで構成されています。各コンポーネントは可能な限り副作用を抑え、テストや再利用を容易にする設計方針が取られています。

主な実装言語: Python 3.9+

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・ツール）
- 環境変数一覧（重要）
- ディレクトリ構成（主要ファイル説明）
- 補足・注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのためのライブラリ兼運用スクリプト群です。主な責務は次のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・研究
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（Paper Trading 対応）
- 実行系の監視（System / Trade / Risk モニタ）、アラート（LINE）送信
- ニュースの NLP によるセンチメントスコア化（OpenAI）
- レジーム検出（MA + マクロセンチメント合成）
- 運用検証ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

---

## 主な機能一覧

- research
  - ファクター計算（モメンタム、ボラティリティ、バリューなど） — duckdb を用いた純粋関数群
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- portfolio
  - 候補選定（スコア順）
  - 等重・スコア加重配分
  - リスク調整（セクター上限適用、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap）
- execution
  - OrderManager、Reconciler、ExecutionEngine（起動スクリプトあり）
  - ブローカークライアント抽象化（paper_trading 用の Mock 対応）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor、MonitoringDB（SQLite）
  - KillSwitch（flag ファイルにより ExecutionEngine を停止指示）
  - AlertManager（LINE push 送信、クールダウン管理）
  - MonitoringEngine（ポーリング統合）
  - Streamlit ダッシュボード表示用スクリプト
- ai
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: MA200 とマクロセンチメントを合成して市場レジーム判定・保存
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

1. Python（推奨: 3.9+）を用意します。仮想環境を推奨します:

   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows では `.venv\Scripts\activate`
   ```

2. 必要パッケージをインストールします（リポジトリに requirements.txt が無い場合の例）:

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   - duckdb: 時系列データ集計・クエリ
   - psutil: システム情報（CPU / メモリ / PID チェック）
   - requests: LINE API 送信
   - openai: OpenAI API 呼び出し
   - streamlit: 監視ダッシュボード用

3. データディレクトリを作成（デフォルトの DB パス等を用いる場合）:

   ```
   mkdir -p data
   ```

4. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くと自動読み込みされます（既存の OS 環境変数を保護）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方

以下は代表的な起動方法・ツールの使い方です。

1. ExecutionEngine（実行エンジン）起動

   - 本番 / 開発 / Paper Trading を切り替えるには環境変数 KABUSYS_ENV を設定します。
     - live / development / paper_trading
     - paper_trading の場合、専用の SQLite（data/paper_trading.db）と MockBrokerClient が使われます。

   実行:

   ```
   # モジュールとして実行
   python -m kabusys.run_execution
   ```

   重要な挙動:
   - 起動直後にプロセス優先度を "high" に設定しようとします（psutil 権限に依存）。
   - paper_trading は本番 DB と完全分離されるようデフォルトで data/paper_trading.db を使用。

2. Monitoring（監視ループ）起動

   ```
   python -m kabusys.run_monitoring
   ```

   - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
     - MONITOR_POLL_INTERVAL=30

   - 監視は MonitoringDB（SQLite）へログを書き、System/Trade/Risk モニタを定期実行します。
   - KillSwitch（data/kill.flag）や PID ファイル（data/execution.pid）を使った停止・状態検出が動作します。

3. Streamlit ダッシュボード（監視）起動

   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

   - 監視用 SQLite を読み取り専用で開き、ポートフォリオ / ポジション / 注文 / システム状態を表示します。

4. Paper Trading 検証レポート生成

   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # デフォルト DB: data/paper_trading.db。--db で別パス指定可
   ```

   出力: 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等をまとめたテキストレポート。

5. AI 関連（ニューススコアリング・レジーム判定）

   - ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date を与えると raw_news から銘柄別センチメントを ai_scores テーブルへ書き込みます。
     - OPENAI_API_KEY が必要（api_key 引数で上書き可）。

   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime テーブルへ書き込みます。

   これらはライブラリ関数（DuckDB 接続を渡して呼ぶ）で、CLI は用意されていません。テスト用スクリプトや cron で呼び出してください。

---

## 環境変数（主なもの）

Settings クラスを通じて読み込まれる重要変数（デフォルト値や説明を含む）:

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI API キー（ai機能で必要）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant/partial/never/reject）
- KABUSYS_ENV — 起動環境（development / paper_trading / live）デフォルト: development
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で true）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を見つけて .env/.env.local を読み込みます。
- OS 環境変数 > .env.local（上書き）> .env（未設定時にセット）という優先度。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 配下の主要モジュール（抜粋）です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）

- src/kabusys/config.py
  - Settings クラス: 環境変数の読み込み・検証・デフォルト管理
  - .env 自動読み込みロジック

- src/kabusys/run_execution.py
  - ExecutionEngine を起動するエントリポイント（KABUSYS_ENV による分岐）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト
  - MONITOR_POLL_INTERVAL による間隔設定

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と MonitoringDB クラス（ログ永続化）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag の書き込み / クリア
  - alert_manager.py: LINE 送信ユーティリティ
  - monitoring_engine.py: 3つのモニタをまとめて定期実行するエンジン
  - streamlit_dashboard.py: Streamlit ベースのダッシュボード

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py（主要な発注・復旧ロジック）
  - broker_factory / broker_api: ブローカー抽象

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算（単元丸め等）
  - risk_adjustment.py: セクター制限・レジーム乗数

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py: raw_news → OpenAI で銘柄別センチメント取得・ai_scores 書き込み
  - regime_detector.py: MA200 とマクロセンチメント合成で市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 補足・注意事項

- DB のマイグレーション
  - init_monitoring_db() は冪等に実行でき、必要に応じてカラムを追加する簡易マイグレーション処理が含まれます（例: trade_logs.latency_ms, dashboard.peak_value の追加）。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite を使い、本番 DB と完全に分離します。PAPER_FILL_MODE により Mock の約定挙動を制御できます。
- OpenAI の呼び出し
  - API エラー（429 / ネットワーク断 / 5xx）については指数バックオフでリトライします。重大な失敗時はフェイルセーフ（スコア 0 やスキップ）を行い、運用停止につながらない設計です。
- 権限
  - process priority / cpu affinity の設定は OS や実行権限に依存します。失敗した場合は警告を出してスキップします。
- ログレベル
  - Settings.log_level で検証可能。起動スクリプト内で logging.basicConfig(level=logging.INFO) 等が設定されています。

---

必要に応じて README にサンプル .env.example、requirements.txt、あるいは各コンポーネントの詳細ドキュメント（API 仕様、DB スキーマ、Engine の設定）を追記してください。質問や特定コンポーネントの詳細説明（例: ExecutionEngine の内部フロー、order_repository スキーマ等）が必要であればお知らせください。