# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ＋実行スクリプト）。  
モジュール化されており、発注エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などを含みます。

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群です。

- ExecutionEngine：ブローカーとやり取りして注文を作成・管理・再同期する実行エンジン
- Monitoring：システム資源・データ鮮度・注文状況・リスク（ドローダウン・ポジション上限）を監視しログ／アラートを出す
- Portfolio：銘柄選定、重み計算、ポジションサイジング等のポートフォリオ構築ロジック（純粋関数群）
- Research：DuckDB 上の時系列データからファクター計算・統計解析を行う
- AI：ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボード等

本リポジトリはライブラリとしての利用と、以下の実行スクリプト／ツールを提供します。
- 実行系: run_execution.py
- 監視系: run_monitoring.py
- 検証ツール: tools/paper_verification_report.py
- 監視ダッシュボード: monitoring/streamlit_dashboard.py

---

## 主な機能一覧

- 監視（Monitoring）
  - CPU / メモリ / ディスクのモニタリング
  - Execution プロセス生存確認（PID ファイル）
  - データ鮮度チェック（DuckDB 上の最終価格日付）
  - 注文滞留・約定価格異常検出
  - ドローダウン・ポジション上限監視、kill.flag による Execution 停止シグナル
  - LINE へのプッシュ通知（AlertManager）

- 実行（Execution）
  - ブローカークライアントの抽象化（本番 / paper_trading 用 Mock 分離）
  - OrderManager / OrderRepository による注文状態管理
  - 起動時のリコンシリエーション（Reconciler）

- ポートフォリオ構築
  - 候補抽出（スコア順、上限指定）
  - 等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイジング（リスクベース・等分配・スコアベース）、単元丸め、aggregate cap

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリ

- AI（OpenAI）
  - ニュース記事の銘柄ごとセンチメントを LLM で算出して ai_scores に書き込み
  - マクロ記事＋ETF MA200 比から市場レジーム（bull/neutral/bear）を判定

- ツール
  - Paper Trading 検証レポート（成功率・稼働率・レイテンシ等）
  - Streamlit ベースの監視ダッシュボード

---

## 前提 / 必要環境

- Python 3.8+（typing の未来仕様を使用、3.10+ 推奨）
- SQLite（Python 標準ライブラリ sqlite3）
- DuckDB（python duckdb パッケージ）
- psutil（プロセス優先度 / CPU affinity / リソース取得）
- requests（LINE 通知）
- openai（OpenAI クライアント）
- streamlit（ダッシュボードを使用する場合）

例（最低限のインストール）:
```
pip install duckdb psutil requests openai streamlit
```
プロジェクトに requirements.txt があればそれを使ってください。

---

## セットアップ手順（ローカル開発 / 簡易）

1. リポジトリをクローンし、作業ディレクトリに移動
2. 仮想環境を作成・有効化（任意）
3. 依存パッケージをインストール（上記参照）
4. data ディレクトリを作成
```
mkdir -p data
```
5. 必要な環境変数を設定（下節を参照）または .env をプロジェクトルートに作成
6. DuckDB / SQLite のデータファイルはスクリプト実行時に自動作成・テーブル生成処理が入る箇所があります（例：init_monitoring_db）

---

## 主要な環境変数（Settings に基づく）

（.env / OS 環境変数で設定）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants トークン（使用モジュールがある場合）
- KABU_API_PASSWORD — kabuステーション API 用パスワード

推奨 / 任意（デフォルトあり）:
- KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、MockBroker を使用し DB は data/paper_trading.db に分離
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH — DuckDB データファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject、デフォルト: instant）
- PID_FILE_PATH — execution PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアするなら "1"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード:
- プロジェクトルートで .env / .env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

