# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の一部モジュール群を含みます。  
ここではプロジェクトの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント（注文実行、モニタリング、ポートフォリオ構築、リサーチ、AI を用いたニュース解析など）をモジュール化したシステムです。  
このコードベースは以下のような目的を持つモジュールで構成されています：

- ExecutionEngine（発注・注文管理・リコンシリエーション）
- Monitoring（システム状態・注文状態・リスク監視、LINE 通知、Dashboard）
- Portfolio（候補選定・配分・ポジションサイズ計算・リスク調整）
- Research（ファクター計算・特徴量探索）
- AI（ニュース NLP による銘柄センチメント、レジーム検出）
- Tools（Paper Trading 検証レポート生成 等）

設計方針としては「テスト可能でフェイルセーフ」かつ「ルックアヘッドバイアス回避（現在時刻の直接参照を避ける）」を心がけています。

---

## 主な機能一覧

- Execution（発注）
  - OrderManager / ExecutionEngine による発注フロー
  - Reconciler による再起動時の自動復旧（ブローカーと突合）
  - Paper Trading モード（本番 DB と分離された専用 SQLite を使用）

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、プロセス存在、データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）作成
  - AlertManager：LINE による通知（クールダウン機能付き）
  - Streamlit ダッシュボード（監視 DB を可視化）
  - monitoring_db：監視ログの永続化（SQLite）

- Portfolio
  - 候補選定（スコア順）、等配分 / スコア重み / リスクベースの株数決定
  - セクター集中制限、レジーム別乗数

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（スピアマンのランク相関）、統計サマリー等

- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントの銘柄別スコア化（ai_scoresへ書込み）
  - regime_detector: MA200 とマクロニュースの LLM 評価を用いた日次レジーム判定（market_regime へ書込み）
  - 両者とも外部 API 呼び出しは環境変数 OPENAI_API_KEY を使用

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（DB から各種指標を集計して出力）

---

## セットアップ手順

※ 下記は一般的なセットアップ手順の例です。プロジェクト固有の requirements.txt が提供されている場合はそちらを使用してください。

1. Python 環境を用意（推奨: Python 3.9+）
2. 必要パッケージをインストール（例）

   pip install duckdb psutil requests openai streamlit

   （実際には requirements.txt を作成して `pip install -r requirements.txt` を推奨）

3. プロジェクトルートに `data/` ディレクトリを作成

   mkdir -p data

4. 環境変数設定（.env ファイルまたは Shell 環境で設定）

   - 基本的な例（.env）:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=your_openai_key
     LINE_CHANNEL_ACCESS_TOKEN=your_line_token
     LINE_USER_ID=your_line_user_id

   - 自動ロード:
     config モジュールはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。

5. データベースファイルのパス（デフォルト）
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db
   - DuckDB: data/kabusys.duckdb

   必要に応じて環境変数で上書き:
   - SQLITE_PATH
   - PAPER_TRADING_SQLITE_PATH
   - DUCKDB_PATH
   - PID_FILE_PATH
   - KILL_FLAG_PATH

6. 権限・OS 依存の注意
   - process_priority の設定には psutil によるシステム呼び出しを行います。低権限環境では優先度設定や CPU affinity 設定が失敗する可能性があります（失敗時はログに警告が残り処理は継続します）。

---

## 使い方（主要スクリプト・モジュール）

以下は主要な起動スクリプトと使い方の例です。

1. Monitoring ポーリングを起動

   - デフォルトでポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、1 以上）。

   実行例（パッケージをモジュールとして起動）:

   python -m kabusys.run_monitoring

   または直接スクリプトを実行:

   python src/kabusys/run_monitoring.py

   特記事項:
   - 監視はプロセス優先度を "high" にセットしようとします（psutil が利用）。
   - 監視は常に production の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）。

2. ExecutionEngine（発注処理）を起動

   python -m kabusys.run_execution

   特記事項:
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します。本番 DB と分離されます。
   - 起動中に data/stop_requested.flag が作成されると停止します。
   - 実行は ExecutionEngine を別スレッドで起動し、外部フラグで安全停止します。

