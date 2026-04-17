# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。注文発行・リコンシリエーション・リスク監視・監視ダッシュボード・ポートフォリオ構築・リサーチ・AI を用いたニューススコアリング等の機能を含みます。

以下はこのリポジトリの簡易 README（日本語）です。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成される自動売買システムです。

- Execution Engine：ブローカーとのやり取りを行い注文を発行・管理する実行エンジン
- Monitoring：システム状態、注文状況、リスク指標を定期監視しログ・アラートを出す
- Portfolio Construction：候補選定、重み付け、ポジションサイズ決定、セクター制限 など
- Research：DuckDB を用いたファクター計算・特徴量解析・フォワードリターン計算
- AI（news_nlp / regime_detector）：OpenAI を用いたニュースのセンチメント評価・レジーム判定
- Tools：Paper Trading 検証レポートや簡易ダッシュボード（Streamlit）など

設計上の主眼は「本番と検証（paper_trading）を分離」「ルックアヘッドを避ける」「フェイルセーフ（API失敗時は安全側にフォールバック）」です。

---

## 機能一覧（主な機能）

- 実行系
  - ExecutionEngine 起動（run_execution.py）
  - ブローカー抽象化（実ブローカー / MockBroker の切替）
  - リコンシリエーション（起動時の注文・ポジション同期）
  - OrderManager / OrderRepository による注文状態管理
- 監視系
  - SystemMonitor: CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE Push 通知（クールダウン管理）
  - MonitoringEngine：複数 Monitor を束ねたポーリングループ
  - streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分・スコア配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース / equal / score）
- リサーチ
  - momentum / volatility / value ファクター計算（DuckDB）
  - forward returns、IC（Spearman）計算、ファクター統計
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄ごとにセンチメントを生成し ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロニュースによる日次レジーム判定（OpenAI 使用）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - DB 初期化 / マイグレーションロジック（monitoring_db.init_monitoring_db）

---

## 前提・依存

- Python 3.10+
  - union 型（A | B）を使用しているため少なくとも 3.10 が必要です。
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite3（組み込み）
- （実ブローカー連携時は kabuステーション API の設定が必要）

必要なパッケージはプロジェクトに requirements.txt がある場合はそちらを利用してください。無ければ下記を例としてインストールしてください:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo_url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは必要なパッケージを個別に pip install してください（上記参照）。

4. 環境変数設定
   - .env / .env.local をプロジェクトルートに置くと自動的に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（使用機能に応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY
   - 便利な設定（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, など
   - 詳細は src/kabusys/config.py を参照してください。

5. data ディレクトリ
   - 実行時に data/ 以下 (execution.pid, kill.flag, stop_requested.flag, monitoring.db, paper_trading.db など) が使われます。
   - 必要に応じて書き込み権限を確認してください。

---

## 使い方（コマンド例）

※ 実行はプロジェクトルート（pyproject.toml または .git がある場所）をカレントにするか、PYTHONPATH に src を含めてください。パッケージとしてインストールしていれば `python -m kabusys.<module>` で起動できます。

- Execution Engine を起動（実運用 or paper_trading）
  - 本番モード例:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（モックブローカー、DBを分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 注意:
    - paper_trading の場合は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）へ記録され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が既に存在すると起動を中止します。
    - ExecutionEngine は data/execution.pid を作成します。プロセス検出や stale PID 検出に利用されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（監視ログは常に同じ DB に保存する設計）。
  - 停止: data/stop_requested.flag を作成するとループが終了します（監視プロセス内で検出して終了）。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトは data/monitoring.db。引数 --db で読み取り専用の DB を指定できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パス指定可。
  - 出力は標準出力にテキストレポートを表示します。

- AI 関連の関数を直接呼ぶ（Python スクリプトまたは REPL）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - 事前に DuckDB 接続を作成し（duckdb.connect(path)）、raw_news / prices_daily 等のテーブルがあることを確認してください。
  - OpenAI API キーが無いと例外になります（api_key 引数または環境変数 OPENAI_API_KEY）。

- Kill / Stop フラグ
  - KillSwitch は data/kill.flag を生成して ExecutionEngine に停止を要求します（実行エンジンは起動時に kill.flag を確認する設計）。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution の外部停止フラグとして使われています。

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須: 機能を使う場合）
- KABU_API_PASSWORD: kabuステーション API 用（必須: 実ブローカー連携時）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, PAPER_FILL_MODE など多数（詳細は src/kabusys/config.py を参照）

.env / .env.local の自動ロード順序:
- OS 環境変数 > .env.local（上書き） > .env（未設定のみ）
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

概略:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings
    - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - utils/
      - process_priority.py           — psutil を使った優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite テーブル初期化と MonitoringDB クラス
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (等、実行系の実装ファイル)
      - ... (broker_factory, execution_engine 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/ (実行時に生成されることがある)
      - monitoring.db, paper_trading.db, kabusys.duckdb 等
      - kill.flag / stop_requested.flag / execution.pid

（上記は本リポジトリから抽出した主要ファイル群のサマリです。細かなファイルは repo を参照してください。）

---

## 実装上の注意点 / 補足

- Settings（config.py）はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします。テストや CI で自動ロードを無効化できます。
- Monitoring の DB 初期化（init_monitoring_db）は冪等実行で必要なテーブルやマイグレーション（列追加）を行います。
- 実行開始直後にプロセス優先度を "high" に設定する呼び出しがあるため、環境により権限不足で警告が出ることがあります（psutil を利用）。
- AI 部分は OpenAI API を利用します。API 利用量やレート制限に注意してください。news_nlp と regime_detector はリトライ・バックオフやフェイルセーフの実装があります。
- paper_trading モードでは MockBroker を使い、本番 DB と分離された PAPER_TRADING_SQLITE_PATH に書き込みます（実運用の誤発注防止）。
- streamlit ダッシュボードは監視 DB を読み取り専用で開く（URI に ?mode=ro を付ける）ため、起動中の監視プロセスと共存できます。

---

## 開発 / 貢献

- まずは動作確認用のデータ（DuckDB の prices_daily、raw_news 等）を用意して、research / ai / monitoring の各機能を単体で実行してみてください。
- 単体関数は比較的純粋関数として書かれている箇所が多く（portfolio や research の関数群など）、ユニットテストを作りやすい設計になっています。
- 変更を加える際は .env.example を更新し、必要な環境変数や挙動のドキュメントを明記してください。

---

以上がこのリポジトリの README.md 相当の概要です。必要であれば、特定のコンポーネント（例: ExecutionEngine の設定方法、OrderRepository の DB スキーマ、AI モジュールのプロンプト設計）の詳細ドキュメントや起動スクリプトの具体例を追加で作成します。どの部分を詳しく説明しましょうか？