# KabuSys

KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリは発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などのモジュールを含みます。設計は本番と Paper Trading（検証）を分離できるようになっており、DuckDB / SQLite を用いたデータ処理と監視ログ永続化を想定しています。

以下はこのコードベースの使い方・セットアップ手順・ディレクトリ構成の説明です。

## 概要（Project overview）
- 自動売買 ExecutionEngine（発注・状態管理・リコンシリエーション）
- Monitoring（システム状態、注文滞留、リスク監視、LINE 通知、kill switch）
- Portfolio Construction（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- Research（ファクター計算、将来リターン・IC、統計サマリー）
- AI モジュール（ニュースのセンチメント分析による ai_scores、マクロニュース + ETF MA によるレジーム判定）
- Tools（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

## 主な機能一覧（Features）
- Settings 管理（.env / .env.local 自動ロード、環境変数アクセス）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、別 SQLite（data/paper_trading.db）へ記録
  - PID ファイル管理、stop フラグ検知で安全停止
- Monitoring 起動スクリプト（run_monitoring.py）
  - 定期ポーリングで system/trade/risk チェックと監視ログ書き込み（monitoring.db）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
  - stop フラグ検知で停止
- Monitoring コンポーネント
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス生存、株価データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止シグナルを発行
  - AlertManager: LINE Push による一方向通知、クールダウン管理
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）
- Portfolio モジュール（候補選定、等金額/スコア配分、リスク調整、ポジションサイズ算出）
- Research（DuckDB を使ったファクター計算、IC、統計サマリ）
- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、ai_scores に書き込む（バッチ・リトライ・検証）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースセンチメントを合成し market_regime を書き込む
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等のレポート出力

## セットアップ手順（Setup）
1. Python 環境
   - Python 3.10+ を推奨
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit（ダッシュボード利用時）
   - （必要に応じて）pytest など
   - インストール例:
     pip install duckdb psutil requests openai streamlit
3. プロジェクトルートに .env を作成（自動ロード）
   - .env.example を参考に必要な環境変数を設定してください。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
4. 主要な環境変数（Settings で参照）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (Paper Trading DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant|partial|never|reject, デフォルト: instant)
     - PID_FILE_PATH, KILL_FLAG_PATH
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|…)
   - OpenAI:
     - OPENAI_API_KEY（AI モジュール利用時）
5. データディレクトリ
   - data/ 以下に SQLite / pid / flag ファイルを置く想定
   - run_* スクリプトは data/stop_requested.flag を見て停止します（手動停止用）

## 使い方（Usage）
- 実行エンジン（発注）
  - 本番想定:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（検証）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使います。
  - 注意: 起動前に data/kill.flag をクリーンにするなどの運用ルールを推奨（Settings.kill_flag_clear_on_start を活用）

- 監視プロセス
  - 監視ループ起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で指定:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV に関わらず）本番の sqlite_path を使用して監視ログを記録します。

- Streamlit ダッシュボード（読み取り専用）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - コマンドライン:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可。

- AI モジュール（プログラムから呼ぶ）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    - OPENAI_API_KEY または引数 api_key が必要
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
  - 注意: OpenAI 呼び出しはリトライ・バックオフなどの処理を含みます。API キー・コストに注意してください。

- 開発・デバッグ
  - Settings は .env/.env.local の自動読み込みを行います（プロジェクトルートの検出は .git または pyproject.toml が基準）
  - 自動ロードを無効化する場合:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 停止フラグ / kill フラグ
  - 監視・実行プロセスは data/stop_requested.flag や data/kill.flag の存在を確認して終了・停止を行います。
  - KillSwitch は条件発生時に data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（冪等）。

## 注意点（Operational notes）
- run_monitoring は MonitoringDB（SQLite）へ永続化します。init_monitoring_db() は必要なテーブル・カラムを作成・マイグレーションします。
- Paper Trading 用 DB は本番 DB と分離されます（settings.is_paper を確認）。
- process_priority を High に設定してから主要処理を起動するため、OS 権限（nice の操作など）によっては設定が失敗する場合があります（ログに警告が出ます）。
- AI モジュールは API 呼び出しで外部通信が発生します。JSON バリデーションやスコアのクリッピング等の安全対策がありますが、API の失敗はフェイルセーフ的に処理される箇所があります。

## ディレクトリ構成（Directory structure）
主要なファイル／モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite ベースの監視 DB（テーブル定義・読み書き API）
    - system_monitor.py      — CPU/メモリ/Disk / データ鮮度 / PID チェック
    - trade_monitor.py       — 注文滞留 / 約定価格異常チェック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE 通知送信とクールダウン管理
    - monitoring_engine.py   — 監視コンポーネントを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（read-only）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py    — （他ファイルあり; 発注ロジック）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_* (関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - data/                   — 実行時に利用する SQLite / DuckDB / pid / flag など（リポジトリに含めないこと推奨）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

## 追加例（.env の例）
例:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

## トラブルシューティング
- DB ファイルが見つからない／開けない:
  - run_monitoring/run_execution 起動時に指定されたパスにファイルがあるか、パーミッションを確認してください。
- OpenAI 呼び出しで例外:
  - API キーが正しいか、ネットワーク／レート制限の状況を確認してください。AI モジュールは一部の失敗でフォールバックしますが、キー未設定は例外になります。
- プロセス優先度の設定失敗:
  - 権限不足（Linux の nice）や未対応 OS の場合は警告が出てスキップされます。

---

必要であれば、以下について詳しいセクション（開発者向けドキュメント、API リファレンス、運用手順、例 .env.example、Dockerfile／systemd ユニット例など）を追加します。どの情報を優先して追加しますか？