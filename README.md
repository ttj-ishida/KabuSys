# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視ツール群をまとめた小規模なシステムです。  
主に以下の機能を提供します：市場レジーム判定、ニュースセンチメント（LLM）によるスコアリング、ポートフォリオ構築、オーダー実行（paper/live 切替）、監視・アラート、検証レポート生成など。

バージョン: 0.1.0

---

## 主要特徴（機能一覧）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / PaperTrading 切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（MockBroker for paper_trading）
  - 起動時の自動リコンシリエーション（Reconciler）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視
  - SQLite ベースの監視ログ（monitoring_db）
  - KillSwitch（フラグファイルによる Execution 停止）
  - LINE Push によるアラート（AlertManager）
  - Streamlit ダッシュボード（監視ダッシュボード）
  - run_monitoring.py による常駐ポーリングループ起動

- Portfolio / Strategy（純粋関数群）
  - 銘柄選定・重み付け（equal / score）
  - セクター制限、レジーム乗数
  - ポジションサイジング（lot 単位丸め、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）
  - ニュース記事のセンチメント評価（gpt-4o-mini を活用）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
  - スコアは DuckDB の ai_scores / market_regime テーブルへ保存

- Tools
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - 注文成功率、送信率、レイテンシ、稼働率などを集計して PASS/FAIL 判定

- ユーティリティ
  - 設定 / .env パーサ（kabusys.config）
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）

---

## 要件（Prerequisites）

必須（代表例）:
- Python 3.10+
- duckdb
- psutil
- requests
- streamlit（ダッシュボード利用時）
- openai（AI スコアリング / レジーム判定）
- SQLite（標準ライブラリ sqlite3 を使用）

推奨: 仮想環境 (venv / virtualenv)

インストール例（代表的なパッケージ）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

（requirements.txt がある場合はそれを使用してください： `pip install -r requirements.txt`）

---

## 環境変数（主なもの）

設定は OS 環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

主要な環境変数（名前 — 説明 — デフォルト / 備考）:

- KABUSYS_ENV — 実行環境（development | paper_trading | live） — default: development
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合 必須）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（任意）
- LINE_USER_ID — LINE Push 送信先ユーザ ID（任意）
- DUCKDB_PATH — DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite — default: data/paper_trading.db
- PAPER_FILL_MODE — paper_trading の約定動作 ("instant"|"partial"|"never"|"reject") — default: instant
- PID_FILE_PATH — ExecutionEngine PID ファイルパス — default: data/execution.pid
- KILL_FLAG_PATH — KillSwitch フラグファイルパス — default: data/kill.flag
- LOG_LEVEL — ログレベル — default: INFO
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒） — default: 60（run_monitoring 用）

.example（.env の例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化（任意推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil requests streamlit openai
   ```

4. 環境変数を設定（`.env` または OS 環境変数）
   - 例: プロジェクトルートに `.env` を作成
   - 必須の変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）は設定してください
   - PaperTrading を試すなら `KABUSYS_ENV=paper_trading` を設定

5. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

6. DuckDB / SQLite の初期スキーマは実行時に自動作成されます（monitoring DB などは init_monitoring_db が冪等で作成します）。

---

## 使い方（起動例・コマンド）

- 監視ループを起動（常駐）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定できます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使用します（監視データは環境に関わらず production sqlite_path に記録される設計）。

- ExecutionEngine を起動（当日のセッションを実行）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PaperTrading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と分離されています。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを指定する場合: `--db data/paper_trading.db`
  - 指定しない場合は環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト `data/paper_trading.db` を使用

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 関連（ライブラリ関数）
  - ニュースセンチメントスコア: `kabusys.ai.score_news(conn, target_date, api_key=None)`（DuckDB 接続と target_date を渡す）
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 主要設計上の注意点 / 動作方針

- 設定の自動ロード:
  - プロジェクトルート検出（.git または pyproject.toml を基準）を行い `.env` / `.env.local` を自動的に読み込みます。
  - OS 環境変数はデフォルトで保護され、`.env.local` は上書き可能。

- Paper Trading の分離:
  - `KABUSYS_ENV=paper_trading` を指定すると、MockBroker と専用 SQLite（data/paper_trading.db）を使用します。実際の発注 API とは分離されます。

- フェイルセーフ設計:
  - OpenAI などの API 呼び出しが失敗してもシステムは継続動作するように設計されています（デフォルトのフォールバック値やリトライを内包）。
  - 監視・リスクイベントは SQLite の監視 DB に永続化され、dedup（一定時間内の重複ログ抑制）などの仕組みがあります。

- プロセス優先度設定:
  - 起動スクリプトは最初に `set_process_priority("high")` を試みます（psutil 経由）。権限不足などで失敗した場合は警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要なファイル・ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env パーサ、Settings クラス
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース記事 -> LLM センチメント
    - regime_detector.py          — レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite スキーマ / 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等 — 実装の詳細に応じて存在)
  - data/ (DuckDB / スキーマ定義などはここに置かれる想定)
  - utils/
    - __init__.py
    - process_priority.py

（上記は主なファイルを抜粋したものです。実際のリポジトリに含まれるファイルはさらに多く存在する可能性があります。）

---

## 開発・拡張のヒント

- DuckDB は分析用途の高速 SQL を提供します。research / ai モジュールは DuckDB 接続を受け取りテーブル（prices_daily / raw_financials / raw_news 等）を参照します。
- AI 機能は OpenAI を利用する設計になっています。API 呼び出し部分はテスト用に差し替えやすく実装されています（_call_openai_api を patch するなど）。
- monitoring_db.py はテーブル作成を冪等に行い、マイグレーション的なカラム追加チェックも備えています。
- リリース / デプロイ時は KABUSYS_ENV の切替により paper/live を明確に分離してください（DB の分離が重要）。

---

## ライセンス / 責任範囲

このドキュメントはコードベースの説明を目的としています。実運用での損失や法規制対応については利用者の責任で対応してください。実際の発注を行う際は十分なテスト・モニタリング・監査を行ってください。

---

必要に応じて README に追記します：
- 依存関係をまとめた requirements.txt（あれば）
- 実行時のログ設定・rotate の推奨
- よくあるエラーと対処（例：OpenAI のレート制限、psutil 権限エラー）など

変更してほしい箇所や、README に追加したい情報（例: サンプル .env、CI/CD 手順、ユニットテスト実行方法など）があれば教えてください。