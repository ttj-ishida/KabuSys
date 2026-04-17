# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注エンジン、監視、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

## プロジェクト概要
KabuSys は自動売買に必要な以下の機能群を提供するモジュール群です。

- 戦略に基づく銘柄選定・配分・株数決定（portfolio）
- 発注・注文状態管理・再整合（execution）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離された DB 運用
- ニュースを LLM でスコアリングする AI コンポーネント（OpenAI）
- ファクター計算・特徴量探索などの研究用モジュール（research）
- 各種ユーティリティ（プロセス優先度設定など）
- Streamlit による監視ダッシュボード

設計上の留意点：
- .env / .env.local を自動で読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（別 SQLite を使用）
- AI モジュールは OpenAI API キーを必要とする（環境変数または引数で指定）
- 監視は `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）

## 主な機能一覧
- portfolio
  - 銘柄候補選定（スコア順）、等配分・スコア重み配分
  - セクター制約の適用、レジームに基づく投下資金乗数
  - 株数（単元）決定と投下資金スケーリング
- execution
  - ブローカークライアント抽象化（本番 / モック）
  - OrderManager、OrderRepository、ExecutionEngine、Reconciler（再整合）
- monitoring
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / プロセス監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ書き込み）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（上記を束ねたポーリングループ）
  - Streamlit ダッシュボード
- ai
  - news_nlp: raw_news を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に保存
  - regime_detector: ma200 とマクロニュースを合成して market_regime に書き込み
- tools
  - paper_verification_report: Paper Trading の検証レポートを出力

## 必要な依存・ランタイム
- Python 3.9+
- 必要パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- 標準ライブラリ: sqlite3, logging, datetime, threading 等

実行前に仮想環境を作成し、依存をインストールしてください（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

## セットアップ手順（基本）
1. リポジトリをクローン／チェックアウトする
2. 仮想環境を作成して依存をインストール
3. `.env` を作成（下記参照）
4. 初回起動時に DB ファイル（data/*.db）や data ディレクトリが自動作成されます。必要に応じてパスを environment variables で変更。

### 推奨 .env（例）
以下は最低限の主要キー例です（実運用時は安全に管理してください）:
```
KABUSYS_ENV=development            # development | paper_trading | live
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant           # instant | partial | never | reject
LOG_LEVEL=INFO
```

- .env, .env.local は自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

## 使い方（起動方法・主要コマンド）

### 監視ループ（Monitoring）
- 監視用プロセスを起動します（監視は常に settings.sqlite_path を使います。env に依らず本番の sqlite_path を参照する点に注意）。
```bash
python -m kabusys.run_monitoring
```
- ポーリング間隔を変更する場合:
```bash
export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
python -m kabusys.run_monitoring
```
- 停止方法:
  - プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します（run_monitoring・run_execution 両方で参照）。
  - KillSwitch（リスクトリガー）が書き込む `data/kill.flag` は ExecutionEngine 停止のために使用されます。

### 実行エンジン（ExecutionEngine）
- 実トレードまたは paper_trading に応じて ExecutionEngine を起動します。
```bash
python -m kabusys.run_execution
```
- Paper Trading モード:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- Paper Trading は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` を使用します（設定は `PAPER_TRADING_SQLITE_PATH`）。本番 DB と完全に分離されます。
- PID 管理: デフォルトで `data/execution.pid` を使用。起動時に既存の stop flag があれば起動しません。

### Streamlit ダッシュボード
- 監視 DB を read-only で表示する UI（起動例）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### Paper Trading 検証レポート
- Paper Trading の DB を対象に検証レポートを生成します:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

### AI モジュール（ニューススコア / レジーム判定）
- OpenAI API キー（`OPENAI_API_KEY`）が必要です。関数はモジュール関数として呼べます：
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、ai_scores テーブルへ書き込みます。
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込みます。
- 実行時は API 呼び出しのリトライやフェイルセーフ（失敗時は代替値で継続）実装あり。

## 設定（Settings）概要
設定は環境変数経由で行います。主なキーと意味:

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の執行挙動（instant|partial|never|reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒） — run_monitoring で参照
- LOG_LEVEL: ログレベル

Settings クラスは厳密に値検証を行います（不正な値は例外となります）。

## 停止・障害対応
- Graceful stop:
  - `data/stop_requested.flag` を作成すると、run_monitoring と run_execution は検知して停止します。
  - KillSwitch は危険条件を検出すると `data/kill.flag` を書き込み、ExecutionEngine 停止を誘発します。
- Reconciler:
  - 起動時に OrderSent 等の不整合をブローカーと照合して同期を試みます（Reconciler）。
- 監視 DB（monitoring_db）:
  - 初回起動時にテーブルを作成します。マイグレーション（列追加）処理も一部自動で行います（例: peak_value, latency_ms）。

## 開発・テスト用メモ
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の位置）を基準に行われます。CWD に依存しません。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し箇所はテスト容易性のため内部呼び出し関数を patch しやすく設計されています（ユニットテスト時のモック化が想定されています）。
- ユーティリティ `kabusys.utils.process_priority` はプラットフォーム差分（Windows / POSIX）を吸収します。権限不足時は警告を出してスキップします。

## ディレクトリ構成
（主なファイル・モジュールと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py — 株数決定・リスク/単元丸め・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — ma200 + マクロニュースを合成し market_regime に書き込み
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ書き込みユーティリティ
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用 run_once あり）
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py — 発注フローの高レベル API（重複防止等）
    - reconciler.py — 起動時の復旧／照合処理
    - order_repository.py, order_record.py, execution_engine.py, broker_factory 等（発注関連）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（注）上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。

---

この README はコード内の docstring と実装に基づいてまとめています。実際の運用では、秘密情報（APIキー等）を安全に管理し、十分なテストを行った上で本番運用してください。必要があれば README を展開してデプロイ手順や CI、ユニットテストの実行方法、各種設定例（production 用の systemd ユニットなど）を追加します。