3. Streamlit ダッシュボード（監視 DB の可視化）

   起動例:

   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - 監視 DB を読み取り専用で開き、ポジション・注文・システムステータス・リスクログを表示します。

4. Paper Trading 検証レポート生成

   使い方:

   python -m kabusys.tools.paper_verification_report
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

   - デフォルト DB: data/paper_trading.db
   - 出力: 標準出力に検証レポートを表示（稼働率、注文成功率、送信率、レイテンシ等）

5. AI モジュール（ニューススコア・レジーム判定）

   - OpenAI API を利用するため、環境変数 `OPENAI_API_KEY` を設定してください。
   - プログラムから呼び出す例（DuckDB 接続を渡す）:

     from kabusys.ai.news_nlp import score_news
     count = score_news(duckdb_conn, target_date, api_key=None)  # api_key None -> 環境変数使用

     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key=None)

   - LLM 呼び出しはリトライ/バックオフを実装しており、失敗時は安全側のフォールバック（例: macro_sentiment=0.0）を行います。

6. ライブラリ的に利用する主要関数例

   - ポートフォリオ構築:

     from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

   - リサーチ:

     from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 開発/ペーパー/本番環境
  - 有効値: development | paper_trading | live
  - デフォルト: development

- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）

- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）

- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の認証トークン（Settings で必須）

- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject。デフォルト: instant）

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）用

- PID_FILE_PATH, KILL_FLAG_PATH: 実行管理・停止フラグのパス（デフォルトは data 内）

---

## 停止・制御フラグ

- data/stop_requested.flag: run_monitoring/run_execution が存在チェックして停止のトリガーに使う（run_execution は起動前に存在すれば起動を中止する）
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine の停止を促す（KillSwitch はリスク条件で生成）
- data/execution.pid: 実行中の ExecutionEngine の PID を管理（SystemMonitor はこれを監視）

---

## ディレクトリ構成（抜粋）

以下はこの README 作成時点での主要ファイル・ディレクトリ一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数・設定読み込みクラス（Settings）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄センチメント生成
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）

  - monitoring/
    - monitoring_db.py — SQLite の監視テーブル定義・ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 滞留注文/約定異常監視
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — フラグファイル書き込みによる停止制御
    - alert_manager.py — LINE 通知の送信（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - reconciler.py — 起動時リコンシリエーション
    - order_manager.py — 発注状態管理 API（OrderManager）
    - order_repository.py (参照されるがここでは抜粋)
    - ...（実際のブローカー API など別モジュール）

  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 株数計算・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

  - utils/
    - process_priority.py — プロセス優先度設定ユーティリティ（psutil 使用）

- data/
  - （実行時に生成される SQLite / DuckDB / pid / flag ファイル等）

---

## 運用メモ・注意点

- SQLite / DuckDB ファイルは相対パスで指定されています。運用時は絶対パスまたは運用環境のワーキングディレクトリに注意してください。
- SystemMonitor はデータ鮮度判定に DuckDB の prices_daily を参照します。price データ投入フローが別に必要です。
- OpenAI API 呼び出し部（news_nlp, regime_detector）はネットワークエラー・429・5xx に対してリトライ/バックオフを実装していますが、API キー利用量やレート制限には注意してください。
- process priority / CPU affinity 設定は OS に依存し、失敗しても処理は継続します（ログに警告が出ます）。
- Paper Trading と Live の DB は意図的に分離されています（Settings.is_paper を利用）。

---

## 追加の開発・拡張案（参考）
- 銘柄ごとの lot_size を外部マスタ（stocks テーブル）から取得する拡張
- position_sizing のトランザクション制御やより厳密なコスト推定（手数料・スリッページ）
- エンドツーエンドのテストスイート（モックブローカー・DuckDB テストデータ）
- モニタリングアラートの多チャネル化（メール・Slack 等）

---

必要であれば README にサンプル .env.example を追加したり、requirements.txt を生成してセットアップ手順を自動化する文書を追加できます。追加したい内容や出力フォーマット（英語版、簡易版等）があれば教えてください。