README.md

概要
-----
KabuSys は日本株向けの自動売買／リサーチ基盤の基礎ライブラリです。
主に以下の用途を想定しています。
- 自動売買の ExecutionEngine（発注管理、リスク管理、リコンシリエーション）
- システム監視（プロセス死活、データ鮮度、注文滞留、価格異常、ドローダウン監視）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI を使ったニュース NLP / 市場レジーム判定（OpenAI を利用）
- Paper Trading 用検証レポート生成ツール

主な特徴
---------
- 環境毎設定（development / paper_trading / live）
  - KABUSYS_ENV による挙動切替（paper_trading は発注をモック化・専用 DB 使用）
- 監視と Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせ、条件で kill.flag を書き込む
  - stop_requested.flag を置くと監視・実行ループを安全に停止できる
- DB
  - DuckDB：時系列・リサーチ用（デフォルト data/kabusys.duckdb）
  - SQLite：監視ログ・発注履歴（デフォルト data/monitoring.db、paper_trading 用は data/paper_trading.db）
  - monitoring_db.init_monitoring_db により監視用テーブルは冪等作成される
- AI 機能（OpenAI）
  - ニュースのセンチメントを LLM でスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（ai.regime_detector）
- ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

セットアップ
------------
1. 依存ライブラリをインストール（仮想環境推奨）
   - 必須（主なもの）:
     - python >= 3.10
     - duckdb
     - psutil
     - openai (AI 機能使用時)
     - PyYAML（config/*.yaml の検証を行う場合に必要）
   - 例:
     pip install duckdb psutil openai pyyaml

2. プロジェクトルートに data ディレクトリを作成（自動作成される場合もありますが手動で用意しておくと安心）
   mkdir -p data

3. 環境変数の準備
   - 推奨: 対話式ウィザードで .env を作成
     python -m kabusys.config_setup
   - 最小必須:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - 重要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視用 DB, デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用の専用 DB）
     - OPENAI_API_KEY: OpenAI を使う機能で必須
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: paper_trading 時の Fill 動作（instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1, 本番は 0 推奨）

4. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

使い方
-------
各主要コンポーネントはモジュール単位で起動できます。プロダクションでは supervisor/systemd 等で管理する想定です。

- 環境設定ウィザード（.env を生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（取引エンジン）
  python -m kabusys.run_execution
  動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - PID ファイルは data/execution.pid（デフォルト）に書かれます。
    - プロセス優先度を "high" に設定しようとします（psutil の権限次第で失敗する可能性があります）。

- Monitoring (SystemMonitor 単体起動)
  python -m kabusys.run_monitoring
  動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。
    - 監視は DB（sqlite）に記録します。monitoring は常に本番 sqlite_path を使用（環境に依らず）。
    - 停止は data/stop_requested.flag を作成すると検知してループを終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数:
    PAPER_TRADING_SQLITE_PATH で DB パスを指定できます（--db が優先）。

- AI 機能（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY を設定します。
  注意: API キーがない場合は ValueError が発生します。API 呼び出し失敗時は多くの場面でフェイルセーフ（0 でフォールバック）しますが、キーは必須です。

停止方法
---------
- 実行中の run_monitoring や run_execution を優雅に停止するにはプロジェクトルートの data/stop_requested.flag を作成してください。両スクリプトはこのファイルを定期的にチェックして停止します。
- 実行エンジン（ExecutionEngine）を外部条件で停止するための Kill Switch は監視が判定した場合に data/kill.flag を書き込みます。kill.flag は ExecutionEngine 側で検知して停止処理を行います。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番環境では推奨されません）。

ディレクトリ構成（主なファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py            — 対話式 .env 作成ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリング
    - regime_detector.py       — マクロ + MA200 によるレジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル作成・ログ）
    - monitoring_engine.py     — Monitor の束ね処理（Polling）
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py         — 注文滞留・約定価格異常の検出
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — （アラート送信の抽象。未表示部分）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py        — BrokerClient 作成（mock / real 切替）
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/                      — データ・DB・フラグファイルが置かれる（実行時生成）
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb

設計上の注意点 / 運用メモ
-------------------------
- .env は絶対にリポジトリにコミットしないでください（README や config_setup の注意に従う）。
- KABUSYS_ENV によって発注部分や DB の扱いが変わります。paper_trading は本番 DB と分離されるため検証に使いやすいです。
- OpenAI を利用する機能は API 呼び出しが発生するため、料金・レートリミット・レスポンスタイムを考慮してください。ライブラリ側でリトライ等の保護は入っていますが、運用監視は必要です。
- プロセス優先度や CPU affinity の設定は psutil の権限に依存します。権限不足時は警告が出てスキップされます。
- monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（列追加）を行います。既存 DB への影響は考慮されていますが、バックアップを推奨します。

例: 最小 .env（参考、必須項目は各自の値に置換）
------------------------------------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

サポート / 開発
----------------
- config_setup.py / validate_config.py を使って設定の品質を担保してください。
- unit tests や CI はここに含まれていませんが、各モジュールは関数単位で分割設計されているためテストが書きやすくなっています。
- AI 関連の関数（_call_openai_api 等）はテスト時にモック可能です（コード内にその旨の注釈あり）。

以上。必要であれば README に実行例（ログ抜粋や運用手順の詳細）を追加します。どの部分を詳しく追記しますか？