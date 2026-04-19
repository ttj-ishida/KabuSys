README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ用ライブラリ兼簡易システムです。本コードベースは
- 実行エンジン（ExecutionEngine）
- 監視サブシステム（Monitoring）
- ポートフォリオ構築ロジック（選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- LLM を使ったニュース／レジーム評価（OpenAI）
- 環境設定ウィザード・設定検証ツール
といった機能群を含みます。

主な設計方針：
- 本番/ペーパートレードを環境変数 KABUSYS_ENV によって切り替え（development / paper_trading / live）
- DB：分析用は DuckDB（DUCKDB_PATH）、監視・発注ログ等は SQLite（SQLITE_PATH、ペーパーは別ファイル）
- .env / 環境変数で設定を管理。config_setup による対話的生成、validate_config による検証が可能
- ログはコンソール（stdout）と日次ローテートファイル（logs/<app>.log）へ出力

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視ループ（run_monitoring.py / monitoring package）
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック、プロセス生存チェック
  - 注文滞留 / 約定異常等の監視、リスク監視（ドローダウン・保有上限）と Kill Switch（data/kill.flag）
  - アラート送信（LINE などのトークン設定で利用可能）
- ポートフォリオ構築（portfolio package）
  - 候補選定、等額/スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ適用・レジーム乗数
- 研究（research package）
  - DuckDB 接続を利用するファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計測、統計サマリ等
- AI ツール（ai package）
  - news_nlp: OpenAI でニュースをスコアリングして ai_scores に書き込む
  - regime_detector: MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
  - いずれも OPENAI_API_KEY の設定が必要
- ユーティリティ
  - config_setup: .env を対話的に作成・更新
  - validate_config: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 本プロジェクトで使用される主な外部依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML
     - またはパッケージ化されていれば: pip install -e .（プロジェクト配布形態により）

4. 環境変数の準備（.env）
   - 対話的に作る: python -m kabusys.config_setup
   - 手動で作る場合は .env に最低限以下を設定（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  (AI 機能を使う場合)
   - 注意: .env は決して Git にコミットしないでください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - data/ ディレクトリや logs/ は自動で作成されますが、必要に応じて権限を確認してください。

使い方
------
基本的な実行例と主要な環境変数を示します。

実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- KABUSYS_ENV の挙動:
  - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。本番 SQLite とは分離。
  - live: 本番接続（kabuステーション）を使う（KABU_API_PASSWORD が必要）
- 停止:
  - data/stop_requested.flag を作ると起動中のスクリプトは検知して終了します。
  - リスク条件で停止させたい場合は monitoring の KillSwitch が data/kill.flag を書き込みます。
- PID / Kill flag:
  - 実行時に data/execution.pid（デフォルト）へ PID を書く実装があるため、管理しやすくなっています。

監視ループ（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は本番 sqlite_path を使用（環境にかかわらず監視用は settings.sqlite_path）
- 監視ループの強制停止:
  - data/stop_requested.flag を作成して監視ループを終了できます。

環境設定ウィザード / 検証
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - strict モード: --strict

Paper Trading 検証レポート
- 生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

AI 機能（ニュース NLP / レジーム判定）
- 必要: 環境変数 OPENAI_API_KEY（または引数で渡す）
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け、ai_scores / market_regime テーブルへ書き込みます。
- 直接使う場合は、DuckDB に prices_daily / raw_news 等のテーブルが存在し最新データが入っている必要があります。

設定（主な環境変数／.env）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログファイル格納ディレクトリ、default: logs)
- OPENAI_API_KEY (LLM 機能利用時)
- MONITOR_POLL_INTERVAL (監視ループ間隔秒、default: 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアするか。1=クリア、0=クリアしない)

運用上の注意
- process_priority の設定は OS・権限に依存します。set_process_priority("high") は権限不足で警告になりますが処理は継続します。
- ログディレクトリの作成に失敗した場合はコンソールログのみ動作します。
- AI 機能は API 呼び出しの失敗を許容する設計でフォールバック値を使うため、例外でプロセスが強制終了されることは基本的にありません。
- Kill Switch（data/kill.flag）は本番環境での誤作動を避けるため、KILL_FLAG_CLEAR_ON_START=0 を推奨。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパー検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 実行関連（ブローカーファクトリ等、詳細実装）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文・約定の監視（ファイル内に実装あり）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定（ロット丸め・aggregate cap）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロニュース）
  - data/                    — デフォルトで使用される DB / flag / PID 等の格納先（実行時に生成）
  - logs/                    — ログファイル置き場（デフォルト）

（上記は代表的なファイル。細部の実装は各サブパッケージ内を参照してください。）

サンプルコマンドまとめ
--------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動（ポーリング）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

補足
----
- DuckDB / SQLite に対するスキーマやテーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）は、実行する処理に応じて事前に用意／投入する必要があります（データパイプライン側実装があることが前提）。
- 本 README はコード内の docstring / コメントを基に要点をまとめたものです。実運用前に validate_config やユニットテストで動作確認してください。

この README で足りない点や、特定のモジュール（例: ExecutionEngine の設定項目、BrokerClient 実装、monitoring.alert_manager の送信先設定等）について詳しいドキュメントが必要であれば、知りたい箇所を指定してください。