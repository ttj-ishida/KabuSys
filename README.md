# KabuSys

日本株自動売買システム（モジュール群） — ポートフォリオ構築、発注実行、監視、リサーチ、AI ニューススコアリングなどを含むライブラリ／ランタイムコンポーネント集です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる各種機能を分離したモジュールで提供します。主な目的は以下です。

- ファクター計算や特徴量探索によるリサーチ（DuckDB を用いた履歴データ解析）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制約）
- 発注実行エンジン（ブローカークライアント抽象化、リコンシリエーション、リスク管理）
- 監視／アラート（システム状態・注文状態・リスク監視、LINE 通知、ストリーミングダッシュボード）
- Paper Trading 用の分離された DB と検証レポート生成
- ニュースを LLM（OpenAI）でスコアリングし AI スコアを保存する機能
- 市場レジーム判定（MA とマクロニュースの LLM センチメントを合成）

実装はモジュール化され、テストや実行をしやすいように純粋関数・I/O 層の分離を心がけています。

---

## 主な機能一覧

- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- portfolio
  - 候補選定、等配分・スコア加重配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ算出（リスクベース、単元丸め、aggregate cap）
- execution
  - OrderManager / ExecutionEngine（ブローカー抽象化、リコンシリエーション）
  - Reconciler（起動時リカバリ）
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存確認、データ鮮度確認）
  - TradeMonitor（滞留注文、約定価格異常検出）
  - RiskMonitor（ドローダウン監視、ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine 停止指示）
  - AlertManager（LINE Push 経由のアラート）
  - Streamlit ダッシュボード（監視データ可視化）
- ai
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に格納
  - regime_detector: ETF MA とマクロニュースで日次の市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
- utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- DB
  - monitoring_db: 監視用 SQLite のスキーマ作成・読み書きラッパー（system_status, trade_logs, positions, risk_logs, dashboard）

---

## セットアップ

※ 以下は一般的な Python プロジェクトのセットアップ手順です。requirements.txt / pyproject.toml に合わせて調整してください。

1. Python（3.10+ 推奨）をインストールします。

2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール:
   - pip install -r requirements.txt
   または（パッケージ化されている場合）:
   - pip install -e .

   主に使用される外部ライブラリ:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

4. プロジェクトルートに `.env`（または `.env.local`）を置いて必要な環境変数を設定します（下記「環境変数/設定」を参照）。

5. データディレクトリを作成（必要に応じて）:
   - mkdir -p data

6. DuckDB / SQLite の初期 DB は各スクリプト実行時に必要なテーブルを作成するため、基本的には起動時に自動で作成されます（monitoring の init_monitoring_db 等）。

---

## 環境変数 / 設定（主要）

- KABUSYS_ENV: 起動環境
  - development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録されます

- DB 関連
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- 認証・API
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知をスキップ）

- Execution / Monitoring
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1"で有効）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE: Paper Trading のフィルモード（instant|partial|never|reject、デフォルト: instant）

- 監視閾値（オプション）
  - CPU_THRESHOLD_PCT (default 90.0)
  - MEMORY_THRESHOLD_PCT (default 85.0)
  - DISK_THRESHOLD_PCT (default 90.0)

- ログレベル
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: Settings モジュールはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的なコマンド）

- ExecutionEngine（本番または paper_trading）を起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 SQLite に記録します。
    - 起動時にプロセス優先度を "high" にセットします。

- SystemMonitor（単体ポーリングループ）を起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で周期を上書き可能（秒）。
    - Monitoring は KABUSYS_ENV に関係なく sqlite_path（監視 DB）を使用します。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI ニューススコアリング（プログラムから呼び出し）
  - Python から直接呼べます。例:
    - python -c "import duckdb, datetime, os; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key=os.environ.get('OPENAI_API_KEY')))"

- 市場レジーム判定（プログラムから呼び出し）
  - python -c "import duckdb, datetime, os; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_regime(conn, datetime.date(2026,4,1), api_key=os.environ.get('OPENAI_API_KEY')))"

- 開発／テストでの便利設定
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（テスト時の手間を減らすため）。

---

## 監視とフェイルセーフの挙動（概略）

- SystemMonitor は CPU/メモリ/ディスク 使用率、Execution の PID 存在確認、データ鮮度（prices_daily の最新日）を確認し system_status にログを書きます。PID が stale（死んだ PID）ならファイルを削除して risk_logs に記録します。
- TradeMonitor は滞留注文（一定分以上経過）や約定の価格乖離を検出し risk_logs に記録します。
- RiskMonitor はダッシュボードの portfolio_value を使ってハイウォーターマークとドローダウンを計算し、閾値超過で risk_logs と KillSwitch のトリガーとなります。
- KillSwitch はフラグファイル（data/kill.flag）を書き、ExecutionEngine 側でこれを検出して安全に停止できる仕組みを提供します。
- AlertManager は LINE Push を用いたクールダウン付き通知を行います（設定がない場合はログのみ）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義とバージョン
  - config.py — 環境変数・設定読み込みと Settings
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - ai/
    - news_nlp.py — ニュース NLU スコアリング（OpenAI 用）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と DB ラッパー（MonitoringDB）
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイル駆動の停止機構
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注ワークフロー（状態遷移・DB 永続化）
    - reconciler.py — 起動時の発注 / ポジションのリコンシリエーション
    - （他の execution 関連モジュールは実装の一部がある想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数算出・スケールダウンロジック
  - research/
    - factor_research.py — Momentum/Value/Volatility 等の算出
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

（注）上記はリポジトリの主要ファイル一覧の抜粋です。実際のプロジェクトでは更に data/（DB・PID・フラグファイル等）、docs/、tests/ などが存在するかもしれません。

---

## 注意事項 / 運用上のヒント

- Paper Trading は本番 DB と完全に分離することを想定しています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は monitoring DB（SQLITE_PATH）を参照します。Monitoring は KABUSYS_ENV に依存せず production sqlite_path を使用します（監視は一貫した DB に書き込む設計）。
- OpenAI API を使う処理は外部 API に依存するため、API キーの管理や利用料金に注意してください。API エラー時は多くの箇所でフェイルセーフ（スコア 0.0 にフォールバック等）を実装していますが、適切なログ監視を推奨します。
- プロセス優先度や CPU affinity の設定は権限や OS に依存します。権限不足時は警告ログが出てスキップされます。
- DuckDB / SQLite の接続はスレッドや URI モードなどで挙動が異なるため、複数プロセスでの同時書き込み時は運用で調整してください。

---

もし README に追加したい具体的な情報（インストール方法や要求パッケージ一覧、サンプル .env ファイル、起動例の systemd ユニット例など）があればお知らせください。必要に応じて追記・整形します。