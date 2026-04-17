# KabuSys

KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なシステム群です。本リポジトリには、取引エンジン起動・監視ループ・ポートフォリオ構築ユーティリティ・リサーチ / ファクター計算・ニュース NLP（OpenAI）連携などのコンポーネントが含まれます。

---

## 概要

- 自動売買の ExecutionEngine（発注、リスク管理、リコンシリエーションなど）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・セクター上限処理）
- リサーチモジュール（ファクター計算、将来リターン、IC計算など）
- ニュースセンチメント処理（OpenAI を用いたニューススコアリング）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

主要な設計方針として、DuckDB / SQLite をデータ層に使い、外部発注は Broker クライアント経由で抽象化されています。Paper Trading モードでは本番 DB と完全に分離された専用 SQLite を使用します。

---

## 機能一覧

- Execution
  - ExecutionEngine の起動（run_execution.py）
  - Broker クライアント抽象化（本番 / モック切替）
  - リスク管理（最大ポジション比率、利用率、回路遮断など）
  - リコンシリエーション（再起動後の注文・ポジション突合）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス / データ鮮度の監視
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件成立時に停止フラグを書き込み ExecutionEngine に停止シグナルを送出
  - AlertManager：LINE Push を用いた通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio
  - 候補選定（スコア順）
  - 等重 / スコア加重重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン / IC / 統計サマリ
- AI
  - ニュース NLP（OpenAI）による銘柄センチメント集計と ai_scores への保存
  - レジーム判定（ETF MA200 + マクロニュースセンチメント合成）
  - リトライ / バックオフやレスポンス検証などの堅牢化処理
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順

前提
- Python 3.10+（型アノテーションの union 表記等を使用しているため）
- システムに sqlite3 がインストール済み（標準ライブラリ）
- 必要なパッケージをインストール

推奨パッケージ（最低限）:
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード利用時)

例（pip）:
```bash
python -m pip install duckdb psutil openai requests streamlit
```

環境変数 / .env
- Settings クラスはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabus API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定だと送信はスキップ）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE — paper_trading 時のモック約定モード: instant | partial | never | reject
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

データディレクトリ
- 実行時に `data/` 配下に DB ファイルやフラグファイル（kill.flag, stop_requested.flag, execution.pid 等）が作成されます。事前に `mkdir -p data` しておくと良いです。

---

## 使い方（実行例）

1. 環境変数を設定（例）
```bash
export KABUSYS_ENV=development
export OPENAI_API_KEY="sk-..."
export JQUANTS_REFRESH_TOKEN="..."
export KABU_API_PASSWORD="..."
# 必要なら PAPER_TRADING_SQLITE_PATH 等を設定
mkdir -p data
```

2. 監視ループ起動（SystemMonitor を定期実行）
```bash
python -m kabusys.run_monitoring
# 環境変数でポーリング間隔を調整:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- stop: プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが終了します（スクリプトはこのファイルの存在を監視します）。

3. ExecutionEngine 起動（発注エンジン）
```bash
python -m kabusys.run_execution
```
- Paper Trading を使う場合:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- ExecutionEngine は `data/execution.pid` を書き込み、`data/stop_requested.flag` の存在で停止処理を開始します。
- KillSwitch（監視側）が `data/kill.flag` を書き込むと ExecutionEngine 側で停止シグナルとして検出されます。

4. Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db で別のファイルを指定可能:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5. Streamlit ダッシュボード（監視 DB を可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

6. AI 機能（プログラム内から呼び出す例）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 4, 15), api_key="sk-...")
print("written rows:", written)
```
- OpenAI API キーが環境変数 `OPENAI_API_KEY` に設定されていれば api_key 引数は不要です。
- レート制限や一時エラーにはリトライ実装が含まれますが、API 使用量には注意してください。

---

## 運用に関する注意

- Paper Trading モードは本番 DB と完全に分離（`PAPER_TRADING_SQLITE_PATH`）するよう設計されています。切り替え時は `KABUSYS_ENV=paper_trading` を設定してください。
- KillSwitch はドローダウンやポジション上限などの条件で `data/kill.flag` を作成します。`kill.flag` は ExecutionEngine 起動時にオプションで消去する設定があります（Settings.kill_flag_clear_on_start）。
- Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- SystemMonitor は PID ファイルの存在・プロセス存在チェックを行い stale PID を検出・削除します。PID の取り扱いに注意してください。
- AI 関連モジュールは外部 API を呼ぶため、API キー管理、コスト、レート制限に十分注意してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ / パッケージ直下は `src/kabusys` 想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（Settings）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite 保存層（init / MonitoringDB）
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
    - ... (order_repository, execution_engine 等)
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
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (ランタイムで生成される想定)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - kill.flag, stop_requested.flag, execution.pid など

---

## 追加情報 / 開発メモ

- DB スキーマ初期化: run_monitoring / run_execution 起動時に `init_monitoring_db()` が呼ばれ、必要テーブル・マイグレーションが実施されます。
- Process priority: 起動直後に set_process_priority("high") が呼ばれており、psutil による優先度設定を試みます（権限や OS によっては無効になる場合があります）。
- Paper Trading の約定挙動は `PAPER_FILL_MODE` により制御（instant, partial, never, reject）。
- Research モジュールは DuckDB 上の prices_daily / raw_financials 等に依存します。データ整備が必要です。
- テスト時は Settings の自動 .env ロードを無効化したり、OpenAI 呼び出し箇所をモックすることが推奨されます（コード内でその旨を考慮した実装になっています）。

---

必要であれば、README に付け加える内容（例: 具体的な環境変数テンプレート、docker-compose での起動例、各コンポーネントの API ドキュメント）を作成します。どの情報を優先して追加しますか？