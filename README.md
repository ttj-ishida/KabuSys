# KabuSys

日本株自動売買システムの一部（実行エンジン、監視、リサーチ、ポートフォリオ構築、AI/ニュース処理等）のコードベース。  
本リポジトリには、ExecutionEngine（発注／復旧）、Monitoring（稼働監視／アラート／kill switch）、Research（ファクター計算）、Portfolio（候補選定・配分・株数計算）、AI モジュール（ニュースセンチメント・レジーム判定）、運用ツールが含まれます。

## 主な機能一覧
- Execution
  - 注文作成・送信・状態同期（OrderManager, Reconciler）
  - 実行エンジン起動スクリプト（run_execution.py）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、PID ファイルチェック（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限の監視と kill.flag 発行（RiskMonitor, KillSwitch）
  - LINE による通知（AlertManager）
  - 継続ポーリングや単発実行をまとめた MonitoringEngine、監視用 DB 初期化
  - Streamlit ダッシュボード（監視情報表示）
- AI
  - ニュース記事の LLM によるセンチメントスコア化（kabusys.ai.news_nlp）
  - マクロ＋MA200 を用いた市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API を用いたスコアリング（gpt-4o-mini を想定）
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）計算等の統計ツール
- Portfolio
  - シグナルから候補選定、等金額／スコア加重配分、リスク調整（セクター上限・レジーム乗数）
  - 株数計算（単元丸め、リスクベース、aggregate cap 処理）
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード起動スクリプト

## セットアップ手順（ローカル開発／実行向け）
以下は代表的な手順です。環境に合わせて適宜調整してください。

1. Python の準備
   - Python 3.10+ を推奨（使用モジュールに依存）
   - 仮想環境を作成・有効化することを推奨

2. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil requests openai streamlit
   - SQLite は標準ライブラリで利用可能です

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置けます（自動読み込みあり）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
     - PAPER_FILL_MODE: paper_trading の MockBroker の fill 振る舞い（instant | partial | never | reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: SystemMonitor ポーリング間隔（秒。デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

   - 注意: Settings モジュールは .env/.env.local を自動でロードします（優先順: OS 環境変数 > .env.local > .env）。プロジェクトルートの検出は .git または pyproject.toml を基準とします。

4. データベース初期化
   - Monitoring 用 DB は起動スクリプト実行時に自動でテーブルが作成されます（monitoring_db.init_monitoring_db）。
   - DuckDB に prices_daily / raw_financials 等のテーブルをロードしておく必要があります（Research・AI モジュール用）。

## 使い方（代表コマンド例）
- 実行エンジン起動（本番／開発／paper_trading に応じて KABUSYS_ENV を設定）
  - 本番/開発:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker を利用し data/paper_trading.db に記録）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行スクリプト run_execution.py は起動時にプロセス優先度を "high" に設定し、必要な DB 接続やコンポーネントを組み立てて ExecutionEngine を起動します。Paper Trading モードでは本番 DB と分離され、paper_sqlite_path を使用します。

- 監視ループ起動（SystemMonitor 単体スクリプト）
  - デフォルト 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能）
    python -m kabusys.run_monitoring
  - 監視スクリプトは監視 DB（settings.sqlite_path）へログを書き、PID ファイルの有無やプロセス生存チェック、データ鮮度チェック等を行います。

- Paper Trading 検証レポート出力（CLI）
  - 期間指定・DB パス指定が可能:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- Streamlit 監視ダッシュボード起動
  - 使い方:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- AI モジュールの利用例（Python REPL から関数呼び出し）
  - ニューススコアリング（例）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

  - 注意: OpenAI API 呼び出し時は API キー（OPENAI_API_KEY または引数）を必ず設定してください。API の一時的な失敗に対しては内部でリトライやフォールバック（safe default）する設計です。

## 主要ファイル / ディレクトリ構成
（抜粋。実際のプロジェクトではさらにファイルが存在する可能性があります）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_execution.py              — ExecutionEngine 起動スクリプト（Paper Trading 切替対応）
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite ベースの監視 DB 初期化・読み書き
    - system_monitor.py           — CPU/メモリ/ディスク / PID / データ鮮度チェック
    - trade_monitor.py            — 注文滞留・約定異常チェック
    - risk_monitor.py             — ドローダウン / ポジション上限監視（ダッシュボード更新・risk_logs 登録）
    - kill_switch.py              — kill.flag の書き込みロジック
    - alert_manager.py            — LINE API を使った通知送信（クールダウンあり）
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン（run / run_once）
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - order_manager.py            — 注文ステートマシンの外向き API
    - reconciler.py               — 起動時リコンシリエーション（OrderSent の同期など）
    - (その他 Broker 関連、order_repository 等)
  - portfolio/
    - portfolio_builder.py        — 候補選定・スコア順ソート・等配分／スコア配分
    - position_sizing.py          — 株数計算（単元丸め・risk_based 等）
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py      — 将来リターン計算・IC・統計サマリ等
  - ai/
    - news_nlp.py                 — raw_news を LLM に投げて ai_scores を書き込む
    - regime_detector.py          — マクロ + MA200 によるレジーム判定（DB 書き込み）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI

## 運用上の注意／設計上のポイント
- Settings（config.py）は .env / .env.local を自動で読み込みます。OS 環境変数が優先されます。
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします（権限がない場合は警告が出ます）。
- Monitoring は監視用 SQLite（settings.sqlite_path）を使用します。monitoring_db.init_monitoring_db() によりテーブルは冪等に作成されます。
- Paper Trading モードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 関連（news_nlp, regime_detector）は OpenAI API に依存します。API 呼び出しはリトライ・フェイルセーフを備え、失敗時には安全側の値（例: macro_sentiment=0.0）で継続するようになっていますが、API キーの設定は必須です。
- LINE 通知は channel token / user id が未設定の場合は送信せずログに記録するだけです。重複通知は内部でクールダウン制御されます。
- データ鮮度チェックは DuckDB の prices_daily の最終日を参照します（SystemMonitor）。

## よくある操作例
- 監視 DB の初期テーブルを作成したいとき:
  - 単純に run_monitoring を起動すると init_monitoring_db が走ってテーブルが作成されます
- Paper Trading の検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボードをローカルで確認:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

問題や拡張要望があれば教えてください。README に追加したい設定例 (.env.example)、起動スクリプトの systemd / supervisor 用ユニット例、あるいは各モジュールの API 使用例（コードスニペット）などを追記できます。