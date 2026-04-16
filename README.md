# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。本リポジトリには以下の主要機能を含むモジュール群が実装されています：

- 注文発行・状態管理とブローカー連携（Execution）
- 監視・アラート・キルスイッチ（Monitoring）
- ポートフォリオ構築（選定・重み・株数決定・リスク調整）
- ファクター計算・特徴量探索（Research）
- ニュースの NLP によるセンチメント評価（AI）
- Paper Trading 用検証レポート生成ツール（tools）
- ユーティリティ（プロセス優先度設定、設定読み込み等）

設計方針として、本番（live）・紙上検証（paper_trading）・開発（development）を環境変数 `KABUSYS_ENV` で切替え可能で、DBの分離やモックブローカーの利用などフェイルセーフを考慮しています。

---

## 主な機能一覧

- Execution
  - 注文作成 → ブローカー送信 → 状態同期（Reconciler）
  - OrderManager / OrderRepository による状態管理
  - RiskManager によるリスク制限（ポジション上限・利用率等）
  - Paper Trading モード（モックブローカー & 専用 SQLite）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス死活 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：リスクトリガで Execution を停止するフラグ書き込み
  - AlertManager：LINE Push 通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio
  - 候補選定、等重/スコア加重の重み算出、位置サイズ計算、セクター制限、レジーム乗数

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）
  - 将来リターン・IC・統計サマリー等の探索系ユーティリティ

- AI
  - news_nlp: ニュース記事を OpenAI に送り銘柄ごとにセンチメントスコアを生成して ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定（bull/neutral/bear）

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## 前提・必要パッケージ

推奨 Python 3.8+（コードの型ヒントやモジュール仕様により 3.8 以上を想定）。

主な依存（requirements.txt が別途あればそちらを参照してください）：
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例：
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル）

1. レポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記を参照）
4. プロジェクトルートに `.env` を配置（任意）
   - 自動で `.env` / `.env.local` を読み込む仕組みがあります（OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須設定は `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` などで、未設定時は実行時にエラーになります。`.env.example` を参照して作成してください（存在する場合）。
5. data ディレクトリの作成（必要に応じて）
   mkdir -p data

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（development | paper_trading | live） デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- SQLITE_PATH: 監視用 SQLite（monitoring.db） デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイル デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: paper_trading の約定シミュレーション（instant | partial | never | reject） デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を消去する場合は "1"
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）で使用

設定は `.env` または実行前に環境変数で与えてください。

---

## 実行方法（代表的なコマンド）

- ExecutionEngine を起動（本番/紙上は Settings.env に依存）
  python -m kabusys.run_execution
  - paper_trading 環境時はモックブローカーを使用し DB は `PAPER_TRADING_SQLITE_PATH` に分離されます。

- Monitoring を起動（ポーリング）
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV にかかわらず production sqlite を参照する設計）。

- Streamlit ダッシュボード（監視 DB を参照）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- AI / Regime スコアリング（Python API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止・キル機構

- stop_requested.flag
  - run_execution/run_monitoring 側で監視されており、ファイルが存在するとループを抜けて安全に終了します。
  - パス: project_root/data/stop_requested.flag（スクリプトにより参照）

- kill.flag
  - KillSwitch が条件を満たしたときに作成され、ExecutionEngine に停止シグナルを送ります。
  - パスは Settings.kill_flag_path（デフォルト data/kill.flag）
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に削除されます（クリーンアップ）。

---

## 主要ファイル・ディレクトリ構成

以下は src/kabusys 以下の主要構成（抜粋）です。

- src/kabusys/
  - __init__.py                (パッケージ定義、バージョン)
  - config.py                  (環境変数 / 設定読み込みロジック)
  - run_execution.py           (ExecutionEngine 起動スクリプト)
  - run_monitoring.py          (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - execution/
    - execution_engine.py      (ExecutionEngine 本体) ※詳細実装あり
    - order_manager.py         (OrderManager)
    - order_repository.py      (OrderRepository, SQLite)
    - reconciler.py            (再起動時のリコンシリエーション)
    - risk_manager.py          (リスク管理)
    - broker_factory.py        (Broker クライアント生成)
    - ...                     (その他 execution 関連)
  - monitoring/
    - monitoring_db.py         (monitoring 用 SQLite テーブル初期化 + ラッパー)
    - system_monitor.py        (システム状態・データ鮮度監視)
    - trade_monitor.py         (滞留注文 / 約定異常監視)
    - risk_monitor.py          (ドローダウン / ポジション上限監視)
    - kill_switch.py           (kill.flag 管理)
    - alert_manager.py         (LINE 通知ラッパー)
    - monitoring_engine.py     (各 Monitor を束ねる Engine)
    - streamlit_dashboard.py   (Streamlit ダッシュボード)
  - portfolio/
    - portfolio_builder.py     (候補選定・重み算出)
    - position_sizing.py       (株数・スケーリング・単元丸め)
    - risk_adjustment.py       (セクター制限・レジーム乗数)
  - research/
    - factor_research.py      (momentum/value/volatility)
    - feature_exploration.py  (forward returns / IC / summaries)
  - ai/
    - news_nlp.py             (ニュース NPL -> ai_scores 書込)
    - regime_detector.py      (MA200 + マクロセンチメントで regime 判定)
  - data/                      (実行時に利用される DB・フラグファイル等を置く場所)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading用)
    - kabusys.duckdb (DuckDB データ)
    - execution.pid
    - stop_requested.flag
    - kill.flag

※上記は代表的なファイルで、実装はさらに細分化されています。各モジュールの docstring に設計意図や使用例が記載されています。

---

## DB / マイグレーションについて

- monitoring_db.init_monitoring_db は冪等にテーブル／インデックスを作成します。起動時に呼び出されるため基本的に手動マイグレーションは不要です。
- 既存 DB に対して必要なカラムが欠けている場合（例: `dashboard.peak_value`, `trade_logs.latency_ms`）は起動時に ALTER TABLE による追加を試みます。

---

## 注意点 / 運用メモ

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、モックブローカーが使用されます。Paper トレードのデータ保存先は `PAPER_TRADING_SQLITE_PATH` で指定してください。
- AI（news_nlp / regime_detector）は OpenAI API を使用します。`OPENAI_API_KEY` が必須です。API 呼び出しはリトライやフェイルセーフを備えていますが、料金・レート制限に注意してください。
- MONITOR_POLL_INTERVAL は秒数で設定。0 以下や不正値はデフォルト（60 秒）にフォールバックします。
- プロセス優先度設定には psutil を使用します。権限次第で設定に失敗することがあります（警告を記録して継続します）。
- LINE 通知は設定が無い場合は送信を行わずログのみ出力します。クールダウン（デフォルト 30 分）が設定されています。

---

## よく使うコマンドまとめ

- 起動（Execution）
  - python -m kabusys.run_execution

- 起動（Monitoring）
  - python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - もしくは --db PATH で DB を指定

---

README は以上です。追加で以下が必要であれば教えてください：
- .env.example のテンプレート作成
- requirements.txt / Dockerfile / systemd ユニットのサンプル
- 各モジュールの API 呼び出し例（コードスニペット）