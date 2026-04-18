KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究／監視を目的とした Python ベースのコードベースです。本リポジトリは主に以下の機能群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う。paper_trading モードではモックブローカーで完全に分離された DB を使用します。
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク条件（ドローダウン等）を定期チェックし、Kill Switch（フラグファイル）やアラートを発生させます。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム調整など純粋関数群。
- リサーチ: DuckDB 上の時系列データを用いたファクター計算、将来リターン・IC 計算や特徴量探索。
- AI モジュール: ニュースの NLP（OpenAI）を用いたセンチメント集約、市場レジーム判定のラッパー。
- ユーティリティ: 設定管理、対話式 .env ウィザード、設定検証、ログ設定、プロセス優先度管理 等。
- ツール: Paper Trading の検証レポート生成スクリプト等。

主な特徴（機能一覧）
------------------
- 設定管理
  - .env の対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
  - 自動 .env ロード（OS 環境変数の優先、.env.local 上書き）
- 実行エンジン（run_execution.py）
  - 実口座（live）／ペーパートレード（paper_trading）モード対応
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク管理、オーダー管理、レコンシリエーションを統合
  - PID / stop フラグによる外部制御
- 監視（run_monitoring.py / MonitoringEngine）
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視）
  - TradeMonitor ／ RiskMonitor（滞留注文・価格異常・ドローダウン等）
  - KillSwitch による data/kill.flag 書き出し
  - ポーリング間隔の環境変数上書き（MONITOR_POLL_INTERVAL）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等の計算（DuckDB 使用）
  - 将来リターン（forward returns）や IC 計算、統計サマリー
- AI（OpenAI）連携
  - ニュースセンチメント集計（gpt-4o-mini 推奨）
  - 市場レジーム判定（ETF + マクロセンチメント合成）
  - API の呼び出しは堅牢なリトライ・バリデーション実装
- ロギング / 運用
  - 統一的な logging セットアップ（stdout + 日次ローテートファイル）
  - process priority / CPU affinity ユーティリティ
- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

前提（Prerequisites）
-------------------
- Python 3.9+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（config 検証で YAML 検査を行う場合）
- SQLite（組み込みモジュール）
- 環境に応じた kabuステーション 等のブローカー設定（実運用時）

セットアップ手順
---------------
1. リポジトリをクローン / コピー
   - プロジェクトルートは .git または pyproject.toml に基づいて自動検出されます。

2. Python 仮想環境を作成・有効化し、依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
   - （requirements.txt がない場合は必要なパッケージを個別にインストールしてください）

3. .env の作成（対話式ウィザード推奨）
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - ウィザードで作成された .env は Git にコミットしないでください。

4. 設定検証
   - 自動検証を実行して必須環境変数や DB パス等を確認します:
     python -m kabusys.validate_config
   - 警告を厳密扱いする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ初期化
   - デフォルトの DB / ディレクトリ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログディレクトリ: logs/（自動作成されます。環境変数 LOG_DIR で変更可）

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒。既定 60）
- PAPER_FILL_MODE（paper_trading の fill 動作: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（起動時に Kill Flag を自動クリアするか: 0/1）

使い方（起動・コマンド）
----------------------

- 設定ウィザード（.env 作成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid が作成されます。停止は stop フラグで行います（下記）。

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用します（環境に依らず）。
  - 停止は data/stop_requested.flag を作成することで検知して終了します。

- 強制停止 / Kill Switch
  - KillSwitch は一定の条件（ドローダウン超過等）で data/kill.flag を書き込みます。ExecutionEngine は kill.flag の存在を検出して停止できます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を上書き可。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）。
  - 直接モジュールをインポートして呼び出す（スクリプト化されている API 呼び出し関数を使用）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

運用上の注意
------------
- ログ: kabusys.utils.logging_setup.setup_logging により stdout + 日次ローテーションファイル（logs/<app>.log）へ出力されます。LOG_DIR でログディレクトリを変更可能です。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼び出しますが、権限によっては設定が失敗することがあります（警告ログ）。
- データ鮮度チェック: SystemMonitor は DuckDB の prices_daily 等を参照してデータ鮮度を判定します。データが不足していると警告/アラート対象になります。
- AI 呼び出し: OpenAI の呼び出しはリトライやレスポンス検証を行いますが、API キー・使用量には注意してください。
- .env の取り扱い: 機密情報（トークン・パスワード）は .env に入れ、絶対にバージョン管理に含めないでください。

ディレクトリ構成（主要ファイル）
-----------------------------
（プロジェクトの src/kabusys 配下を簡略化）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し・スコア保存）
    - regime_detector.py      — マーケットレジーム判定（MA200 + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・スケーリング
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等の計算
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリー
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化（system_status 等）
    - system_monitor.py       — システム稼働・データ鮮度監視
    - trade_monitor.py        — （滞留注文等の監視）※実装参照
    - risk_monitor.py         — ドローダウン等の監視
    - monitoring_engine.py    — 各 Monitor を束ねる実行エンジン
    - kill_switch.py          — フラグによる停止シグナル管理
    - alert_manager.py        — （アラート送信管理）※実装参照
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（起動/セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - data/
    - pipeline.py             — データ取得/最終日取得ユーティリティ 等
    - stats.py                — 正規化ユーティリティ等
  - utils/
    - logging_setup.py        — 統一ログ設定ヘルパ
    - process_priority.py     — プロセス優先度 / CPU affinity ヘルパ
    - __init__.py

（注）上記は主なファイル群の抜粋です。実際のリポジトリにはさらに実装ファイルや補助スクリプトが存在します。

開発 / テストのヒント
---------------------
- 設定検証（validate_config）は依存ライブラリがない場合でも基本チェックを実行します。PyYAML があれば config/*.yaml の構文検査も行います。
- AI を使った関数は外部 API に依存するため、ユニットテストでは _call_openai_api をモックすることを推奨します（各モジュールに注記あり）。
- DuckDB を用いたリサーチ関数は副作用が無く純粋関数的に設計されています。小規模な DuckDB テスト DB を用意して単体テストを行うと良いです。

追加情報 / トラブルシューティング
--------------------------------
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります（警告が出ます）。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）をチェックして安全終了します。手動停止は該当ファイルを作成してください。
- paper_trading モードは本番 DB と分離されています。開発・検証時はこちらを用いて安全に動作確認してください。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ にて管理されています（現在 0.1.0）。

問題の報告・貢献
----------------
バグ報告や機能改善の提案は Issue を作成してください。プルリクエスト歓迎です。

以上で README の概要となります。必要であれば、起動例、.env のサンプル全体、より詳しい運用手順（systemd ユニット、cron、Docker 化等）を追記できます。どの情報を追加しますか？