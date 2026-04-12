# KabuSys

日本株自動売買システムの軽量実装。価格データやファクター計算、ポートフォリオ構築、発注実行、監視、AI を使ったニュースセンチメント評価などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を持つモジュール群です。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター上限適用）
- 発注エンジン（ブローカー抽象化、OrderManager、ExecutionEngine、再起動時のリコンシリエーション）
- 監視（プロセス監視、データ鮮度、注文滞留、リスク監視、アラート送信）
- AI（OpenAI）連携によるニュースセンチメント評価 / レジーム判定
- 各種ユーティリティ（プロセス優先度設定、.env ローダー等）
- 開発/検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

このリポジトリは純粋関数ベースの計算モジュールと、軽量な永続層（SQLite / DuckDB）を組み合わせた設計になっています。

---

## 主な機能一覧

- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- portfolio
  - 候補選定（スコア順）、等配分 / スコア加重、リスクベースの株数決定
  - セクターキャップ適用、レジーム乗数算出
- execution
  - Broker 抽象化（本番 / モック切替）
  - OrderManager（状態遷移、DB 永続化）、Reconciler（起動時リコンシリエーション）
  - RiskManager、OrderRepository（SQLite）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine（ポーリング統合）、AlertManager（LINE push）
  - kill switch（data/kill.flag による Execution 停止）
  - Streamlit ダッシュボード（監視用）
- ai
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄別スコアを書き込む
  - regime_detector.score_regime: ETF MA 乖離 + LLM マクロセンチメントで市場レジーム判定
- tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力

---

## セットアップ手順

前提: Python 3.10+ を推奨

1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone ... && cd <repo>

2. 依存ライブラリをインストール
   - 簡易例:
     - pip install duckdb psutil requests openai streamlit
   - 実プロジェクトでは requirements.txt / Poetry 等を用意してください。

3. データディレクトリを作成
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring (SQLite): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 例:
     - mkdir -p data

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主要な環境変数（例）:
   - KABUSYS_ENV=development | paper_trading | live
     - paper_trading の場合、本番 DB と分離して `PAPER_TRADING_SQLITE_PATH` を使用
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...         （AI 機能を使う場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant | partial | never | reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO

5. 必要に応じて権限設定
   - プロセス優先度変更（set_process_priority）は OS によって権限が必要な場合があります。失敗時は警告ログでスキップされます。

---

## 使い方

主要な起動スクリプトはパッケージ経由で実行できます（`src/` 配下を PYTHONPATH に含めるか、パッケージをインストールしてください）。

- ExecutionEngine を起動（本番/ペーパートレードを切替）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録されます。

- Monitoring のポーリングを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定できます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きダッシュボードを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 出力: 標準出力に指標と PASS/FAIL 判定を表示します。

- AI 関連（コードから関数を呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を参照・更新します。api_key が None の場合は環境変数 OPENAI_API_KEY を参照。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - prices_daily / raw_news を参照して market_regime テーブルに結果を書き込みます。

注意点:
- ExecutionEngine と Monitoring はそれぞれ PID ファイル（Settings.pid_file_path）を参照してプロセス存在チェックや kill flag の判定を行います。
- Monitoring 側には KillSwitch があり、一定のリスク（ドローダウン・ポジション上限等）に達すると data/kill.flag を書き込み、Execution 側が検出して停止する設計です。

---

## 主要な設定（Settings から参照される主な環境変数）

- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数ロード・Settings 定義（.env 自動ロード機能含む）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV によるブローカー切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py           — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py    — MA 乖離 + マクロセンチメントでレジーム判定
- monitoring/
  - monitoring_db.py      — SQLite スキーマ初期化 / 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py      — LINE 送信
  - monitoring_engine.py  — Monitors を束ねるポーリングエンジン
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - （その他ブローカー関連・実行エンジン等が存在）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py

（上記は抜粋です。実際のファイル群は src/kabusys 以下をご参照ください。）

---

## 運用上の注意 / ヒント

- Paper Trading モードは本番 DB と分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。安全に検証できます。
- OpenAI API 呼び出しは外部ネットワーク依存のため、失敗時はフェイルセーフ（0.0 などにフォールバック）して処理を継続する実装になっていますが、コストとレート制限に注意してください。
- process priority / CPU affinity の設定はプラットフォーム依存で権限エラーが発生する場合があります。ログで警告が出たら設定を確認してください。
- .env のパースはシェル風のフォーマットをサポートします（'export KEY=val'、クォート、インラインコメント等）。
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング秒数（デフォルト 60 秒）を上書きします。不正な値は無視されデフォルトにフォールバックします。

---

この README はコードベースから抽出した情報をもとに作成しています。実際の運用や拡張時は各モジュールのドキュメント（ソース内 docstring）を併せて参照してください。問題や追加の説明が必要であれば教えてください。