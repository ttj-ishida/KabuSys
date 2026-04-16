KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なPythonパッケージ群です。
主な設計方針は「本番環境と検証（Paper Trading）を分離」「DBはSQLite / DuckDBで完結」「外部API呼び出しは明示的に管理（OpenAI, kabuステーション 等）」です。  
モジュール群は発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI を用いたニュース解析などを含みます。

主な特徴（機能一覧）
-------------------
- ExecutionEngine：ブローカークライアント経由の注文管理・発注・リスク管理・リコンシリエーション
- Monitoring：システム状態、注文滞留、約定異常、ドローダウン等の定期監視とログ永続化（SQLite）
- Kill Switch：リスク閾値（ドローダウン等）到達時に停止フラグを書き込む機能
- AlertManager：LINE Messaging API を用いた通知（クールダウン制御あり）
- Portfolio Construction：候補選定、重み付け（等金額/スコア）・ポジションサイズ計算（単元丸め、リスク制限）
- Research：DuckDB を使ったファクター計算（モメンタム/ボラティリティ/バリュー）と特徴量探索（IC計算等）
- AI モジュール：ニュースのセンチメントスコアリング（OpenAI）・市場レジーム判定
- Tools：Paper Trading 検証レポート生成スクリプト、Streamlit ダッシュボード 等
- DB：DuckDB（時系列・リサーチデータ等）と SQLite（監視ログ・注文ログ）を併用

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意する
   - 仮想環境推奨: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストールする
   - 主要依存（一例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit （ダッシュボード利用時）
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt は本リポジトリに含まれていない想定のため、上記を参考に必要なパッケージをインストールしてください。

3. プロジェクトルートに .env を配置（任意）
   - Settings モジュールは自動でプロジェクトルートの .env と .env.local を読み込みます（既存の OS 環境変数を保護）。
   - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリの作成
   - data/ 配下に SQLite / DuckDB を置く想定（デフォルトパスは Settings に記載）。
   - 例: mkdir -p data

主要な環境変数（代表）
---------------------
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、専用の Paper DB（data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出し用（AI モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker での約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用パス（デフォルト data/execution.pid / data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロードを無効化

使い方
------

- 実行エンジン（ExecutionEngine）を起動する
  - 簡単な起動例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録され本番 DB と分離されます。
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に stop flag が作成されると安全に停止します（flag パスはプロジェクトの data/stop_requested.flag）。

- 監視ループ（Monitoring）を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト60秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

- Streamlit ダッシュボード（監視用）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで SQLite に接続し、ポートフォリオ / ポジション / 注文 / 最新システムステータス を可視化します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH または --db で DB を指定できます。

- AI 関連（ニューススコアリング / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して使用
  - OpenAI API キーが必要（引数で渡すか OPENAI_API_KEY 環境変数）

停止制御とフラグ
----------------
- 停止要求（監視 / 実行の中断）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して順次停止します（冪等的）。
- Kill Switch（リスク閾値到達時の自動停止）
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 起動側がこのフラグを見て停止します。
  - KillSwitch は drawdown やポジション上限などの条件に基づきファイルを書きます。

注意点 / トラブルシューティング
-------------------------------
- プロセス優先度設定:
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil の権限で失敗する場合は警告が出ますが処理は継続します。
- OpenAI や外部 API の呼び出しは失敗時にフェイルセーフ（スコア=0等でフォールバック）する設計です。ただし API キー未設定は例外を投げる箇所があります。
- DuckDB / SQLite への接続権限やファイル存在を確認してください。Streamlit は SQLite を read-only Uri で開きます。

ディレクトリ構成（主要ファイル・モジュールの概要）
---------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた挙動）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - execution/
    - order_manager.py, reconciler.py, ... — 注文管理・再同期・リスク管理に関する実装（Engine 本体は別ファイル）
    - broker_factory / broker_api / order_repository 等（ブローカー抽象・DBアクセス）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル作成と読み書きラッパー
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 判定用
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各モニタを束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出（リスク/単元丸め等）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — ETF MA とマクロセンチメントから市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (ランタイムで使用する想定のディレクトリ)
    - monitoring.db, paper_trading.db, kabusys.duckdb, *.pid, stop_requested.flag, kill.flag など

開発 / テストに関する補足
-------------------------
- Settings は .env/.env.local を自動で読み込みます。CI やユニットテストで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しや外部ブローカー呼び出しはテスト時にモック化できるように設計されています（内部の _call_openai_api などを patch 可能）。
- MonitoringDB.init_monitoring_db は冪等的にスキーマを作成し、必要に応じて簡易マイグレーション（カラム追加）を行います。

ライセンス / 貢献
-----------------
（本テンプレートではライセンス情報は含まれていません。必要に応じて LICENSE を追加してください。）

以上がこのコードベースの概要と利用方法のまとめです。特定のコマンド例や .env のサンプル（.env.example 相当）が必要であれば追って追加します。