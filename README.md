# KabuSys

日本株向け自動売買システムの参照実装 (KabuSys)。  
このリポジトリはシグナル処理、ポートフォリオ構築、注文発注、モニタリング、AIによるニュース/レジーム評価、Paper Trading用の検証ツール等を含むモジュール群で構成されています。

## 主な機能
- 注文管理・発注フロー（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager、ドローダウン・ポジション上限監視）
- 監視コンポーネント（SystemMonitor・TradeMonitor・RiskMonitor）と永続化（SQLite）
- 監視ループ起動スクリプト（run_monitoring.py）
- Execution 起動スクリプト（run_execution.py） — 本番 / Paper Trading 切替対応
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- Streamlit 監視ダッシュボード（monitoring/streamlit_dashboard.py）
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ）
- 研究用モジュール（ファクター計算、将来リターン、IC 等）
- AI モジュール：ニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）
- 設定管理（環境変数と .env 自動読み込み）

---

## 要件
- Python 3.10 以上（typing における `X | Y` 構文を使用）
- ライブラリ（主なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
  - sqlite3（標準ライブラリ）
- DB: DuckDB（時系列・ファクターデータ格納用）および SQLite（監視ログ / Paper Trading 用）

（実際のプロジェクトでは requirements.txt を用意して pip でインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成して依存ライブラリをインストール
3. data ディレクトリ等の作成（必要に応じて）
   ```
   mkdir -p data
   ```
4. 環境変数を設定（.env / .env.local をプロジェクトルートに置くか、OS環境変数で設定）
   - 自動的に .env / .env.local がプロジェクトルートから読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. DuckDB / SQLite のデータファイルパスを設定（デフォルトは data/kabusys.duckdb, data/monitoring.db）

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading の場合、Paper 用 MockBroker + 別 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE: Paper Trading 時の Fill モード（`instant` | `partial` | `never` | `reject`、デフォルト `instant`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするなら `1`
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（パーセンテージ）
- LOG_LEVEL: ログレベル（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）

サンプル .env（例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
```

---

## 使い方（主要コマンド・実行例）

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
```
python -m kabusys.run_execution
```
- Monitoring のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
```
python -m kabusys.run_monitoring
# 例: 30秒間隔にする
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
注意: run_monitoring は監視用 DB（settings.sqlite_path）を用いる。Monitoring は環境にかかわらず本番 sqlite_path を使用します。

- Streamlit ダッシュボード起動（read-only モードで SQLite を開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI モジュール（プログラムから）
  - ニュースセンチメントスコア生成: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  例（簡易）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date.fromisoformat("2026-04-01"), api_key="sk-...")
  ```

---

## 実行時の挙動メモ
- run_execution.py は起動直後に set_process_priority("high") を呼びます（utils/process_priority）。
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
- run_monitoring.py は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックします。
- KillSwitch: risk モニタがトリガー条件を満たした際に kill.flag を書き込み、ExecutionEngine に停止信号を送れる設計です（flag の存在チェック / クリア機能あり）。
- MonitoringDB（SQLite） は init_monitoring_db により必要なテーブルとインデックスを冪等に作成します。既存 DB に対する簡単なマイグレーション（カラム追加）機能あり。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック (.env 自動ロード含む)
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースセンチメント収集 & OpenAI 呼び出しロジック
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層 / MonitoringDB クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE 通知用ラッパー
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注の外向き API（状態遷移管理）
    - reconciler.py — 起動時の注文/ポジションリコンシリエーション
    - （その他 broker, order_repository, risk_manager など多数の実装が想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・尺度調整・単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility ファクター計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発上の注意点 / 備考
- 設定は .env / .env.local / OS 環境変数の順に解決されます（OS 環境変数が最優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- AI 関連は OpenAI API に依存します。API 呼び出しはリトライやフェイルセーフを備えていますが、APIキーがないと該当処理は失敗します（例外またはフォールバック動作）。
- Paper Trading は本番の発注 API を叩かず、専用の DB に記録するため本番データと分離して検証可能です。
- ストリームリットダッシュボードは SQLite を read-only モードで開くことを推奨します（コマンドライン引数 --db で指定）。
- ログ・アラートは設定により LINE へプッシュ通知できます（LINE チャンネルアクセストークンとユーザIDの設定が必要）。

---

この README はリポジトリ内の主要なモジュールをベースにまとめた概要ドキュメントです。各モジュールの詳細な使い方や Broker 実装、ExecutionEngine の設定値等はソースの docstring / コメントを参照してください。必要であればサンプル .env.example、requirements.txt、起動スクリプト（systemd ユニット例）等の追加ドキュメントを作成できます。