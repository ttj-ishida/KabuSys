# KabuSys

日本株自動売買システムのコードベース（簡易ドキュメント）です。本リポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース/NLP）モジュールなどで構成されています。

以下は開発者／運用者向けの概要、機能、セットアップ手順、使い方、ディレクトリ構成です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。主な役割は：

- シグナルに基づく発注（ExecutionEngine）
- 実行状態の自動リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視・アラート（MonitoringEngine / AlertManager / KillSwitch）
- ポートフォリオ構築（候補選定・配分・ポジションサイジング）
- ファクター計算・リサーチ（DuckDB を用いた factor / feature モジュール）
- ニュースの NLP によるセンチメント算出（OpenAI を利用）
- Streamlit による監視ダッシュボード

運用は複数プロセス（Execution, Monitoring, optional: Streamlit ダッシュボード）で行う想定です。

---

## 主な機能一覧

- Execution
  - Signal Queue ベースの発注（発注の Gate チェック、レート制限、Circuit Breaker）
  - ブローカー同期（sync_order）・起動時リコンシリエーション
  - Paper trading モード（本番 DB と分離して data/paper_trading.db に記録）
- Monitoring
  - SystemMonitor：CPU/Memory/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：キーファイル（data/kill.flag）を生成して Execution を停止
  - AlertManager：LINE Push による通知（クールダウンあり）
  - Streamlit ダッシュボード（監視データ閲覧）
- Portfolio
  - 候補選定、等金額/スコア加重配分、リスクベースの株数決定、セクター上限、レジーム乗数
- Research
  - Momentum / Volatility / Value 等ファクター算出（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini 等）で評価して ai_scores テーブルへ格納
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定
- Utilities
  - 設定管理（.env 自動読み込み / Settings）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントで PEP 604 の「|」を使用）
- SQLite（標準ライブラリ）
- DuckDB（pip install duckdb）
- psutil（pip install psutil）
- requests（pip install requests）
- openai（pip install openai） — AI 機能を使う場合
- streamlit（pip install streamlit） — ダッシュボードを使う場合

例（仮の requirements が無い場合の最小インストール例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 設定（環境変数・.env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（デフォルト）。読み込み順は OS 環境 > .env.local > .env。自動読み込みを無効化するには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（代表例）:

- KABUSYS_ENV: 起動環境（development, paper_trading, live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、既定 60）

注意: Settings クラスで必須項目が未設定の場合は起動時に ValueError が発生します。`.env.example` を参照して設定してください（リポジトリに存在する場合）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてルートに移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` をプロジェクトルートに作成して必要な環境変数を設定
5. data ディレクトリを作成（初回のみ）
   ```bash
   mkdir -p data
   ```
6. 初回起動時は SQLite / DuckDB ファイルはプロセスが接続することで自動作成・マイグレーションされます（monitoring_db.init など）。

---

## 起動 / 使い方

注意: 実際の運用では Execution と Monitoring を別プロセスで常時稼働させます。paper_trading モードでは本番 DB と分離された DB に記録されます。

- Monitoring の起動（ポーリングループ）

  MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）:

  ```bash
  # 例: 30秒間隔で監視
  export MONITOR_POLL_INTERVAL=30
  PYTHONPATH=src python src/kabusys/run_monitoring.py
  ```

  run_monitoring はプロセス優先度を `high` に設定し、監視用 SQLite（settings.sqlite_path）と DuckDB に接続します。
  Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。

- Execution（発注エンジン）の起動

  paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録します。

  ```bash
  # 本番/開発用
  export KABUSYS_ENV=development  # or live

  # Paper trading
  export KABUSYS_ENV=paper_trading

  PYTHONPATH=src python src/kabusys/run_execution.py
  ```

  実行時にプロセス優先度が `high` に設定され、必要なコンポーネント（BrokerClient, OrderRepository, RiskManager, ExecutionEngine 等）が組み立てられます。

- Streamlit ダッシュボード（監視 UI）

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  デフォルトは data/monitoring.db。Monitoring を先に起動していないと閲覧できない場合があります（read-only 接続を試みます）。

- AI 機能（ニュース NLP / レジーム判定）

  OpenAI API キーが必要です（OPENAI_API_KEY）。モジュールの関数は以下のように呼べます（例は Python REPL）:

  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  # duckdb 接続を作成して呼び出す
  import duckdb, datetime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, datetime.date(2026, 3, 20), api_key="sk-...")
  score_regime(conn, datetime.date(2026, 3, 20), api_key="sk-...")
  ```

- kill.flag による安全停止

  KillSwitch は data/kill.flag を書き込み、ExecutionEngine 起動中にそれを検出して安全停止を促します。Execution 起動時の初期化で kill flag をクリアするオプション（Settings.kill_flag_clear_on_start）があります。

---

## 重要な挙動・運用メモ

- Paper trading は本番 DB と明確に分離されます（settings.is_paper により data/paper_trading.db を使用）。
- run_monitoring は MONITOR_POLL_INTERVAL に従って監視を行い、例外はログ出力して次のポーリングに続行します。
- Process priority は set_process_priority("high") により可能な範囲で優先度を上げます（プラットフォーム依存、権限により失敗する場合あり）。
- AI 呼び出しは 429/タイムアウト/5xx 等をリトライ（エクスポネンシャルバックオフ）します。失敗時はフォールバックやスキップを行い、致命的例外を極力発生させない設計です。
- 設計方針として「ルックアヘッドバイアス防止」が随所に適用されています（target_date 未満のデータ使用等）。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 設定・.env ローダー（Settings）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/execution/
- execution_engine.py — ExecutionEngine（シグナル処理 / push drain）
- order_manager.py — 発注の高レベル API（create/send/sync/cancel）
- order_repository.py — （DB 操作用モジュール）※ファイルはコード内に別途ある想定
- reconciler.py — 再起動時の同期・照合ロジック
- reconciler, risk_manager, broker_factory 等

src/kabusys/monitoring/
- monitoring_db.py — SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常検出
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 管理
- alert_manager.py — LINE Push 管理
- monitoring_engine.py — 各 Monitor を束ねる
- streamlit_dashboard.py — Streamlit UI

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・スコアソート
- position_sizing.py — 株数計算（lot 丸め、aggregate cap）
- risk_adjustment.py — セクターリミット、レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value 等の算出（DuckDB SQL）
- feature_exploration.py — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュース群を OpenAI に送りセンチメントを ai_scores に書き込む
- regime_detector.py — ETF MA + マクロニュースの LLM スコアからレジーム判定

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## よく使うコマンドまとめ

- Monitoring（ポーリング）
  ```bash
  export MONITOR_POLL_INTERVAL=60
  PYTHONPATH=src python src/kabusys/run_monitoring.py
  ```

- Execution（発注）
  ```bash
  export KABUSYS_ENV=paper_trading
  PYTHONPATH=src python src/kabusys/run_execution.py
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

## トラブルシューティング

- .env が読み込まれない／テストで読み込みを避けたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- OpenAI API キーがないと AI 機能（news_nlp / regime_detector）は動作しません。`OPENAI_API_KEY` を設定してください。

- Monitoring／Execution を同一マシンで動かす場合、PID ファイルや kill.flag の配置（Settings のデフォルトパス）に注意してください。

---

必要に応じて README に要件ファイル（requirements.txt）、.env.example、運用手順（systemd / supervisor 用のユニット例）を追加できます。追加要望があれば教えてください。