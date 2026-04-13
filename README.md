# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。  
本リポジトリには、取引実行エンジン、モニタリング、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）連携などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 取引実行（ExecutionEngine）とブローカー抽象化
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離環境（専用 SQLite）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・リサーチ（DuckDB 上でのファクター計算）
- ニュースの NLP スコアリング（OpenAI API を利用）
- Streamlit ベースの監視ダッシュボード
- 検証レポート生成ツール（Paper Trading 用）

設計方針の一部:
- DuckDB / SQLite を使ったローカルデータベース中心
- 本番と Paper Trading は DB を分離
- 外部 API（OpenAI 等）呼び出しはリトライやフォールバックを持つ設計
- ルックアヘッドバイアスを避けるため日時参照に注意

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（実ブローカー / MockBroker）
  - 注文作成・送信・同期（Reconciler による再起動後の復旧）
  - リスク管理（max position, utilization, circuit breaker など）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文、約定の価格異常検出
  - RiskMonitor：ドローダウン検出、ポジション上限監視
  - KillSwitch：条件により ExecutionEngine 停止フラグ（data/kill.flag）を生成
  - AlertManager：LINE への一方向プッシュ通知
  - Streamlit ダッシュボード（read-only で監視DBを表示）

- Portfolio
  - 候補選定（スコア降順、上位 N）
  - 等重 / スコア重み付け
  - セクター集中制限
  - レジーム乗数（bull/neutral/bear）
  - 単元株丸めを考慮したポジションサイズ計算（risk_based, equal, score）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coef.）計算、統計サマリー

- AI（ニュース）
  - raw_news を集約して OpenAI に投げ、銘柄毎のセンチメントを ai_scores に保存
  - market_regime（ETF + マクロニュース）を判定して保存

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 動作前提 / 依存

- Python 3.10+
- 必要な外部ライブラリ（概ね）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 環境に応じてブローカークライアントの実装（Mock / 実ブローカー）

（requirements.txt があればそれを使用してください。なければ以下例）
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb psutil requests openai streamlit

3. 環境変数を設定
   - プロジェクトルートの `.env` / `.env.local` を作成して設定可能（自動読み込みあり）。
   - 必須（プロダクションで必要なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - その他主要な設定は下節「環境変数一覧」を参照

4. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。
   - 例: mkdir -p data

5. 監視 DB の初期化
   - init_monitoring_db() は各起動スクリプトから自動実行されるため、通常手動作業は不要です。
   - ただし手動で初期化したい場合は Python REPL などから呼び出せます。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: Paper Trading の fill 動作（instant | partial | never | reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化（テスト用）

注意:
- MONITOR_POLL_INTERVAL は正の整数のみ有効。無効値はデフォルト 60 秒にフォールバックします。
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番の監視 DB と分離されます。

---

## 使い方（コマンド例）

- ExecutionEngine 起動（本番 / 開発 / Paper Trading）
  - 本番（env をセット）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き（例: MONITOR_POLL_INTERVAL=30）

- Streamlit ダッシュボード（ローカルで監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベースパスを明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI関連（スクリプト内関数呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を渡して呼び出します。OPENAI_API_KEY が必要です（引数で上書き可能）。

- Kill flag 操作
  - KillSwitch.clear() で `data/kill.flag` を消去（ExecutionEngine 起動時にクリアする設定あり）

---

## 注意点 / 運用上のメモ

- Process priority:
  - run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil 経由）。権限不足等で失敗しても警告ログに留まり処理は続行します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブルとカラムがなければ作成・ALTER を行います（冪等）。

- Paper Trading:
  - Paper Trading は本番 DB と分離され、PAPER_FILL_MODE で約定挙動を制御できます。モードには instant/partial/never/reject があり、無効値は ValueError になります。

- OpenAI 呼び出し:
  - ネットワークエラー・429・タイムアウト・5xx に対しては指数バックオフでリトライします。最終的に失敗した場合はフォールバック（多くはスコア 0.0 や処理スキップ）します。

- ログレベル:
  - Settings.log_level や logging.basicConfig により出力レベルを調整してください。

---

## ディレクトリ構成（主要ファイル / モジュールの説明）

src/
- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定の集中管理（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースの OpenAI によるセンチメントスコアリング（ai_scores への書き込み）
    - regime_detector.py — ETF + マクロニュースを使った市場レジーム判定

  - monitoring/
    - __init__.py
    - monitoring_db.py — monitoring 用 SQLite 永続化層（テーブル定義・CRUD ユーティリティ）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE Push 通知ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード

  - execution/
    - order_manager.py — 注文作成／送信の外向け API（状態遷移管理）
    - reconciler.py — 起動時の注文照合・ポジション照合（再起動復旧）
    - その他（broker_factory, execution_engine, order_repository などは別ファイルに実装）

  - portfolio/
    - __init__.py — 公開 API
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算・単元丸め・aggregate cap

  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - __init__.py
    - process_priority.py — プラットフォーム差分を吸収するプロセス優先度 / CPU affinity 設定

その他:
- data/ — デフォルトの DB / PID / flag を配置する想定（gitignore で除外推奨）

---

## 開発 / テスト時のヒント

- .env の自動ロードはデフォルトで有効です。テストで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB や SQLite の中身を直接参照するときは read-only 接続（URI + mode=ro）でダッシュボードや確認を行うと安全です。
- OpenAI 呼び出し部分はモック化しやすい設計です（内部の _call_openai_api を patch してテスト可能）。
- ポートフォリオ / position sizing 等の関数群は純粋関数として実装されているため単体テストが容易です。

---

必要であれば、README に追記する具体的な env のサンプル (.env.example)、requirements.txt、運用 runbook（systemd / Docker / kubernetes 用）やユニットテストの実行方法も作成します。どれを優先して追加しますか？