例（.env の最小例）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
JQUANTS_REFRESH_TOKEN=...
```

---

## 使い方（起動・主要コマンド）

注意: パッケージが `src` 配下にある想定です。PYTHONPATH を適切に設定するか、プロジェクトルートで `python -m` で実行してください。

- 監視ループを起動（SystemMonitor をポーリングして SQLite にログを保存）
```
# プロジェクトルートで
PYTHONPATH=src python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL 環境変数で秒間隔を上書き可能
MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
```
run_monitoring は起動時にプロセス優先度を "high" に設定し、MonitoringDB を初期化します。停止は data/stop_requested.flag ファイルを作成するか Ctrl+C。

- ExecutionEngine を起動（ブローカーと接続して注文処理を実行）
```
PYTHONPATH=src python -m kabusys.run_execution
```
KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録します。停止は data/stop_requested.flag を作成するか Engine 内の KillSwitch により kill.flag が作成されると停止します。

- Paper Trading の検証レポート生成
```
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit ダッシュボード（監視 DB の可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ライブラリ API の利用例（Python スクリプト内で）
```python
from kabusys.ai import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026, 4, 15), api_key="sk-...")
```
score_regime（レジーム判定）や research モジュールも同様に DuckDB 接続を渡して利用します。

---

## 停止 / 制御ファイルについて

- data/stop_requested.flag — run_monitoring / run_execution のループで監視される停止フラグ（存在すれば起動中のループは終了）
- data/kill.flag — KillSwitch が作成するファイル。ExecutionEngine 停止を指示するために作成される（存在すると Execution の起動を拒否するなどの制御に使われる）
- data/execution.pid — ExecutionEngine が自身の PID を書き込むファイル。SystemMonitor はこの PID を見てプロセス生存を判定する

---

## ディレクトリ構成（主要ファイル説明）

（src 配下の kabusys パッケージがルート）

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / 設定読み込み（.env 自動ロード含む）、Settings クラス
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP による銘柄ごとのセンチメント算出（OpenAI 呼び出し）
    - regime_detector.py — マクロ + ETF MA200 による市場レジーム判定（OpenAI 呼び出し）
  - monitoring/
    - monitoring_db.py — SQLite の監視用テーブル初期化と簡易 DB API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留／約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の読み書きロジック
    - alert_manager.py — LINE への通知
    - monitoring_engine.py — 各 Monitor を束ねる Engine
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — Order 管理ロジック（State Machine）
    - reconciler.py — 起動時の注文／ポジション照合
    - （その他：broker_factory, execution_engine, order_repository 等が存在する想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・制約処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 実行時の注意点 / 運用上のポイント

- KABUSYS_ENV の設定により本番 / paper_trading が切り替わります。paper_trading は実ブローカーと分離された専用 DB を使用するため、検証用途に便利です。
- run_monitoring は MonitoringDB（SQLite）の初期化を行います。既存 DB に対するマイグレーション処理も含まれます。
- AI（OpenAI）を利用する機能は API キーが必要です。API 呼び出しはリトライやフェイルセーフが実装されていますが、コストとレート制限に注意してください。
- process_priority（高優先度設定）や CPU affinity 設定は psutil を使います。アクセス権限やプラットフォーム差異により実行できない場合は警告でスキップされます。
- kill.flag / stop_requested.flag 等のフラグファイルは運用スクリプトや CI で扱うことを想定しています。作成・削除は冪等で扱ってください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことを推奨します（起動時に read-only URI を使う例を参照）。

---

## 参考コマンドまとめ

- 監視起動:
  MONITOR_POLL_INTERVAL=60 PYTHONPATH=src python -m kabusys.run_monitoring

- 実行エンジン起動:
  PYTHONPATH=src python -m kabusys.run_execution

- Paper 検証レポート:
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、この README をベースに以下も作成できます：
- .env.example（推奨設定例）
- requirements.txt（実際の依存関係一覧）
- 運用手順書（起動／停止／フラグ運用、ローテーション、ログ管理）
- デプロイ手順（systemd / Docker / Kubernetes の Unit / Container 化）