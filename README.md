# KabuSys

日本株自動売買システムの一部（実行エンジン、監視、ポートフォリオ構築、研究、AI ニューススコアリング等）のコードベースです。  
この README はリポジトリ内の主要コンポーネントと利用方法（セットアップ・起動手順等）をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する複数コンポーネント群を含みます。主な目的は次のとおりです。

- シグナルに基づく発注と注文状態管理（ExecutionEngine）
- 発注・約定の監視とリスク監視（Monitoring）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制約）
- 研究用ファクター計算・特徴探索（DuckDB を用いたオンプレミス計算）
- ニュース記事に対する LLM ベースのセンチメント評価（OpenAI API）
- Paper Trading（検証用の完全分離 DB）と検証レポート生成
- Streamlit ベースの監視ダッシュボード

設計上の特徴:
- 環境変数および .env ファイルによる設定（自動ロード機能あり）
- production / paper_trading / development 等の実行モード切替
- DuckDB / SQLite を利用したデータ永続化・解析
- 外部 API（kabuステーション, J-Quants, OpenAI, LINE）との連携を想定

---

## 機能一覧（主なコンポーネント）

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV により Paper Trading（モックブローカー）を選択可能。
  - 発注、リスク管理、リコンシリエーションを行う。
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。監視データを SQLite に記録。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
- monitoring/
  - system_monitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度を監視して記録。
  - trade_monitor: 滞留注文、約定異常価格を検出してリスクログへ記録。
  - risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ生成。
  - kill_switch: フラグファイルを使って外部に停止シグナルを出す（data/kill.flag）。
  - alert_manager: LINE Messaging API で通知（クールダウン管理あり）。
  - monitoring_engine: これらを束ねてポーリングするエンジン。
  - monitoring_db: SQLite スキーマ初期化と CRUD ユーティリティ。
  - streamlit_dashboard: 監視 DB を参照する Streamlit ダッシュボード。
- execution/
  - order_manager, order_repository, reconciler 等：注文ライフサイクル管理、起動時リコンシリエーション。
- portfolio/
  - portfolio_builder, position_sizing, risk_adjustment：候補選定、重み付け、株数算出、セクター制限、レジーム乗数。
- research/
  - factor_research, feature_exploration：ファクター計算、将来リターン、IC、統計サマリー等。DuckDB を使用。
- ai/
  - news_nlp: raw_news を集約し OpenAI に投げて銘柄ごとにセンチメントを算出し ai_scores に書き込む。
  - regime_detector: ma200 等とマクロニュースの LLM 評価を組合せて市場レジーム判定を行い DB へ書き込む。
- tools/
  - paper_verification_report.py: Paper Trading DB を解析して検証レポートを生成。

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントの構文や型表記に依存）
- SQLite / DuckDB が利用できる環境
- ネットワーク接続（OpenAI 等外部 API を使う場合）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   以下のパッケージが最低限必要です（環境に合わせて適宜インストールしてください）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード使用時)
   例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数の設定
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすれば自動ロードを無効化可能）。
   主要な環境変数（代表例）:
   - KABUSYS_ENV: execution モード。`development`|`paper_trading`|`live`（デフォルト: development）
     - paper_trading: MockBrokerClient を使用し DB を data/paper_trading.db に分離
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須で利用部位がある場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実取引時）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）

5. データディレクトリ作成
   - mkdir -p data

6. DB 初期化
   - 監視 DB のテーブルは run_monitoring/run_execution 等で起動時に自動的に作成されます（init_monitoring_db が冪等に実行します）。

---

## 使い方（主要な起動コマンド例）

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV で切替）
  - 環境変数を設定してから:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    KABUSYS_ENV=live python -m kabusys.run_execution

  - 実行時の挙動:
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - live: 実ブローカーへ接続（KABU_API_PASSWORD 等が必要）

- Monitoring（SystemMonitor の単体ループ）を起動
  - 環境変数 MONITOR_POLL_INTERVAL を使ってポーリング間隔を上書き可能（秒）
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - 監視は monitoring_db を初期化し、system_status, trade_logs, positions, risk_logs, dashboard を管理します。

- Streamlit ダッシュボードを起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（省略時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI ニューススコアリング
  - モジュール関数を呼ぶ形です（直接実行用の CLI は未実装）。例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="OPENAI_KEY")

  - OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。

---

## 主要設定（環境変数まとめ）

- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（例: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD: kabu API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: ExecutionEngine PID ファイル（data/execution.pid）
- KILL_FLAG_PATH: kill.flag（data/kill.flag）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

※ .env/.env.local に記述すると自動で読み込まれます（プロジェクトルートの検出は .git または pyproject.toml を基準に行われます）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env ロード、Settings クラスによる集中管理
  - run_execution.py
    - ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて挙動が変わる）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading DB の検証レポート生成ツール
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ作成・CRUD を提供
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定異常監視
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - フラグファイルによる停止シグナル管理
    - alert_manager.py
      - LINE への通知（クールダウン付き）
    - monitoring_engine.py
      - 各 Monitor を統合してポーリングするエンジン
    - streamlit_dashboard.py
      - Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ...（発注・リコンシリエーション・DB 系）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定・重み付け・単元丸め・セクター制約・レジーム乗数
  - research/
    - factor_research.py, feature_exploration.py
      - ファクター計算、将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を集約し OpenAI で銘柄ごとにセンチメントを算出して ai_scores に書き込む
    - regime_detector.py
      - MA200 とマクロニュース LLM 評価を組み合わせて市場レジームを判定
  - data/ (想定)
    - data/kabusys.duckdb
    - data/monitoring.db
    - data/paper_trading.db
    - data/execution.pid
    - data/kill.flag

---

## 運用上の注意・補足

- Paper Trading と本番 DB は完全に分離されています（paper_trading 実行時は PAPER_TRADING_SQLITE_PATH が使われます）。
- monitoring コンポーネントはどの環境でも本番用の sqlite_path を参照する設計になっている箇所があります（run_monitoring の挙動に注意）。
- PID ファイルと kill.flag を使った外部制御に対応しています。Execution 起動時に kill.flag をクリアするかを設定で制御できます。
- OpenAI への呼び出しはリトライ（指数バックオフ）やレスポンス検証・スコアクリッピングなどフェイルセーフ処理が実装されていますが、API コストやレート制限に注意してください。
- DuckDB に対する executemany の空リストはバージョンによって挙動が異なるため、コード内で空配列対策が施されています。
- プロセス優先度設定（set_process_priority）や CPU affinity 設定は OS により権限が必要な場合があります。権限不足だと警告ログが出てスキップされます。

---

## トラブルシューティング

- .env が読み込まれない場合:
  - プロジェクトルートが正しく検出されているか確認（.git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認。
- OpenAI 呼び出しで失敗が多発する場合:
  - OPENAI_API_KEY の有効性、API レート、ネットワークを確認。
  - news_nlp/regime_detector はリトライ実装があるためログを確認して原因を特定。
- Streamlit で DB を読み込めない場合:
  - run_monitoring で monitoring DB を初期化したか、ファイルパス（--db）を確認。
  - DuckDB/SQLite のファイルロックやパスのアクセス権も確認。

---

必要であれば、この README をベースに
- requirements.txt の作成例
- systemd / supervisor 用のサービスユニット例（run_execution/run_monitoring の起動）
- 具体的な .env.example のテンプレート
なども追加します。どれを追加したいか教えてください。