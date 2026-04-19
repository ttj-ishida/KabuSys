README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を含むモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）とその起動スクリプト
- 監視/アラート機構（Monitoring）とポーリングループ
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- ファクター計算・特徴量解析（Research）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- 設定ウィザード・設定検証ツール
- Paper Trading 用検証レポート生成ツール

目的は本番口座による取引と研究ワークフローを分離し、監視・リスク管理・レポーティングを備えた堅牢な自動売買基盤を提供することです。

主な機能
--------
- Execution:
  - 実際のブローカーまたは Paper Trading（モック）での発注処理（settings による切替）
  - RiskManager / OrderManager / Reconciler による発注管理と安全制御
- Monitoring:
  - システム資源（CPU/メモリ/ディスク）、データ鮮度、プロセス生存などの定期監視
  - Trade / Risk の監視（滞留注文、約定異常、ドローダウン等）
  - Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine に停止指示）
  - sqlite に監視ログを永続化（init_monitoring_db によりスキーマ自動作成・マイグレーション）
- Portfolio:
  - シグナルを基に候補選定、等金額/スコア加重配分、リスクベースの株数算出
  - セクター集中制限やレジームに応じた調整
- Research:
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）
  - 将来リターンや IC（Information Coefficient）などの統計ツール
- AI:
  - raw_news をまとめて OpenAI（gpt-4o-mini 等）に送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書込む
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定を行う
- ツール:
  - 環境設定ウィザード：python -m kabusys.config_setup
  - 設定検証：python -m kabusys.validate_config (--strict で警告も失敗扱い)
  - Paper Trading 検証レポート生成：python -m kabusys.tools.paper_verification_report

セットアップ
----------
前提
- Python 3.10+ を推奨（typing の一部表記等を使用）
- システムに duckdb, psutil などがインストール可能であること

依存ライブラリ（代表例）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証時に YAML 内容検証を行う場合に必要）

例: 仮想環境作成 & インストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil openai PyYAML

必要な環境変数（最小セット）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

主な任意・上書き可能な環境変数（デフォルト値）
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1, default 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

初期設定（.env 作成）
1. ウィザードで .env を作成（対話式で入力）
   python -m kabusys.config_setup
   → これによりプロジェクトルートに .env が保存されます（※ .env は Git にコミットしない）

2. 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

使い方
------
起動スクリプト
- 実行エンジンを起動（バックグラウンドや Supervisor 等で実行）
  python -m kabusys.run_execution

  挙動のポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をキャンセルします。
  - 実行中に data/stop_requested.flag を作成すると安全に停止処理を開始します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）

- 監視ループ起動
  python -m kabusys.run_monitoring

  挙動のポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境に依らず）
  - 停止は data/stop_requested.flag で検知

ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

AI 関連
- OpenAI を使用する機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY を設定する必要があります。
- API 呼び出しは失敗耐性（リトライ、フォールバック値）を備えていますが、料金・レートリミットに注意してください。

停止・Kill Switch
- Monitoring によって判定された重大なリスク（ドローダウン超過・ポジション上限超過 等）は data/kill.flag に理由を書き込みます。ExecutionEngine 側は kill.flag の存在を検知して停止できます。
- 開発時に誤って本番で kill.flag が残っていると起動しないため、KILL_FLAG_CLEAR_ON_START=1 を使って自動クリアできますが、本番では 0 を強く推奨します。

実運用上の注意
- KABUSYS_ENV=live の場合は設定（LINE 通知など）を慎重に確認してください。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（utils.logging_setup.setup_logging により自動設定）。

ディレクトリ構成
----------------
以下は主なファイル / モジュールのツリー（src/kabusys 以下）です。実際のプロジェクトルートは src/ を含む場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・Settings 管理（.env 自動ロード含む）
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリングループ起動スクリプト

    - utils/
      - __init__.py
      - logging_setup.py         # 共通ログ設定ユーティリティ
      - process_priority.py      # プロセス優先度 / CPU affinity ユーティリティ

    - execution/                 # 注文実行に関わる実装群（OrderManager 等 — 省略されたファイルあり）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py

    - monitoring/
      - monitoring_db.py         # monitoring 用 sqlite テーブル作成 / 永続化層
      - risk_monitor.py
      - system_monitor.py
      - trade_monitor.py         # （monitoring のトレード監視ロジック）
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py         # （アラート送信ロジック）

    - portfolio/
      - __init__.py
      - portfolio_builder.py     # 候補選定・重み算出
      - position_sizing.py       # 株数算出・スケーリング
      - risk_adjustment.py       # セクターキャップ・レジーム乗数

    - research/
      - __init__.py
      - factor_research.py       # Momentum / Volatility / Value 等
      - feature_exploration.py   # forward return / IC / 統計サマリ

    - ai/
      - __init__.py
      - news_nlp.py              # ニュース → OpenAI → スコア書込
      - regime_detector.py       # ETF MA200 + マクロニュースでレジーム判定

    - data/                      # 実行時生成される想定のディレクトリ
      - monitoring.db (default)
      - paper_trading.db (paper trading 用)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/                      # ログ出力先（デフォルト）

補足: 既存コード内の重要ファイル
- monitoring_db.init_monitoring_db: monitoring DB のスキーマ作成と簡易マイグレーションを行います
- run_monitoring / run_execution: 実行時のプロセス優先度設定・DB 接続・ポーリングループを含むエントリポイント
- news_nlp.score_news / regime_detector.score_regime: OpenAI 呼び出しを行い DuckDB に結果を書き込む

ライセンス / バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（本 README に含まれていない場合は別途追加してください）。

お問い合わせ / 開発メモ
---------------------
- 開発者向けには .env.example を用意しておくと便利です（README にある必須変数・推奨値を反映）。
- CI / デプロイ時は KILL_FLAG_CLEAR_ON_START の扱いや DB パスの設定を明確にしてください。
- OpenAI を利用するコードは API の変更により将来的に修正が必要になる可能性があります。API エラー時のフォールバックは実装されていますが、料金とレート制御には注意してください。

以上。必要があれば、README に含めるサンプル .env テンプレートや docker-compose 例、systemd ユニットファイルの例なども追加できます。どの追加情報が必要か教えてください。