# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なシステムです。戦略（ファクター計算・特徴量解析）、ポートフォリオ構築、注文実行、監視（システム・注文・リスク）、AI（ニュース NLP / レジーム判定）などのモジュールを含みます。

以下はこのリポジトリで提供される主要機能、セットアップ方法、使い方、ディレクトリ構成の概要です。

---

## プロジェクト概要

- 株価データ（DuckDB）を用いたファクター計算・リサーチ機能
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 注文実行エンジン（ブローカー抽象化、Paper Trading 対応）
- 監視プログラム（システム状態、注文滞留、ドローダウン監視）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- 監視用の簡易ダッシュボード（Streamlit）
- Paper Trading 検証レポート生成ツール

設計方針として、ルックアヘッドバイアスを防ぐ実装や部分失敗時のフェイルセーフ（API 失敗時はスキップして継続）を重視しています。

---

## 機能一覧（ハイライト）

- research:
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials からファクター計算
  - calc_forward_returns, calc_ic, factor_summary：特徴量探索・IC 計算
- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier
- execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler（再起動時の自動復旧）
  - BrokerClientFactory を通じた本番／モックの切替（KABUSYS_ENV）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine（ポーリングループで各 Monitor を実行）
  - MonitoringDB：SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager：LINE Push 通知（クールダウン管理）
  - KillSwitch：条件により ExecutionEngine 停止フラグを書き込み
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- ai:
  - news_nlp.score_news：OpenAI でニュースをスコア化して ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロセンチメントを合成して市場レジーム判定
- tools:
  - paper_verification_report：Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提: Python 3.9+（コードの型表記に合わせることを推奨）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限次を入れてください:
     - pip install duckdb psutil openai streamlit requests
     - （実行環境により他パッケージが必要になる場合があります）
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先、`.env.local` は上書き）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. data ディレクトリの作成（必要時）
   - mkdir -p data

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- OPENAI_API_KEY — OpenAI を利用する機能で必要（ai.news_nlp / regime_detector）

よく使う任意設定（Settings にて既定値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading を選ぶと Execution は MockBrokerClient を使用し、data/paper_trading.db に記録され本番 DB とは分離されます
- PAPER_FILL_MODE: instant / partial / never / reject（paper_trading 時の約定挙動）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：AlertManager（LINE）用
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）

---

## 使い方

以下は主要な実行コマンド例です。ソースはパッケージ形式に配置されているため、モジュールとして実行できます。

- 実行エンジン（ExecutionEngine）起動
  - 通常実行:
    - python -m kabusys.run_execution
  - Paper Trading 環境で実行（Mock ブローカー・分離 DB）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 動作:
    - 起動時に process priority を high に設定
    - Settings に応じて SQLite（本番 or paper）に接続
    - Engine は別スレッドで動作し、data/execution.pid に PID を書く
    - stop は data/stop_requested.flag を作成すると検出して停止

- 監視ループ起動（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）
    - 例: export MONITOR_POLL_INTERVAL=30

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは:
    - streamlit run -m kabusys.monitoring.streamlit_dashboard -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。
  - 直接スクリプト化されているエントリポイントはありませんが、Python API として呼び出せます。
    - 例:
      - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, date(2026, 4, 10), api_key="...")

停止・強制終了の仕組み
- data/stop_requested.flag：run_execution/run_monitoring のループはこのファイルの存在を監視し、検出すると優雅に停止します。
- KillSwitch（監視経由）で data/kill.flag が書かれると、実行エンジンに停止シグナルを送る設計です（Execution 側は起動時に設定でクリアする挙動がある場合があります）。

ログ
- 各スクリプトは logging.basicConfig(level=logging.INFO) をデフォルトで使用します。LOG_LEVEL 環境変数で変更可能。

---

## ディレクトリ構成（主要ファイル）

トップレベル（src/kabusys を想定）

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）

- src/kabusys/config.py
  - Settings クラス：環境変数管理・自動 .env ロード（.env / .env.local）

- src/kabusys/run_execution.py
  - ExecutionEngine を初期化して起動するスクリプト
  - Paper Trading 切替、pid/stop フラグ管理

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能

- src/kabusys/execution/
  - order_manager.py, reconciler.py, ... — 注文・再同期・リスク管理など

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル初期化・CRUD
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種チェック
  - monitoring_engine.py — 各 monitor をまとめる
  - alert_manager.py — LINE push 通知
  - kill_switch.py — 停止フラグの読み書き
  - streamlit_dashboard.py — 監視ダッシュボード

- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算・統計解析

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築

- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメントを OpenAI で評価して ai_scores に書き込み
  - regime_detector.py — MA とマクロセンチメントを合成して市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - デフォルトの DB / フラグ / pid を置く想定ディレクトリ
  - 例:
    - data/kabusys.duckdb (DuckDB)
    - data/monitoring.db (監視 SQLite)
    - data/paper_trading.db (Paper Trading 用 SQLite)
    - data/execution.pid
    - data/stop_requested.flag
    - data/kill.flag

---

## 追加ノート / 運用上の注意

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動で読み込みします。
  - OS の環境変数は保護され、`.env.local` の override は可能ですが保護されたキーは上書きされません。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading
  - KABUSYS_ENV=paper_trading にすると本番 DB と完全に分離された paper_sqlite_path が使用されます。
  - PAPER_FILL_MODE で Paper Broker の約定挙動を設定できます（instant/partial/never/reject）。

- OpenAI 呼び出し
  - API の失敗（429・タイムアウト・ネットワーク断・5xx）に対して指数バックオフでリトライしますが、最終的に失敗した場合はフェイルセーフとして処理をスキップします。
  - テスト時は内部の API 呼び出し関数をモックできるように設計されています（ユニットテストでの置換を想定）。

- 権限
  - process priority 設定や CPU affinity の適用では権限不足で失敗する可能性があります。失敗した場合はログに警告を出してスキップします。

---

必要であれば、README にサンプル .env、より詳しい起動例（systemd ユニット例や Dockerfile、CI の設定例）や API 使用例（各モジュールの使い方コードスニペット）を追加します。どの情報を優先して追記しますか？