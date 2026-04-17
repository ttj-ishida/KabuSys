# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）です。本リポジトリは注文発行・実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ・ファクター計算、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。設計方針として「本番データアクセスを含まない研究系モジュール」「環境変数による設定」「SQLite / DuckDB を利用した永続化」といった点を重視しています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（主なもの）
- 使い方
  - ExecutionEngine（取引実行）の起動
  - Monitoring（監視）ループの起動
  - Streamlit 監視ダッシュボード
  - Paper Trading 検証レポート生成
  - AI モジュール（ニューススコアリング / レジーム判定）
- ディレクトリ構成（主要ファイルと説明）
- 運用上のメモ / 注意点

---

## プロジェクト概要

本プロジェクトは日本株自動売買の各機能をモジュール化した Python パッケージです。主な役割は次のとおりです。

- シグナルを受け取り、ブローカー API 経由で発注（ExecutionEngine / OrderManager）
- 発注履歴・監視ログを SQLite に保持し、監視ループでシステム状態を記録（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- DuckDB を用いた価格データ・財務データに対するファクター計算・リサーチ
- OpenAI を使ったニュースセンチメント評価と市場レジーム判定
- Streamlit による監視ダッシュボード、ツールスクリプトによる検証レポート出力

---

## 機能一覧

- Execution
  - ExecutionEngine（注文発行・実行管理）
  - Broker クライアント抽象化（paper_trading 時は MockBroker を使用）
  - Reconciler による起動時の注文同期とポジション照合
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス状態 / データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検知）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（リスク発生時にフラグファイルで Execution を停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（上記を束ねるループ）
  - Streamlit ダッシュボード表示
- Portfolio
  - 候補選定、等重/スコア重み付け、セクター制限、ポジションサイズ計算（単元丸め、リスク制約）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを生成して ai_scores に書き込む
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM スコアを合成しレジーム判定・永続化
- Tools
  - paper_verification_report: Paper Trading DB の指標を集計して PASS/FAIL 判定を出力

---

## セットアップ手順（ローカル開発用）

前提:
- Python 3.9+（コードは型ヒント等を使用）
- Git, SQLite (標準), インターネット接続（OpenAI API を利用する場合）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （実行環境に合わせて他のパッケージが必要になる場合があります）

4. データディレクトリを用意
   - mkdir -p data

5. 環境変数 / .env
   - プロジェクトルートの `.env` / `.env.local` を用いて環境を設定できます。
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須のキーの例は次節「環境変数」を参照してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース / レジーム機能で必須）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 送信）用
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START：監視/停止フラグに関する設定

注意: Settings モジュールは自動的に .env / .env.local をプロジェクトルートから読み込みます（必要に応じて環境変数で上書き可）。

---

## 使い方

### ExecutionEngine（取引実行）の起動
- 実行コマンド:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、`data/paper_trading.db` を使用して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するとループが検知して停止します。
  - 起動時に `data/execution.pid` に PID を書きます（プロセスの stale PID 検出機能と連携）。

### Monitoring（監視）ループの起動
- 実行コマンド:
  - python -m kabusys.run_monitoring
- 動作:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - system / trade / risk 各モニタを実行し、監視結果を SQLite（settings.sqlite_path）に永続化します。
  - 危険条件により `data/kill.flag` を書き込み、ExecutionEngine を停止する仕組み（KillSwitch）があります。

### Streamlit 監視ダッシュボード
- 起動コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 概要:
  - ダッシュボードでダッシュボード集計、ポジション、注文履歴、最新のシステム状態、リスクログなどを可視化します。
  - SQLite DB を read-only モードで開きます（MonitoringEngine が DB を更新中でも参照可能な場合があります）。

### Paper Trading 検証レポート生成
- 実行コマンド例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL を表示します。

### AI モジュール
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（raw_news / news_symbols / ai_scores テーブルが必要）を渡すことで、指定日のウィンドウ記事を集約して OpenAI に投げ、ai_scores テーブルへ書き込みます。
  - OPENAI_API_KEY が必要（api_key 引数で明示も可）。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）MA とマクロニュースを合成して market_regime テーブルに書き込みます。
  - OPENAI_API_KEY が必要（フェイルセーフで失敗時は macro_sentiment=0.0 として継続）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings の読み込み
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体起動スクリプト（シンプルなポーリング）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py — 発注の外向き API（状態遷移管理）
    - reconciler.py — 起動時の照合・自己回復
    - ...（BrokerFactory / ExecutionEngine / OrderRepository 等、発注関連）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite スキーマ + DB アクセサ
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE 通知ラッパ
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・リスク制約）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュース集約 + OpenAI でスコア化
    - regime_detector.py — マクロ + ETF MA によるレジーム判定
  - utils/
    - process_priority.py — psutil を用いたプロセス優先度 / CPU affinity 設定
  - data/ (ランタイムで使用することが想定されるディレクトリ)
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（DuckDB ファイル）
    - stop_requested.flag, kill.flag, execution.pid などのフラグ/メタファイル

---

## 運用上のメモ / 注意点

- プロセス優先度設定:
  - utils/process_priority.py は psutil を使用し、Windows / POSIX を吸収しますが権限（nice 値変更など）により失敗する場合があります。失敗時は警告が出てスキップされます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成／簡易マイグレーション（カラム追加）を行います。
- フラグファイル:
  - stop_requested.flag（run_* スクリプトが監視）や kill.flag（KillSwitch が作成）を使ってプロセス間シグナルを渡します。これらのファイルを直接編集/作成/削除することで運用操作が可能です。
- OpenAI API:
  - AI 機能は OpenAI を利用します。API 呼び出しはリトライ・バックオフやレスポンス検証を実装していますが、API キーの管理・コストに注意してください。
- Paper Trading:
  - paper_trading 環境では実際の注文は送信されません。専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB とは完全に分離されます。
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git / pyproject.toml を探索）を基準に .env / .env.local を自動ロードします。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば、README にサンプル .env.example や実行時のログ例、より詳細な API 仕様（OrderRequest / BrokerAPIProtocol）やユニットテストの実行方法を追加できます。どの情報を優先して追加しますか？