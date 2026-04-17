# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。本リポジトリには以下の機能群（発注エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニュース判定など）が含まれます。各コンポーネントは可能な限りフェイルセーフに実装されており、paper trading（検証環境）を本番データベースから分離して動作させる仕組みを備えています。

- 推奨 Python バージョン: 3.10+
- 主要依存ライブラリ（例）: duckdb, psutil, requests, openai, streamlit

## 機能一覧

- Execution
  - ExecutionEngine による注文発行 / リスク管理 / オーダー管理
  - Broker クライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - 自動リコンシリエーション（再起動後の注文・ポジション同期）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク使用率、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文（stale order）・約定価格異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 一定条件で ExecutionEngine を停止するフラグ書き込み
  - AlertManager: LINE Push によるアラート送信（オプション）
  - Monitoring DB（SQLite）へのログ永続化と Streamlit ダッシュボード
- Portfolio construction
  - 候補選定・重み算出（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ算出（単元丸め・制約適用）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini 等）でスコアリングして ai_scores に格納
  - regime_detector: ETF（1321）MA とマクロニュースを組み合わせて市場レジーム判定
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools: Paper Trading の検証レポート生成スクリプト

## セットアップ手順

1. リポジトリをクローン
   - git clone … && cd <repo>

2. Python 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（必要なものを列挙）
   - pip install duckdb psutil requests openai streamlit

   （実際のプロジェクトでは requirements.txt / pyproject.toml に依存がまとめられている想定です）

4. PYTHONPATH を設定して実行できるようにする（ローカル実行時）
   - export PYTHONPATH=src
   - Windows (PowerShell): $env:PYTHONPATH = "src"

5. .env ファイル作成（プロジェクトルート）
   - .env.example を参照して作成してください。自動読み込みの順序:
     - OS 環境変数 > .env.local > .env
   - 必須/主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）を使う場合は必須
     - KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
   - 任意（デフォルトあり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject", デフォルト: instant)
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / その他

6. data ディレクトリ
   - デフォルトの DB ファイルやフラグファイルは data/ 配下に作られます。必要があれば作成してください（スクリプトが自動で作成することもあります）。

備考:
- monitoring の初期テーブルは各起動スクリプト内で init_monitoring_db が呼ばれ自動作成されます（冪等）。
- Execution の paper_trading モードは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に完全に分離して書き込みます。

## 使い方

基本的にはパッケージを PYTHONPATH に含めた状態で、モジュールとして実行します。

- 監視プロセスを起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を変更可能（例: 30 秒）
  - 実行例:
    - export PYTHONPATH=src
    - python -m kabusys.run_monitoring
  - 備考:
    - 監視ループは data/stop_requested.flag の存在をチェックして終了します（停止したい場合はそのフラグファイルを作成）。

- 発注エンジンを起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 実行例:
    - export PYTHONPATH=src
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成するとエンジンは停止します。
    - KillSwitch（条件達成）により data/kill.flag が書き込まれると Execution 側で検出して停止します。

- Streamlit ダッシュボード
  - 監視 DB を読み取り専用で表示します。
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB が存在しない・開けない場合はエラー表示されます。

- Paper Trading 検証レポート（CLI）
  - スクリプト: kabusys.tools.paper_verification_report
  - 実行例:
    - export PYTHONPATH=src
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で別 DB を指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db が使われます）
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを判定し PASS/FAIL を出力します。

- AI 機能（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を呼ぶか、上位の処理から呼び出されます。
  - OpenAI API キー (OPENAI_API_KEY) が必要です。API 呼び出しはリトライ・フェイルセーフ（失敗時は 0.0 等でフォールバック）を備えています。

- 環境切替
  - KABUSYS_ENV は以下をサポート: development, paper_trading, live
  - Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（production 相当）を使用する点に注意（run_monitoring の実装より）。

- プロセス優先度
  - 起動スクリプトは起動時に set_process_priority("high") を実行します（プラットフォームによる制限あり。権限不足時は警告でスキップ）。

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定方式）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔秒（デフォルト: 60）
- PID_FILE_PATH: Execution Engine 用 PID ファイルのパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアする（"1" で有効）

## 停止 / フラグ方式

- 停止要求（外部からの安全停止）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
- KillSwitch（リスクトリガ）:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag に理由を書き込みます。Execution 起動時に設定によりこれをクリアすることも可能です。

## ディレクトリ構成（抜粋）

（ファイルは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数 / Settings 管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ層（テーブル作成・読み書き）
    - system_monitor.py — CPU/mem/disk/process/data鮮度監視
    - trade_monitor.py — 滞留注文 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知クライアント
    - monitoring_engine.py — 各モニタの束ね
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・同期ロジック（主要ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み算出
    - position_sizing.py — 株数計算・丸め・制約適用
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - utils/
    - process_priority.py — 優先度 / CPU affinity ユーティリティ
  - data/  （実行時に生成される想定）
    - monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, execution.pid, kill.flag など

## 注意事項 / 実運用にあたって

- OpenAI やブローカー API の呼び出しは課金やレート制限のリスクがあるため、API キーの管理や呼び出し制御（レート制限、リトライポリシー）は十分注意してください。本コードでは一部リトライ・クリッピング等の耐障害処理を実装していますが、実運用前に十分なテストを行ってください。
- Paper Trading モードは本番 DB と完全に分離されますが、設定ミスで本番 DB にアクセスしないよう .env の内容・KABUSYS_ENV を確認してください。
- process priority の変更や PID 操作は OS 権限に依存します。権限不足で失敗するケースは警告ログによりスキップされます。
- DuckDB / SQLite のバージョン差・SQL 文法差により挙動が異なる場合があります。テスト環境での検証を推奨します。

---

必要であれば、README に含める .env.example のテンプレートや systemd / supervisor 用の起動ユニット例、より詳細な開発者向けセットアップ手順（テスト実行、モックブローカーの利用方法など）も作成します。どの情報が必要か教えてください。