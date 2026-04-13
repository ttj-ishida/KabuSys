# KabuSys

KabuSys は日本株の自動売買システム（コアライブラリ）です。戦略のポートフォリオ構築、注文管理、実行エンジン、監視・アラート機能、ニュースの NLP スコアリング、リサーチユーティリティなどを含みます。

以下はこのリポジトリ（src/kabusys/**）の簡易 README です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 主要な環境変数（抜粋）
- ディレクトリ構成

---

## プロジェクト概要

- 日本株向けの自動売買基盤ライブラリ群。
- DuckDB / SQLite をデータストアとして利用し、戦略（ファクター計算・ポートフォリオ構築）と実行（ブローカー呼び出し）を分離。
- 監視（System / Trade / Risk）とアラート（LINE push）を備え、異常時は ExecutionEngine を停止させる kill flag を書く仕組みを提供。
- Paper Trading 用の分離された DB と Mock ブローカーを使った検証機能を提供。
- OpenAI を用いたニュースセンチメント（AI）モジュールと、それを利用した市場レジーム判定を実装。

---

## 機能一覧

- Execution
  - ExecutionEngine（発注／注文状態管理／リコンシリエーション）
  - OrderManager / OrderRepository（SQLite ベース）
  - リスク管理（RiskManager）
  - BrokerClientFactory による本番／モック切替（KABUSYS_ENV）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス状態監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン / ポジション数監視
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager：LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（監視用）
- Portfolio
  - 候補選定、等分配・スコア配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（ロット丸め・aggregate cap）
- Research
  - ファクター計算（Momentum/Volatility/Value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュースのセンチメント評価（OpenAI API を利用）
  - レジーム検出（ETF MA + マクロニュースセンチメントの合成）
- Tools
  - paper_verification_report：Paper Trading 結果からの検証レポート生成

---

## セットアップ手順（開発環境向け）

1. 前提
   - Python 3.10+ を推奨（型ヒントの構文などで 3.10 以上を想定）
   - git, sqlite3（OS 標準）、DuckDB（Python パッケージ）

2. リポジトリをクローン
   - git clone <リポジトリ>
   - カレントをプロジェクトルートにする（pyproject.toml/.git があるディレクトリ）

3. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

4. 依存パッケージをインストール
   - pip install -U pip
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   ※ requirements.txt があれば pip install -r requirements.txt を使用してください。

5. PYTHONPATH の設定（開発時）
   - ソースが `src/` 下にあるため、パッケージを使うには `PYTHONPATH=src` を通すか、編集可能インストールを行います。
   - 例:
     - export PYTHONPATH=src
     - またはプロジェクトルートで pip install -e ".[dev]"（該当設定がある場合）

6. データディレクトリ
   - デフォルトで `data/` 以下に DB 等を置きます。必要なら作成してください。
     - mkdir -p data

7. 環境変数の設定
   - .env / .env.local に必要なキーを記述できます（config モジュールが自動ロードします）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数は次節参照。

---

## 使い方（主なコマンド）

注意: 開発時は project root から実行し、PYTHONPATH=src を通すか pip install -e して下さい。

1. 監視ループ起動（Monitoring）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
   - 実行例:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - 監視は MonitoringDB（SQLite）へ永続化します。init_monitoring_db は自動で呼ばれます。

2. 実行エンジン起動（Execution）
   - KABUSYS_ENV によりモードを切替:
     - development / paper_trading / live
     - paper_trading の場合は MockBrokerClient を使用し、Paper 用の SQLite（デフォルト: data/paper_trading.db）に記録
   - 実行例:
     - PYTHONPATH=src python -m kabusys.run_execution
   - Execution 起動時に監視用テーブル（monitoring DB）を冪等で初期化します。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。`--db PATH` または環境変数 PAPER_TRADING_SQLITE_PATH で変更可能。

4. Streamlit 監視ダッシュボード
   - 起動例（ファイル内のヘルプにも同様の記載あり）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. AI モジュール（ニューススコア / レジーム）
   - プログラム的に利用:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key="...") など
   - OpenAI API キー（OPENAI_API_KEY）を環境変数または api_key 引数で渡す必要があります。

6. 注意点
   - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（設定の sqlite_path）を使用します（監視ログは一元化）。
   - Execution の Paper Trading は paper_sqlite_path（data/paper_trading.db がデフォルト）へ完全に分離されます。
   - 起動時、プロセス優先度を High に設定しようとします（psutil の権限に依存し失敗可）。

---

## 主要な環境変数（抜粋）

- 基本
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動 .env 読み込みを無効化）
- API / トークン
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須: Settings.jquants_refresh_token を参照する箇所がある）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE Push 用
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- 監視
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: "1" で ExecutionEngine 起動時に kill.flag をクリア
- リソースしきい値
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（パーセンテージ）

例（.env の一部）
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60
```

---

## 注意点・補足

- .env のパースは多少柔軟で、export KEY=val やクォート／エスケープに対応します。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。
- Process priority / CPU affinity の設定は OS に依存し、権限がない場合は警告を出してスキップします（psutil に依存）。
- DuckDB / SQLite のスキーママイグレーションは起動時にある程度自動で行われます（例: カラム追加）。
- OpenAI API の呼び出しは再試行ロジックや JSON バリデーションを備え、失敗時はフェイルセーフでスコア 0.0 を使ったり部分的にスキップします（システムの健全性を優先）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/.env ローダー & Settings
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - utils/
      - process_priority.py          — 優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite の永続化層（テーブル初期化/読み書き）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py       — streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository など)
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py

---

もし README に追記してほしい項目（例: 実際の依存関係ファイル生成、CI のセットアップ、デプロイ手順、より詳しい環境変数一覧、API キーの安全な管理方法など）があればお知らせください。必要に応じてサンプル .env.example も作成します。