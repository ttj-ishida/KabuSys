README
======
KabuSys — 日本株自動売買システム（ミニマル版）
----------------------------------------

このリポジトリは、日本株の自動売買システム「KabuSys」の主要コンポーネント群を含みます。
設計方針としては、実際の ブローカーAPI を呼ぶ実行部分（Execution）と、監視（Monitoring）、ポートフォリオ構築（Portfolio）、
リサーチ（Research）や AI を用いたニュース解析（AI）などをモジュール化して実装しています。
多くのユーティリティはテストしやすい純粋関数群として実装されています。


主な特徴
--------
- Execution
  - ExecutionEngine を起動して注文発行・リスク管理・約定リコンシリエーションを行う（run_execution.py）。
  - paper_trading 環境では MockBrokerClient を使い、本番 DB と分離して data/paper_trading.db に記録。
- Monitoring
  - System / Trade / Risk の各種モニタをポーリングして監視ログを SQLite に永続化（run_monitoring.py）。
  - Kill switch（data/kill.flag）により ExecutionEngine を安全に停止可能。
  - Streamlit ベースの監視ダッシュボードを提供（src/kabusys/monitoring/streamlit_dashboard.py）。
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群。
- Research
  - DuckDB を用いたファクタ計算（Momentum/Volatility/Value）や特徴量解析ユーティリティ。
- AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）。
  - API レスポンスのリトライやバリデーション、結果の DuckDB への書き込みを実装。
- ユーティリティ
  - 環境変数管理（.env 自動読み込み）、プロセス優先度設定（psutil）など。


依存パッケージ（代表例）
-----------------------
本リポジトリの一部機能は下記パッケージを必要とします（環境によって増減します）。
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit
- sqlite3（標準ライブラリ）
- その他（プロジェクトで使用する追加ライブラリがあれば requirements.txt を参照してください）

例（pip でのインストール）:
pip install duckdb psutil requests openai streamlit


セットアップ手順
---------------
1. リポジトリをクローンし、Python 環境を用意します。
   - 仮想環境の作成を推奨（venv, conda 等）。

2. 依存パッケージをインストールします（上記参照）。
   - 例: pip install duckdb psutil requests openai streamlit

3. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成して設定できます。
   - 自動読み込みのルール:
     - OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。
   - 必要な代表的環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定動作: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring で上書き可、デフォルト 60）

4. 初回起動時の DB 初期化
   - run_monitoring.py や run_execution.py は内部で init_monitoring_db() を呼び、必要なテーブルを作成します。
   - DuckDB ファイルは外部から用意しておくか、必要に応じて接続時に生成されます。


使い方（実行例）
----------------

- 監視ループの起動（Monitoring）
  - デフォルト: KABUSYS_ENV に依存せず本番 sqlite_path を使用して監視ログを記録します。
  - 実行:
    python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - ストップ: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します（または Ctrl-C）。

- 実行エンジンの起動（Execution）
  - paper_trading 環境では MockBrokerClient を使用し、paper 用 DB に記録します。
  - 実行:
    KABUSYS_ENV=development python -m kabusys.run_execution
    # paper_trading 環境例
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成すると実行中に検知して停止します。

- Paper Trading 検証レポート（ツール）
  - SQLite（paper_trading DB）から集計レポートを生成します。
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit 監視ダッシュボード
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで表示される UI から最近のポジション・注文・システム状態等を確認できます。

- ライブラリ関数の利用例（Python REPL）
  - ポートフォリオ関連:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - Research:
    from kabusys.research import calc_momentum, calc_volatility, calc_value

注意事項 / 実運用に関するポイント
--------------------------------
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH に保存）。
- Monitoring は KABUSYS_ENV にかかわらずデフォルトで本番 sqlite_path を使用します（監視は常に本番状態を想定）。
- kill.flag / stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトの data ディレクトリ下の stop_requested.flag を監視して終了します。
  - KillSwitch（監視側）からは data/kill.flag に理由テキストを書き込み、ExecutionEngine に停止シグナルを与えます。
- OpenAI を使う AI 機能:
  - OPENAI_API_KEY が未設定だとエラー・未実行になります。AI 関連は外部 API に依存するため、API 呼び出し時にリトライやフォールバック（0.0）を行う設計です。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。psutil の権限や OS によっては設定に失敗して警告が出ますが動作は継続します。
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対してカラム追加（簡易マイグレーション）を試みます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings 管理（.env 自動ロード）
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

src/kabusys/ai/
- news_nlp.py                      — ニュースセンチメント評価（OpenAI）
- regime_detector.py               — 市場レジーム判定（OpenAI）

src/kabusys/monitoring/
- monitoring_db.py                 — SQLite 監視ログ永続化層
- system_monitor.py                — システム状態・データ鮮度監視
- trade_monitor.py                 — 注文滞留・約定異常監視
- risk_monitor.py                  — ドローダウン・ポジション上限監視
- kill_switch.py                   — kill.flag 書込みユーティリティ
- alert_manager.py                 — LINE 通知管理
- monitoring_engine.py             — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py           — Streamlit ダッシュボード

src/kabusys/execution/
- execution_engine.py (実装ファイル群は存在) — 実行エンジン、order_manager、reconciler 等
- order_manager.py
- reconciler.py
- order_repository.py
- (その他 execution 関連ファイル)

src/kabusys/portfolio/
- portfolio_builder.py              — 候補選定・重み計算
- position_sizing.py                — 株数計算・丸め・投下金額スケーリング
- risk_adjustment.py                — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py                — ファクター計算（momentum/volatility/value）
- feature_exploration.py            — 将来リターン、IC、統計サマリー

src/kabusys/tools/
- paper_verification_report.py      — Paper Trading 検証レポート生成 CLI ツール

src/kabusys/utils/
- process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

data/
- monitoring.db (デフォルトの SQLite 監視 DB)
- paper_trading.db (paper_trading 用 DB)
- execution.pid / stop_requested.flag / kill.flag 等のフラグ・PIDファイルを格納

テスト / 開発メモ
-----------------
- 多くの計算関数（portfolio, research 等）は副作用がなくユニットテストが容易です。
- AI 関連や外部 API 呼び出しはモック化が推奨されています（モジュール内で _call_openai_api をラップしているため patch が容易）。
- .env の取り扱いは config.Settings に集約されており、自動読み込みを環境変数で無効化してテスト時の影響を防げます。

ライセンス
---------
（ここにライセンス情報を記載してください。リポジトリに LICENSE ファイルがあればその内容に従ってください。）

お問い合わせ / 追加情報
-----------------------
- コード内の docstring や各モジュールの先頭コメントに設計意図や利用方法の説明があります。実装や振る舞いの詳細は該当ファイルを参照してください。