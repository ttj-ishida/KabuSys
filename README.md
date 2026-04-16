# KabuSys — README

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群（KabuSys）のソースコードです。本 README はプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成をまとめた参照ドキュメントです。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- 自動注文の実行エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視基盤（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選別・重み計算・ポジションサイズ算出）
- リサーチ用ファクター計算（momentum/value/volatility 等）と特徴量解析
- ニュースを利用した AI（OpenAI）ベースのセンチメント評価（news_nlp）
- Paper Trading 向けの検証・レポート生成ツール
- 監視ダッシュボード（Streamlit）

設計のポイント：
- DuckDB をリサーチ用データベース、SQLite を監視・発注ログ等に使用
- Paper Trading 環境は本番 DB と分離（専用 SQLite を使用）
- OpenAI API を利用した NLP モジュールは失敗耐性（リトライ・フォールバック）を考慮

---

## 主な機能一覧

- Execution
  - 注文作成・送信・状態同期（OrderManager, Reconciler）
  - Risk 管理（RiskManager）や注文リポジトリ
- Monitoring
  - システム健全性（CPU/メモリ/ディスク）とデータ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件を満たしたら実行エンジンに停止信号）
  - LINE での通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio Construction
  - 候補選択、等ウェイト／スコア加重、リスクベースのポジション量算出
  - セクターキャップ適用、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事を OpenAI に送り銘柄別センチメントを算出し DB に書き込む（news_nlp.score_news）
  - マクロニュース + ETF MA200 差で市場レジーム判定（ai.regime_detector.score_regime）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)
- SQLite（標準ライブラリで利用可）
- ネットワークは OpenAI, LINE API 等へのアクセスが必要（該当機能を使用する場合）

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

4. .env の用意
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. data ディレクトリ等を作成
   - mkdir -p data

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabu API 用）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）送信に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用ファイルのパス

注: Settings モジュール（kabusys.config）により自動読み込みされます。必須キーが未設定の場合は例外が発生します。

---

## 実行方法（代表コマンド）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する場合:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)  # api_key が None の場合は環境変数 OPENAI_API_KEY を利用
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 実行制御・フラグファイル

- data/stop_requested.flag
  - run_monitoring/run_execution などがこのファイルを検知すると自動的にループを終了します（安全停止用）。
- data/kill.flag
  - KillSwitch により書き込まれ、ExecutionEngine に停止シグナルを送ります（条件: ドローダウン超過など）。
- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込む想定のファイル。SystemMonitor はこれを参照してプロセス生存チェックを行います。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数／設定読み込みロジック（.env 自動読み込み、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ（主なファイル）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py — 注文滞留・約定価格異常の監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成/管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文生成・外向け API
  - reconciler.py — 起動時の復旧・照合作業
  - その他（broker_factory, execution_engine, order_repository 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数算定（lot サイズ丸め、aggregate cap 等）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースを用いた銘柄センチメント算出（OpenAI）
  - regime_detector.py — マクロ+MA200 による市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

その他:
- data/ — 実行時に生成される DB・フラグファイルなど（既定: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）

---

## 使い方の補足・注意点

- Settings（kabusys.config）
  - .env/.env.local を自動読み込み（OS 環境変数優先）。自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 必須変数が未設定だと ValueError が出ます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
- Paper Trading
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を利用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます
  - PAPER_FILL_MODE によってモックの約定挙動を制御できます
- OpenAI 関連
  - API 呼び出しでは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライします
  - API キーは OPENAI_API_KEY もしくは関数引数で指定
- ロギング
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を行います。詳細は Settings.log_level 等でカスタマイズ可能
- DB マイグレーション
  - init_monitoring_db は冪等（必要に応じてカラム追加の簡易マイグレーション処理あり）

---

## 開発メモ

- 単体・結合テストでは .env 自動読み込みを無効にすること（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）を推奨
- OpenAI 呼び出し部分はテスト時に _call_openai_api を patch して外部依存を切る設計になっています
- process_priority や CPU affinity 設定はプラットフォーム依存の差分を吸収しますが、権限不足や未対応 OS の場合は警告が出てスキップされます

---

以上が README の要点です。必要であれば、実際に配布する README.md に含めるサンプル .env.example、requirements.txt のテンプレート、起動・デバッグのユースケース（例: ローカルでの Paper Trading ワークフロー）を追記できます。どの情報を追加しますか？