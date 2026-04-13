# KabuSys

日本株向け自動売買プレイグラウンド / 監視・検証ツール群

このリポジトリは、簡易的な自動売買実行エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・研究用ファクター計算・AI を使ったニュースセンチメント評価などを含むモジュール群です。設計方針は「本番ロジックとリサーチロジックの分離」「ルックアヘッドバイアスを防ぐ」「外部 API 呼び出しは明示的に制御する（環境変数でキーを渡す）」ことにあります。

## 主な機能

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 注文管理（OrderManager / OrderRepository）
  - Reconciler による起動時リコンシリエーション
  - paper_trading モード（MockBrokerClient、専用 SQLite DB で分離）
- Monitoring
  - System / Trade / Risk 各種モニター（SystemMonitor / TradeMonitor / RiskMonitor）
  - MonitoringEngine によるポーリングループ
  - monitoring DB の永続化（SQLite）
  - streamlit ダッシュボード（streamlit_dashboard.py）
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE 通知（AlertManager）
- Portfolio construction
  - 候補選定・重み付け（等分配・スコア重み）
  - セクター上限適用・レジーム乗数
  - 株数算出（ロット丸め・利用可能現金に応じたスケーリング）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（forward returns / IC / summary）
- AI（OpenAI）
  - ニュース記事のセンチメント解析 → ai_scores への書き込み（news_nlp.py）
  - マクロ + MA200 からの市場レジーム判定（regime_detector.py）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提・依存パッケージ

主な依存（抜粋）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード起動時)
- sqlite3（標準ライブラリ）
- その他テスト・開発用パッケージがある場合があります

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1 など
python -m pip install --upgrade pip
python -m pip install duckdb psutil requests openai streamlit
```

もし requirements.txt を用意している場合:

```bash
python -m pip install -r requirements.txt
```

---

## 設定と環境変数

このプロジェクトは .env / .env.local から環境変数を自動読み込みします（ただし OS 環境変数が優先されます）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（デフォルト値や説明）:

- KABUSYS_ENV: 起動環境
  - 有効値: `development`（デフォルト）, `paper_trading`, `live`
  - `paper_trading` の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE: paper_trading の約定挙動（`instant` / `partial` / `never` / `reject`、デフォルト `instant`）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 関連
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE Push 通知（AlertManager）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: `data/kill.flag`）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。run_monitoring のデフォルトは 60 秒。環境変数で上書き可能。
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアする（`1` で有効）

注意:
- Monitoring（run_monitoring.py）は KABUSYS_ENV にかかわらず本番の sqlite_path を使って監視ログを記録します（監視 DB は環境に依存しない設計）。
- Paper Trading 実行（run_execution.py）では `KABUSYS_ENV=paper_trading` の場合に paper 用 DB に切り替えます（本番 DB と完全分離）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
3. 必要な環境変数を .env または環境に設定（.env.example を参照）
   - 特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須設定がある箇所があります
4. データディレクトリの準備
```bash
mkdir -p data
```
5. （任意）DuckDB / SQLite DB を準備（初回は各種スクリプトが必要に応じてテーブルを初期化します）

---

## 実行例（使い方）

- 監視ポーリングループを起動（Monitoring）
```bash
# デフォルト: ポーリング 60 秒 (環境変数 MONITOR_POLL_INTERVAL で上書き可)
python -m kabusys.run_monitoring
# 例: 30 秒間隔
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジンを起動（Execution）
```bash
# production / development（デフォルト）
python -m kabusys.run_execution

# Paper Trading モード（MockBrokerClient を使用し、data/paper_trading.db に記録）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- streamlit ダッシュボードを起動（監視 DB を可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート（ツール）
```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。モジュール関数として呼び出します。

例（Python から直接呼び出す）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# ニューススコア（target_date のウィンドウを基にスコア付与）
score_news(conn, date(2026, 4, 1), api_key="sk-...")

# レジーム判定（market_regime テーブルへ書き込み）
score_regime(conn, date(2026, 4, 1), api_key="sk-...")
```

---

## 重要な設計上の注意点 / 備考

- .env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して行われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の DB 初期化は init_monitoring_db() により冪等に行われます。初回起動時のテーブル作成やマイグレーション（列追加）を内部で行います。
- ExecutionEngine 起動時はプロセス優先度を可能な限り High にセットする試みを行います（プラットフォーム差分を吸収するユーティリティを利用）。権限不足等で失敗してもエラーにはなりません。
- kill.flag（デフォルト: data/kill.flag）は ExecutionEngine 停止のトリガーとして使用します。KillSwitch によって書き込まれます。ExecutionEngine 側で起動時にこれをクリアする設定があります（Settings.kill_flag_clear_on_start）。
- Paper Trading は本番 DB と分離して動作するよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI（LLM）呼び出しは外部 API に依存するため、API の失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続する設計です。API キーは明示的に渡すか環境変数で設定してください。
- DuckDB を使った研究（research）モジュールは prices_daily / raw_financials 等のテーブルに依存します。データ準備は別途行ってください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み込みロジック（.env 読み込み、Settings クラス）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化（init / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor をまとめる
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — kill.flag 制御
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文作成・送信ロジック
    - reconciler.py — 再起動時の自動復旧ロジック
    - （その他: broker_factory / execution_engine / order_repository 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング・ロット丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary 等
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

---

## 開発者向けメモ

- 各モジュールは「DB 参照部（DuckDB / SQLite）」と「純粋関数部（ポートフォリオ計算等）」で分離されています。ユニットテストを書く際は純粋関数を優先してテストしてください。
- LLM 呼び出し部分は内部でラップされており、テスト時は該当関数（_call_openai_api 等）を patch して外部依存を切り離せます。
- MonitoringEngine.run_once() は単発実行テスト用インターフェースを提供しています（ループを回さず監視処理を一度だけ実行）。

---

この README はコードベースの主要ポイントをまとめたものです。詳細な実装や追加のユーティリティ、API の使い方はソースコード内の docstring / コメントを参照してください。質問や追記してほしい項目があれば教えてください。