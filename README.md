# KabuSys

日本株向け自動売買システムのコアライブラリ群（監視、発注エンジン、ポートフォリオ構築、リサーチ、AI/NLP 補助など）。

このリポジトリはライブラリとしての内部モジュール群を含み、個々のスクリプト／コンポーネントを起動して運用できます。

主な設計方針
- DuckDB / SQLite をデータ層に利用（ローカルファイルベース）
- 本番（live）・ペーパートレード（paper_trading）環境を分離
- 監視（Monitoring）コンポーネントで ExecutionEngine を安全に運用
- AI 呼び出し（OpenAI）を使ったニュースセンチメント／レジーム判定機能を提供
- 可能な限りルックアヘッドバイアスを避ける実装方針

---

## 機能一覧

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク使用率、Execution プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）・約定異常価格検出
  - RiskMonitor: ドローダウン／ポジション上限監視、ダッシュボード更新とリスクログ記録
  - MonitoringEngine: 上記を束ねて定期ポーリング、KillSwitch の評価、LINE 通知支援
  - SQLite ベースの監視ログ（monitoring_db）

- Execution（発注）
  - ExecutionEngine（起動スクリプト含む）: Broker クライアント経由の発注、リスク管理、Reconciler（再起動時の同期）
  - ペーパートレード時は MockBroker を使用し DB を完全分離（data/paper_trading.db）

- ポートフォリオ構築（portfolio）
  - 候補選定、重み付け（等分配／スコア加重）
  - セクター制限、レジーム乗数、ポジションサイズ計算（単元株丸め、投下資金制限）

- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 未来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ai）
  - news_nlp: raw_news を OpenAI で評価し ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースから市場レジーム判定・DB 書き込み

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（成功率、レイテンシ、稼働率等）
  - Streamlit ダッシュボード（監視データ表示）

---

## 前提 / 必要パッケージ

推奨 Python バージョン: 3.10+

主な依存（一例）
- duckdb
- psutil
- requests
- openai (OpenAI SDK)
- streamlit (ダッシュボードを使う場合)

インストール例（仮に requirements.txt がある場合）
```bash
pip install -r requirements.txt
```
個別にインストールする場合:
```bash
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成して依存をインストール
3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（デフォルト動作）。読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数は下記「環境変数」セクション参照
4. data ディレクトリの作成（必要に応じて）
```bash
mkdir -p data
```
5. （オプション）ペーパートレード用 DB 初期化は Execution 起動時に自動で行われます。Monitoring は必要に応じて init_monitoring_db を呼びます。

---

## 環境変数（主なもの）

Settings/モジュール内で参照される主要な環境変数（デフォルト値は Settings ドキュメント参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザー ID（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で true）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — 動作環境（development|paper_trading|live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合、必須）

ランタイム個別:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）。1 秒以上の整数。

---

## 使い方（主要スクリプト）

- 監視ループ起動（監視データを定期記録）
```bash
# デフォルト 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で変更可）
python -m kabusys.run_monitoring
```

- ExecutionEngine 起動（発注エンジン）
```bash
# 通常（development/live）の起動例
python -m kabusys.run_execution

# ペーパートレード（MockBroker を使い、data/paper_trading.db を使用）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- 停止制御: プロセスは data/stop_requested.flag の存在を監視します。停止したい場合はフラグを作成してください（作成済みの場合は起動をスキップする箇所があります）。

- Paper Trading 検証レポート生成
```bash
# デフォルト DB パス: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を明示
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- Streamlit 監視ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI 機能（プログラム内呼び出し）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡します。

---

## 実運用の注意点

- ペーパートレードと本番は DB を明確に分離するよう設計されています（Settings.is_paper 判定を利用）。
- Monitoring は KABUSYS_ENV に依らず本番 sqlite_path（SQLITE_PATH）を使用する実装箇所があります。運用時はその点に注意してください（run_monitoring の docstring を参照）。
- Execution 起動前に `KILL_FLAG_CLEAR_ON_START=1` が設定されていれば起動時に kill.flag をクリアできます。kill.flag が存在するとエンジンを起動しません。
- OpenAI 呼び出しはレート制限やネットワーク障害に対してリトライ実装がありますが、API キーの管理およびコスト管理に注意してください。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル一覧（src/kabusys ベース）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker / Engine / Repository などの実装が想定される）
  - utils/
    - __init__.py
    - process_priority.py

data/ 以下（実行時に生成／使用）
- data/kabusys.duckdb       — DuckDB（デフォルト）
- data/monitoring.db        — 監視用 SQLite（デフォルト）
- data/paper_trading.db     — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading）
- data/execution.pid        — Execution の PID 管理
- data/kill.flag            — KillSwitch による停止フラグ
- data/stop_requested.flag  — run_* スクリプト内で監視している停止フラグ

---

## 開発・テスト時のヒント

- Settings はプロジェクトルートの `.env` / `.env.local` を自動ロードします。テストで自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は外部 API に依存するため、ユニットテストでは _call_openai_api 等の内部関数を patch してモック化してください（モジュール内コメントに記載あり）。
- DuckDB / SQLite クエリはローカルファイルを直接読むため、テスト用のサンプル DB を用意すると良いです。
- process_priority と cpu_affinity の設定はプラットフォーム差（Windows vs POSIX）を吸収する実装ですが、実行権限によっては設定に失敗します（警告ログのみ）。

---

必要に応じて README を拡張して、インストール手順（requirements.txt の明示）、運用手順（systemd / supervisor 用の unit テンプレート）、具体的な DB スキーマ説明や API 使用例を追加できます。追加で欲しい項目があれば教えてください。