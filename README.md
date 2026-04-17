# KabuSys

日本株自動売買システムのコアライブラリ（実行エンジン、監視、ポートフォリオ構築、研究用ユーティリティ、AI連携など）。  
この README はリポジトリ内の主要機能・起動方法・設定・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株向けのアルゴリズム売買プラットフォームのコンポーネント群です。主な役割は次の通りです。

- ExecutionEngine：ブローカーと連携して注文を送信・管理する実行エンジン
- Monitoring：実行プロセスや注文の状態、システム資源、レジームやリスクを監視する機能群
- Portfolio：銘柄候補選定、配分（重み）計算、株数決定（position sizing）
- Research：ファクター計算・特徴量探索・IC計算など研究用のモジュール（DuckDB を利用）
- AI：ニュースセンチメントや市場レジーム判定のための OpenAI 連携モジュール
- Tools：Paper Trading の検証レポート生成などのユーティリティスクリプト

設計方針として、
- DuckDB/SQLite を用いたローカルデータ処理
- 環境に応じた切替（development / paper_trading / live）
- Paper Trading は本番データと完全分離
- LLM（OpenAI）呼び出しはフェイルセーフ・リトライを実装
が採用されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアント抽象化（実ブローカー / MockBrokerClient）
  - OrderManager / OrderRepository / Reconciler（再起動後の自動復旧）
  - リスクマネージャ（発注制限・回路遮断など）
- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・データ鮮度・実行プロセス状態監視
  - TradeMonitor：滞留注文・約定価格異常監視
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager：しきい値到達時の停止フラグ書き込み・LINE通知
  - MonitoringEngine：上記を束ねてポーリング実行（run_monitoring.py）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio
  - 銘柄選定、等分配/スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- Research
  - ファクター（momentum/value/volatility）計算、将来リターン、IC、統計サマリー
- AI
  - news_nlp: ニュースセンチメントを OpenAI に投げて ai_scores に保存
  - regime_detector: ETF 等の指標とマクロ記事の LLM 出力を組み合わせ市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB の検証レポート生成（合格/不合格判定）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | Y` を使用）
- Git、DuckDB、SQLite を使用するためのファイルアクセス権

1. リポジトリをクローン・カレントディレクトリに移動
   - 例: git clone ... && cd kabusys

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 目安（requirements.txt がない場合は手動で）:
     - pip install duckdb psutil requests openai streamlit
   - 実運用では lock ファイルや requirements.txt を用いて固定してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合は必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB path、デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト: 60）

例 .env（最小）
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=...
    KABU_API_PASSWORD=...
    OPENAI_API_KEY=...
    LINE_CHANNEL_ACCESS_TOKEN=...
    LINE_USER_ID=...

注意:
- .env の読み込みは .env → .env.local（.env.local が優先）で行われ、OS 環境変数は保護され上書きされません。
- .env の書式はシェルライク（export KEY=val の許容、クォート処理、コメント処理あり）。

---

## 使い方

### 実行エンジン（ExecutionEngine）を起動する
- スクリプト: src/kabusys/run_execution.py
- 起動例:
  - KABUSYS_ENV=development python src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
- 特記事項:
  - paper_trading の場合は MockBrokerClient を利用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込まれ、本番 DB と完全分離します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が保存されます。監視プロセスはこれを見てプロセス存在チェックを行います。

### 監視ループを起動する
- スクリプト: src/kabusys/run_monitoring.py
- 起動例:
  - python src/kabusys/run_monitoring.py
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
- 特記事項:
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視テーブルに記録します（KABUSYS_ENV に依らない）。
  - 停止にはプロジェクトルート/data/stop_requested.flag を作成するか、KillSwitch が条件により data/kill.flag を書き込みます。

### Streamlit ダッシュボード
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で監視 DB を表示（positions / recent orders / system / dashboard）。

### Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 起動例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で SQLite DB パスを指定（デフォルト: data/paper_trading.db）
- 出力: 検証期間の稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し PASS/FAIL 判定を行います。

### AI 関連（ニューススコアリング / レジーム判定）
- 関数:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 必須: OPENAI_API_KEY（引数で渡すことも可能）
- 注意:
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、API キー未設定時は例外となります。
  - レスポンスの保存は DuckDB の ai_scores / market_regime テーブルへ行われます。

### 停止・Kill Switch
- KillSwitch（監視コンポーネント）はドローダウンやポジション上限超過時に data/kill.flag を書き込み、ExecutionEngine 側が検知して停止する仕組みです。
- 手動停止: プロジェクトルートに `data/stop_requested.flag` を作成すると監視や実行スクリプトが次回のループで検知して終了します。

---

## 設定（Settings）について

- 設定クラス: src/kabusys/config.py の Settings/ settings インスタンス
- KABUSYS_ENV 値: development / paper_trading / live（無効値は ValueError）
- DB パスのデフォルト:
  - Monitoring (sqlite): data/monitoring.db
  - Paper trading sqlite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb
- PAPER_FILL_MODE（paper_trading の約定挙動）: instant | partial | never | reject（不正値は例外）
- ログレベルや閾値などは環境変数で上書き可能（LOG_LEVEL, CPU_THRESHOLD_PCT 等）

.env 自動読み込み:
- プロジェクトルートが .git または pyproject.toml により自動検出される場合、.env と .env.local を自動で読み込みます（OS 環境変数は保護）。

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール)
    - utils/
      - process_priority.py
      - __init__.py
    - data/                         — 実行時に利用する SQLite / pid / flag ファイル（リポジトリ直下に data ディレクトリを配置）
- pyproject.toml / その他メタ情報（プロジェクトルートに配置想定）

---

## 運用上の注意点 / ベストプラクティス

- Paper Trading と本番 DB は分離する（PAPER_TRADING_SQLITE_PATH を設定）。
- .env に機密情報を置く場合は適切にアクセス権を管理する（git 管理外にする）。
- OpenAI を利用する機能は API コストが発生するため、テスト時は API 呼び出しをモックすることを推奨します（モジュール内で呼び出し関数を差し替え可能）。
- プロセス優先度や CPU affinity の設定は権限不足で失敗する可能性があるため警告ログのみで継続します。
- DuckDB / SQLite のバージョン依存性に注意（executemany の空パラメータ制約など、コード内に互換性対策あり）。
- 監視は定期的に system_status / risk_logs / trade_logs / dashboard を更新します。ディスク容量やファイル肥大化に注意してください。

---

## 開発・デバッグ

- モジュールごとに純粋関数が多く含まれており、ユニットテストを書きやすい設計です（I/O を分離）。AI / 外部 API 呼び出しはモックで置き換えてテストしてください。
- logging.basicConfig(level=logging.INFO) を使っているため、LOG_LEVEL 環境変数（Settings.log_level）で挙動を制御できます（ただし各スクリプトは起動時に basicConfig を呼んでいます）。

---

この README はコードの主要点を抜粋してまとめたものです。詳細な実装や追加の運用手順は個別のモジュールの docstring / コメントを参照してください。必要であれば起動手順や .env の具体例、systemd 用ユニット例なども追記できます。必要な情報を教えてください。