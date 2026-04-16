# KabuSys

日本株向け自動売買システム（ライブラリ兼軽量実行コンポーネント群）。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・検証・研究用ユーティリティを含むモジュール群を提供します。実運用（live）・ペーパートレード（paper_trading）・開発（development）環境を想定しています。

---

## プロジェクト概要

主な目的は「安全性を重視した日本株アルゴリズム売買システム」の基盤実装です。以下の責務を持つコンポーネントで構成されています。

- ExecutionEngine（発注・リスク管理・再同期）
- Monitoring（システム状態・注文状態・リスク監視、LINE 通知、kill switch）
- Portfolio construction（候補選定、重み・株数決定、セクター制約）
- Research（ファクター計算、IC 計算、特徴量探索）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- Tools（ペーパートレードの検証レポート、Streamlit ダッシュボード）

---

## 機能一覧

- Execution
  - ブローカークライアント（実アダプタ／モックを環境に応じて切替）
  - OrderManager / OrderRepository による状態管理
  - Reconciler による起動時の自動復旧・ポジション差分検出
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、PID ファイル監視）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（データ/フラグに基づく ExecutionEngine 停止）
  - AlertManager（LINE Push による通知・クールダウン管理）
  - MonitoringEngine（上記を束ねたポーリングループ）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定（スコア降順／タイブレーク）
  - 重み付け（等金額・スコア加重）
  - セクター上限の適用
  - position sizing（risk-based / equal / score、単元株丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン、IC、統計サマリー、ランク変換
- AI（OpenAI）
  - ニュースを集約して銘柄別センチメントを ai_scores に書込
  - マクロニュース＋ETF MA200 を使った日次レジーム判定
  - API 呼び出しは冪等性・リトライ・フェイルセーフを考慮
- Tools
  - paper_verification_report: ペーパートレード DB からレポート生成
  - streamlit_dashboard: 監視 DB の可視化

---

## 必要条件

- Python 3.9+
- 主な依存ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（OS に同梱）
- ネットワーク（OpenAI／LINE API を使用する場合）

依存は pyproject.toml / requirements.txt がある場合はそちらを利用してください（本コードベースでは省略）。

例（簡易）:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存インストール
   - pip install -r requirements.txt
   - あるいは必要なパッケージを個別に pip install
4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

推奨する .env の例:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant

注意:
- 自動ロードはプロジェクトルートを .git や pyproject.toml で探索して行います。
- 必須環境変数に未設定があると Settings プロパティで ValueError が発生します。

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連オプション
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - 無効な値や 0/負数はデフォルトにフォールバックします。

---

## 実行方法（主要な CLI）

- 監視ループを起動（監視 DB に書き込み）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 実行中にプロジェクト/data/stop_requested.flag が作成されるとループが終了します（停止フラグ機構）。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録して本番 DB と分離します。
  - 実行中に data/stop_requested.flag または data/kill.flag による停止が可能です。
  - 実行は別スレッドで engine.run_session が動作します。PID ファイルを data/execution.pid に書きます。

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

- AI / レジーム判定・ニューススコアのプログラム的利用
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
  - conn は duckdb.connect(...) で得た接続を渡す

---

## 注意事項 / 運用メモ

- Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
- ExecutionEngine は paper_trading 環境であればペーパーデータベースを使用します（Settings.paper_sqlite_path）。
- KillSwitch は RiskMonitor の判定により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine 起動時は KILL_FLAG_CLEAR_ON_START オプションでクリア可）。
- プロセス優先度設定（set_process_priority）は OS に依存し権限が必要な場合があります。失敗時は警告ログに留まり、正常動作は継続します。
- OpenAI / LINE など外部 API 呼び出しはネットワーク/料金が発生します。API キー・トークンは適切に管理してください。
- DuckDB を使った研究モジュールは prices_daily / raw_financials / raw_news などのテーブルを前提とします。データ準備は別途必要です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとして抜粋）

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py                    — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                     — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py       — ペーパートレード検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py                   — SQLite テーブル作成 / MonitoringDB API
    - system_monitor.py                  — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py                   — 注文滞留・約定異常検出
    - risk_monitor.py                    — ドローダウン / ポジション上限監視
    - kill_switch.py                     — kill.flag の書き込み・評価
    - alert_manager.py                   — LINE 通知（クールダウン）
    - monitoring_engine.py               — 各 Monitor を束ねるループ
    - streamlit_dashboard.py             — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (その他 Broker/Engine 関連)
  - portfolio/
    - portfolio_builder.py               — 候補選定、重み計算
    - position_sizing.py                 — 株数計算・リスク制限
    - risk_adjustment.py                 — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py                 — Momentum/Volatility/Value ファクター
    - feature_exploration.py             — 将来リターン / IC / 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py                        — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py                 — レジーム判定（ETF ma200 + LLM）
    - __init__.py
  - utils/
    - process_priority.py                — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（補足）
- data/ 配下に DB / PID / フラグファイルを置く想定（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 開発者向け補足

- Settings クラスはプロパティアクセスで環境変数を検証します（無効値は ValueError）。
- DuckDB 経由の研究モジュールは SQL により集計しており、テーブルスキーマに依存します。
- AI 機能はレスポンスの検証やリトライ・フェイルセーフを重視しています。テストでは API 呼び出し関数をモックする設計になっています（_call_openai_api を patch）。

---

## よく使うコマンド例

- 監視を 30 秒間隔で実行:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレードで Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ペーパートレード検証レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README のサンプル .env や systemd/起動スクリプトの例、CI 用のテスト手順、DB スキーマ定義（DuckDB / SQLite の初期化手順）なども追加できます。どの情報を優先して追加しますか？