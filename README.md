# KabuSys

日本株向けの自動売買システムの一部コンポーネント群（モニタリング、実行エンジンの起動スクリプト、ポートフォリオ構築、リサーチ、AIニューススコアリングなど）を収めたコードベースです。本 README はこのリポジトリの主要機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買に必要な以下の機能を含むモジュール群です。

- 実行エンジン（ExecutionEngine）の起動・依存組み立て（ブローカークライアント、注文管理、リスク管理、リコンシリエーション）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- モニタリング DB（SQLite）への永続化インタフェース
- Paper Trading 用の分離された DB と検証レポート生成
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約・レジーム乗数）
- リサーチ用ファクター計算（Momentum / Volatility / Value など）と特徴量解析ユーティリティ
- ニュース NLP による銘柄別センチメントスコアリング（OpenAI API を利用）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- 便利ユーティリティ（プロセス優先度設定、Streamlit ダッシュボードなど）

設計上のポイント：
- DuckDB を使った時系列・ファクタ計算（prices_daily, raw_financials 等）
- 監視や実行まわりは SQLite にログ・状態を保持
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- OpenAI 呼び出しはフェイルセーフ（API 失敗時はデフォルト値で続行）

---

## 主な機能一覧

- run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で間隔を上書き可能（デフォルト 60 秒）
  - PID ファイル監視・データ鮮度チェック・システムリスクログ記録
- run_execution.py：ExecutionEngine 起動スクリプト
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
  - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立てて run_session を呼ぶ
- monitoring パッケージ：
  - MonitoringDB：SQLite スキーマ初期化・読み書き API
  - SystemMonitor / TradeMonitor / RiskMonitor：個別チェックと DB ログ書き込み
  - KillSwitch：フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine：複数モニタを束ねたポーリングループ
  - streamlit_dashboard.py：Streamlit によるダッシュボード表示
- tools：
  - paper_verification_report.py：Paper Trading DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）
- portfolio：
  - 候補選定、重み計算、リスク制約適用、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- research：
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリ
- ai：
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: MA とマクロニュースの LLM 評価を合成して market_regime に書き込む

---

## セットアップ手順

前提：
- Python 3.10 以上（typing の `X | Y` を使用）
- 標準的な Unix 系または Windows（psutil の挙動差異あり）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存ライブラリをインストール
   - 決まった requirements.txt が無い場合の例（必要に応じて調整してください）:
     - pip install duckdb psutil requests openai streamlit

   必要に応じて SQLite は標準に同梱されています。OS によっては追加パッケージが必要な場合があります。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境 > .env.local > .env の順で優先）。
   - 自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（デフォルト値/説明）：
   - KABUSYS_ENV: 起動環境。`development` | `paper_trading` | `live`（デフォルト: development）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要に応じて）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag ファイルパス（デフォルト: data/kill.flag）
   - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするフラグ（"1" で有効）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

4. DB 初期化
   - 監視用 SQLite はスクリプト起動時に `init_monitoring_db()` が呼ばれて不足テーブルを作成します。DuckDB のスキーマ（prices_daily 等）が必要な場合は事前にデータ投入してください。

---

## 使い方

基本的な起動コマンド例（プロジェクトルートから）:

- システム監視ループ起動
  - MONITOR_POLL_INTERVAL を指定する例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトでは 60 秒間隔で SystemMonitor.check_once を呼び続け、Monitoring DB に書き込みします。

- 実行エンジン起動
  - 本番/テストを切り替えるには KABUSYS_ENV を設定
    - Paper Trading（MockBroker を使用、データは data/paper_trading.db に分離）
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - 開発（デフォルト）
      - python -m kabusys.run_execution

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定の例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI（ニューススコア・レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数、または関数引数で指定）
  - Python から呼ぶ例（簡略）:
    - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, target_date, api_key="...")  # 書き込みは ai_scores テーブルへ
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(duckdb_conn, target_date, api_key="...")  # market_regime テーブルへ

運用上の注意:
- run_execution は起動時に PID ファイルを書き、SystemMonitor から存在チェックされます。stale PID 検出時は PID ファイルを削除してリスクイベントを記録します。
- KillSwitch は RiskMonitor の判定に基づき kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側で kill.flag を検出して停止する実装が前提）。
- LINE 通知は AlertManager を通じて送信。token / user_id が未設定の場合はログのみ。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義（バージョン、public API）
- config.py — 環境変数・設定読み込みロジック（.env 自動読込、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループのエントリ
- run_execution.py — ExecutionEngine 起動のエントリ

src/kabusys/monitoring/
- monitoring_db.py — monitoring 用 SQLite スキーマ初期化／永続化 API（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常価格の監視
- risk_monitor.py — ドローダウン・ポジション上限チェック
- monitoring_engine.py — 各 Monitor を束ねるポーリング実行器
- alert_manager.py — LINE による通知送信（クールダウン管理）
- kill_switch.py — kill.flag の作成/評価
- streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

src/kabusys/execution/
- order_repository.py, order_manager.py, reconciler.py, execution_engine.py など（注文管理・リコンシリエーション・実行エンジン関連）
  - （本文に長い実装が含まれています。OrderManager, Reconciler は起動時自動復旧・注文同期などを担います）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み付け（等配分・スコア加重）
- position_sizing.py — 発注株数計算・lot 単位の丸め・aggregate cap
- risk_adjustment.py — セクター上限適用・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value ファクターの計算（DuckDB を利用）
- feature_exploration.py — 将来リターン・IC・統計サマリ等の研究ユーティリティ

src/kabusys/ai/
- news_nlp.py — raw_news を OpenAI で評価し ai_scores に書込む
- regime_detector.py — ETF MA とマクロニュース LLM を組合せて market_regime に書込む

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成ツール

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — デフォルトの DB 保存先（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
  - 実際のプロジェクトではこのディレクトリに DB を置く想定（Path.expanduser を使用）

---

## 追加の運用メモ / FAQ

- .env のパースはシンプルな実装をしており、クォートや export 形式、インラインコメントに一定の対応があります。`.env.example` を参考にしてください（例ファイルがある場合）。
- Paper Trading の約定挙動（PAPER_FILL_MODE）:
  - instant / partial / never / reject が有効値。`Settings.paper_fill_mode` が検証します。
- SQLite / DuckDB のロックや読み取り専用アクセス:
  - Streamlit ダッシュボードは監視 DB を read-only URI でオープンする例を実装しています（URI に `?mode=ro` を付与）。
- OpenAI API の呼び出しは外部サービスに依存するため、ネットワーク/レート制限に対してリトライロジックを実装しています。API キー未設定時は例外を投げます（関数呼び出し側で扱ってください）。

---

この README はコードベース内から読み取れる設計意図・利用方法に基づいて作成しています。実運用・デプロイ時は環境変数や DB のバックアップ、権限（PID 書き込み等）の確認、LINE / OpenAI の利用制限を十分に考慮してください。必要であれば、README に追記する具体的なデプロイ手順や systemd / Windows サービス登録例なども作成します。どの情報を追加したいか教えてください。