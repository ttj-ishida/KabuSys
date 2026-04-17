# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を行う小規模なシステム群です。本リポジトリは以下の主要機能を持つモジュール群を含みます：注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI を用いたニュースセンチメント評価など。

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、コードベースのディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

- 目的：日本株自動売買のためのコンポーネント（注文作成／発注／リコンシリエーション）、監視・アラート、ポートフォリオ構築、リサーチ、ニュース NLP を統合的に提供する。
- 設計方針：
  - DB（SQLite / DuckDB）で状態を永続化し、主要ロジックは純粋関数または明確なインターフェース設計によりテスト容易性を確保。
  - Paper Trading（検証）と Live（本番）を環境変数で切り替え、Paper 時は本番 DB と完全に分離。
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントやレジーム判定機能を用意（API キー必須）。
  - 監視は独立プロセスとしてポーリング実行し、アラートは LINE Push に送信可能。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler により注文の送信・同期・再起動時の自動復旧を実装
  - Paper Trading モードでは MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）へ記録

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
  - AlertManager：LINE Messaging API による通知（クールダウン管理あり）
  - Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を表示）

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順ソート）、等分配・スコア加重配分、セクターキャップ適用、ポジションサイズ計算（単元株丸め、リスクベース等）

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン計算、IC（Information Coefficient）など
  - DuckDB を用いた高速な時系列集計

- AI（ニュース NLP / レジーム判定）
  - raw_news をまとめて OpenAI に送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み
  - ETF（1321）を用いた MA ベースの指標とマクロニュースの LLM 結果を合成して市場レジーム判定（market_regime テーブル）

- ユーティリティ
  - .env 自動ロード（.env / .env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - Paper Trading 用の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

※ここでは一般的な Python プロジェクトとしての手順を示します。実際の依存関係は requirements.txt 等で管理してください。

1. 必要条件
   - Python 3.10 以上を推奨
   - system パッケージ: libpq 等は不要（SQLite / DuckDB を使用）
   - 外部サービス: OpenAI（API キー、news/regime 機能を使う場合）、kabu API（本番連携時）

2. リポジトリをクローン
   - git clone <repo-url>
   - 作業ルートは pyproject.toml や .git が置かれているプロジェクトルートを想定

3. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt
     - （requirements.txt がない場合は duckdb, psutil, requests, streamlit, openai などを個別にインストールしてください）

4. 環境変数設定
   - プロジェクトルートに .env を作成（自動で読み込まれます）。例:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development         # development | paper_trading | live
     LOG_LEVEL=INFO
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant
     LINE_CHANNEL_ACCESS_TOKEN=...   # （アラート有効化時）
     LINE_USER_ID=...
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データディレクトリ作成
   - mkdir -p data

注意: 本番でのログ・監視構成、OpenAI のコスト管理、ブローカー API の資格情報管理は慎重に行ってください。

---

## 使い方（主要スクリプト・モジュール）

以下は主な起動例と利用方法です。プロジェクトルートで実行します。

- 監視ループ（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 挙動
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）
    - 起動時にプロセス優先度を "high" に設定し、monitoring DB（settings.sqlite_path）へ接続
    - data/stop_requested.flag が作成されるとループを終了
    - Monitoring は KABUSYS_ENV に関係なく production の sqlite_path を使用

- Execution（注文エンジン起動）
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込み（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が既に存在すれば起動せず終了
    - data/execution.pid に PID を書く（PIDファイル経由で process 健在を監視）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で monitoring DB の最新ダッシュボード / ポジション / 注文履歴 / リスクログ等を表示

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを変更可能、または --db オプションで指定

- AI 機能（ニューススコアリング / レジーム判定）
  - 関数は kabusys.ai に含まれる。スクリプト形式の CLI は無いが、Python から直接呼べます。
  - 例（Python REPL）:
    from kabusys.ai.news_nlp import score_news
    n = duckdb.connect("data/kabusys.duckdb")
    score_news(n, target_date=date(2026,4,1), api_key="sk-...")

- 停止 / Kill
  - Execution 停止トリガー: KillSwitch が条件を満たすと data/kill.flag を書き込み（ExecutionEngine は検知して停止）
  - 手動停止: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了する

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（news/regime 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定動作）
- MONITOR_POLL_INTERVAL: SystemMonitor ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 参照）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: ALERT（LINE）送信に使用

設定は .env / .env.local に記述すると自動ロードされます（ただし OS の環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス：環境変数読み取り・検証・デフォルト管理を行う
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 用の DB 分離、PID ファイル管理、stop フラグ検知）
- ai/
  - news_nlp.py：ニュースセンチメントスコア生成（OpenAI 連携）
  - regime_detector.py：マクロ + MA200 によるレジーム判定（OpenAI 連携）
- monitoring/
  - monitoring_db.py：監視用 SQLite テーブル初期化 & DB 操作ラッパー（MonitoringDB）
  - system_monitor.py / trade_monitor.py / risk_monitor.py：各種監視ロジック
  - kill_switch.py：kill.flag の書き込みロジック
  - alert_manager.py：LINE 送信ラッパー
  - monitoring_engine.py：複数モニタの統合ポーリング実装
  - streamlit_dashboard.py：Streamlit ダッシュボード
- execution/
  - order_manager.py / order_repository.py / reconciler.py / execution_engine.py / broker_factory.py など（発注 & リコンシリエーション関連）
- portfolio/
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py（ポートフォリオ構築ロジック）
- research/
  - factor_research.py / feature_exploration.py（ファクター・リサーチ）
- tools/
  - paper_verification_report.py（Paper Trading 検証レポート）
- utils/
  - process_priority.py（プロセス優先度・CPU affinity ユーティリティ）
- data/（実行時に使用される SQLite / DuckDB / flag / pid 等）
  - monitoring.db（デフォルト）
  - paper_trading.db（Paper Trading 用デフォルト）
  - kabusys.duckdb（DuckDB データ）
  - stop_requested.flag, kill.flag, execution.pid など

（上記は主要ファイルの抜粋です。詳細はソース内の docstring / コメントを参照してください。）

---

## 開発上の注意点・運用メモ

- Paper Trading と Live の DB は完全分離する設計です。KABUSYS_ENV=paper_trading を使用することで、本番用の monitoring.db を汚染しません。
- Settings モジュールは .env の自動読み込みを行います。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンス検証等のロジックを持ち、フェイルセーフとして API 失敗時は欠損値にフォールバックする設計です（ただし API キーが未設定の場合は例外を投げます）。
- 監視側は kill.flag と stop_requested.flag を使って ExecutionEngine の停止やプロセスの制御を行います。flag の運用は慎重に行ってください（誤って kill.flag を残すと ExecutionEngine が起動しません）。
- DuckDB は時系列集計用に使われます。prices_daily / raw_financials / raw_news / ai_scores / market_regime 等のスキーマを前提とした処理が含まれます。初期データ投入方法は別途スクリプトを用意してください。

---

必要であれば、README に「依存パッケージ一覧」「サンプル .env のテンプレート」「運用手順（デプロイ・systemd unit 例）」「テスト手順」などを追加できます。どの情報が要るか教えてください。