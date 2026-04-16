# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム KabuSys のコアライブラリ群です。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行、監視・アラート、Paper Trading 用ツールや AI 補助機能を含んでいます。

以下はコードベースの概要、機能一覧、セットアップ手順、主要な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームで、主に次を提供します：

- ファクター計算・特徴量探索（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数決定）
- 注文管理とブローカー連携（ExecutionEngine、OrderManager、Reconciler）
- 監視・アラート（system/trade/risk の監視、LINE で通知）
- Paper Trading（本番 DB と分離）および検証ツール
- ニュース NLP による銘柄センチメント評価 / 市場レジーム判定（OpenAI 経由）
- Streamlit ダッシュボードによる監視 UI

設計方針の一部：
- DuckDB / SQLite をデータ層に使用（ローカルで高速集計）
- ランタイム設定は環境変数経由（.env 自動ロード対応。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD にて無効化可能）
- Paper Trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）

---

## 主な機能一覧

- research/
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC 計算・統計サマリー
- portfolio/
  - 候補選定（select_candidates）
  - 等比率 / スコア重み付け（calc_equal_weights, calc_score_weights）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め・aggregate cap）
- execution/
  - OrderManager, ExecutionEngine, Reconciler（再起動復旧）
  - Broker クライアント抽象化（本番 / Paper 用）
- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor（DB へログ永続化）
  - MonitoringEngine（ポーリングループ）、AlertManager（LINE push）
  - KillSwitch（条件に応じて data/kill.flag を作成して ExecutionEngine を停止）
  - Streamlit ダッシュボード（読み取り専用）
- ai/
  - news_nlp: OpenAI を使った記事ごとの銘柄センチメントを ai_scores に書き込み
  - regime_detector: ma200 + マクロニュースで市場レジーム判定
- tools/
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL レポート出力

---

## 依存関係（代表例）

このリポジトリは少なくとも Python 3.10 以上を想定しています（型アノテーション `X | Y` を使用）。

主な Python ライブラリ：
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例：
- pip install duckdb psutil requests openai streamlit

（実プロジェクトでは requirements.txt / Poetry 等で依存管理してください）

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロードはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

重要な環境変数（Settings クラスに基づく）：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: Kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 関係で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定振る舞い（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読込を無効化

注意:
- Monitoring（監視）は KABUSYS_ENV に関わらず sqlite_path（本番監視 DB）を使用して永続化します。
- Paper Trading 起動時は settings.is_paper が True の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし Python 環境を用意する（pyenv / venv 等）。
2. 依存ライブラリをインストール（上記参照）。
3. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定する。
   - 例（最低限）:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
4. データディレクトリを作成:
   mkdir -p data
5. 必要に応じて DuckDB / SQLite のテーブルを用意する（多くの初期化はコード側で行われます。例: init_monitoring_db() が monitoring DB のテーブルを作成します）。

---

## 使い方（主要スクリプト & コマンド）

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - プロセス優先度を "high" に設定（utils.process_priority）
    - Settings から sqlite_path を読み監視用 DB に接続
    - Monitoring 用 DB スキーマがなければ init_monitoring_db が生成
    - SystemMonitor の check_once を定期実行（MONITOR_POLL_INTERVAL 秒、デフォルト 60）
    - data/stop_requested.flag を検知するとループを終了

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path に書き込む（本番 DB と分離）
    - プロセス優先度を "high" に設定
    - ExecutionEngine をスレッドで起動。data/stop_requested.flag を検知すると停止要求を出す
    - PID ファイル: data/execution.pid（デフォルト）を使用

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数、さらに無ければ data/paper_trading.db）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を表示（positions, trade_logs, system_status, risk_logs, dashboard）

- AI / レジーム・ニュース処理（ライブラリ関数）
  - kabusys.ai.score_news(...)：DuckDB 接続と target_date を渡すと ai_scores を書き込む
  - kabusys.ai.regime_detector.score_regime(...)：market_regime テーブルへ書き込む
  - いずれも OPENAI_API_KEY（または引数で渡す api_key）が必要

---

## 運用・注意点

- Kill Switch / Stop フラグ:
  - KillSwitch は RiskMonitor の結果等を評価して data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を検出して停止します。
  - run_monitoring / run_execution はそれぞれ data/stop_requested.flag を監視して安全にシャットダウンします（stop 用の別フラグ）。
- モード差分:
  - Paper Trading モード（KABUSYS_ENV=paper_trading）は発注をモック化し、DB を分離します（PAPER_TRADING_SQLITE_PATH）。
  - 監視は常に sqlite_path（監視用 DB）を使用します。環境に依らず監視ログは production path に書き込まれます。
- 権限:
  - プロセス優先度 / CPU affinity の設定は OS により権限が必要な場合があります。設定が失敗すると警告ログのみ出力されます。
- OpenAI 呼び出し:
  - rate-limit / 一時エラー / 5xx に対しては指数バックオフでリトライする実装がありますが、API キーの設定とコスト管理は運用者の責任です。

---

## 主要ファイルとディレクトリ構成

（src/kabusys をルートにした主要ファイルの抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - ai/
    - news_nlp.py          — ニュース文章の OpenAI を使ったスコアリング
    - regime_detector.py   — マクロ + MA200 によるレジーム判定
  - research/
    - factor_research.py   — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / summary utilities
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定ロジック（単元丸め・制限）
    - risk_adjustment.py   — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ初期化 + MonitoringDB ラッパー
    - system_monitor.py    — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py     — 注文滞留 / 約定異常検出
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 書き込みロジック
    - alert_manager.py     — LINE への通知
    - monitoring_engine.py — 監視コンポーネントの統合（ポーリング）
    - streamlit_dashboard.py — Streamlit UI
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py  (Engine 実装ファイルはリポジトリ内に存在)
    - broker_factory.py    (ブローカークライアント生成)
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ
  - research/, portfolio/ ...（上記参照）

- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper trading 用)
  - execution.pid
  - kill.flag
  - stop_requested.flag

（実際の構成はリポジトリ内のファイルを参照してください）

---

## 開発者向けメモ / テスト支援

- Settings は自動で .env をロードしますが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動ロードを無効にできます。
- OpenAI 呼び出しや外部 API はユニットテストでモック可能なように、呼び出し部分は関数化されており patch がしやすく作られています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB スキーマが古い場合は軽微なマイグレーション（列追加）を行います。

---

## よくある質問（FAQ）

Q. Paper Trading と本番 DB は分離されていますか？
A. はい。KABUSYS_ENV=paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring.sqlite は触りません。

Q. 監視のポーリング間隔を変更するには？
A. 環境変数 MONITOR_POLL_INTERVAL に秒数を設定してください（整数、1 以上）。不正値はデフォルト 60 秒にフォールバックします。

Q. ExecutionEngine の強制停止はどうしますか？
A. KillSwitch による自動停止（kill.flag）か、data/stop_requested.flag を作成して run_execution/run_monitoring のループを終了させる方法があります。kill.flag は KillSwitch が書き込みます。手動で削除したい場合はファイルを削除してください。

---

README の内容はコードのコメントや docstring を参照して作成しています。各モジュールには詳細な docstring／注記があるため、実装や調整を行う際は該当ファイルを参照してください。必要であればデプロイ手順や .env.example のテンプレートも作成しますのでお知らせください。