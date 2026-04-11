KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なフレームワークです。  
主要な機能はシグナルに基づく発注エンジン（ExecutionEngine）、監視・アラート基盤（Monitoring）、ファクター計算・リサーチ、そして LLM を利用したニュースセンチメント評価（AI モジュール）を含みます。  
本リポジトリは純粋関数的なポートフォリオ構築ロジック（配分・ポジションサイジング等）や、SQLite / DuckDB を用いたデータ操作・永続化の実装を備えています。

主な特徴
--------
- ExecutionEngine
  - シグナル読み込み → Gate 検査 → 発注（OrderManager 経由）
  - 再起動時のリコンシリエーション（Reconciler）
  - Paper trading 用に本番 DB と分離された専用 SQLite を使用可能
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - 注文滞留・約定異常の検出
  - ドローダウン／ポジション上限監視と Kill Switch（フラグファイルにより Execution を停止）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースのダッシュボード
- Portfolio ライブラリ
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算、セクター上限・レジーム乗数適用
- Research
  - モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC 計算等（DuckDB 接続で動作）
- AI
  - raw_news をまとめて OpenAI（gpt-4o-mini 等）へ送信し、銘柄別センチメントスコアを ai_scores テーブルへ記録
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
  - 環境変数の .env 自動ロード（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）

動作要件
--------
- Python 3.10+
  - ソース内で | 型（union）や一部新しい型注釈を使用しています
- 主な Python 依存パッケージ
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（Python 標準ライブラリで利用）
- （オプション）LINE Messaging API の利用にはトークン

セットアップ
----------
1. リポジトリをクローン／プロジェクトルートへ移動
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS / Linux: source .venv/bin/activate
3. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - requirements.txt がない場合は個別に:
     - pip install duckdb psutil requests openai streamlit
4. 開発時はパッケージを editable インストールすると便利
   - pip install -e .

環境変数 / .env
----------------
- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env を自動的に読み込みます（.env.local は上書き）。
  - OS 環境変数は上書きされないよう保護されます。
  - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- よく使う環境変数（代表例）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
  - KABU_API_PASSWORD, KABU_API_BASE_URL: kabu ステーション API
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag パス（デフォルト data/kill.flag）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（主要スクリプト）
-----------------------

1. 監視ループを起動（Monitoring）
   - デフォルトで本番 sqlite_path を使用（KABUSYS_ENV に依らず）
   - ポーリング間隔を上書きする:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 実行（パッケージをインストール済みの場合）:
     - python -m kabusys.run_monitoring
   - 直接スクリプトパスから実行する場合（PYTHONPATH に src を含めるか pip install -e . を推奨）
     - PYTHONPATH=src python src/kabusys/run_monitoring.py
   - 実行中、system_status / risk_logs / trade_logs / positions / dashboard 等が data/monitoring.db に書き込まれます。

2. 発注エンジンを起動（Execution）
   - デフォルト環境: KABUSYS_ENV=development
   - Paper trading（ブローカークライアントは Mock を使用、DB は data/paper_trading.db）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - Live 環境:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - 起動直後にプロセス優先度を上げ、Reconciler による状態同期等を行います。
   - ExecutionEngine は kill.flag を検出すると安全に停止する設計です（KillSwitch が書き込み）。

3. Streamlit ダッシュボード（監視）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite を開くため、MonitoringEngine が先に DB を初期化している必要があります。

4. AI / リサーチ機能
   - OpenAI API キーを設定:
     - export OPENAI_API_KEY="sk-..."
   - ニュース NLP（ai_scores へ書込）:
     - 呼び出しはアプリケーション内部から行います（例: kabusys.ai.score_news を import して使用）。
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime を利用。DuckDB の prices_daily / raw_news テーブルを参照します。
   - 注意: API 失敗時はフェイルセーフとしてスコアを 0.0 にする等の保護が入っていますが、API キー未設定時は例外が投げられます。

設定例（.env）
--------------
例:
    KABUSYS_ENV=paper_trading
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
    JQUANTS_REFRESH_TOKEN=xxxxxxxx
    KABU_API_PASSWORD=secret
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    PID_FILE_PATH=data/execution.pid
    KILL_FLAG_PATH=data/kill.flag
    LOG_LEVEL=INFO
    PAPER_FILL_MODE=instant

挙動上の注意点 / 補足
-------------------
- .env の自動ロードはプロジェクトルート（.git or pyproject.toml）を基準に行います。テスト環境などで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は常に設定ファイルが指定する sqlite_path（本番 DB）を使用します。paper_trading モードでも監視 DB は共有される点に注意してください（ただし run_execution は paper_trading の場合 paper_sqlite_path を使用して発注ログを分離します）。
- KillSwitch はデータベース上のリスクイベントやルールに基づき data/kill.flag に理由を書き込みます。ExecutionEngine は起動時／ループ中に kill.flag を検出すると停止します。kill.flag を手動で削除する場合は設定により起動時に自動クリア（KILL_FLAG_CLEAR_ON_START=1）できます。
- OpenAI 呼び出しにはネットワークエラーやレート制限へのリトライロジックが含まれますが、API キー未設定時は明示的に例外が上がります。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env 読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor をポーリングで回す起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成・管理
    - alert_manager.py — LINE Push 送信（クールダウン管理付き）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py — 発注状態の外向き API（OrderManager）
    - order_repository.py, order_record.py, broker_api.py, broker_factory.py, ...（注文関連）
    - reconciler.py — 再起動後の同期ロジック
    - risk_manager.py — 発注 Gate / レート制限 / 回路ブレーカー
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 配分・サイズ計算
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM センチメント処理（ai_scores テーブルへ書込）
    - regime_detector.py — マクロ + MA200 によるレジーム判定
  - data/  （実行時に生成される想定: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）

テスト / 開発
---------------
- 各モジュールは pure 関数やクラスで分離されています。ユニットテストを追加する際は、DuckDB や SQLite のインメモリ接続（/ tmp に一時ファイル等）を使って依存を注入してください。
- OpenAI 呼び出し部分は _call_openai_api 関数をパッチ（unittest.mock.patch）してモック化する設計になっています。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス・貢献方針はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はプロジェクト所有者へ問い合わせてください）。

問い合わせ・補足
-----------------
この README はソースコードから抽出した仕様に基づき作成しています。環境依存の詳細や未提示ファイル（broker 実装、orders DB スキーマ等）については実際のプロジェクトドキュメントやコードコメントを参照してください。必要であれば、実行例や .env.example の雛形を追加で作成します。