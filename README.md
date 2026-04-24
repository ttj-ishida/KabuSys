README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）などの主要コンポーネントを含みます。設計方針として「本番 DB とペーパートレードの分離」「ルックアヘッドバイアスの回避」「フェイルセーフ（API 失敗時に安全なデフォルトで継続）」を重視しています。

主な機能
--------
- 実行エンジン（ExecutionEngine）:
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker を含む）
  - リスク管理（ポジション上限、ドローダウン、レート制限等）
- 監視（Monitoring）:
  - システム状態（CPU/メモリ/ディスク）監視
  - 注文ログ・約定の監視（滞留注文、異常約定等）
  - リスクモニタ（ドローダウン、ポジション上限）と Kill Switch（停止フラグ）
  - 定期ポーリングエンジン（監視ループ）
- ポートフォリオ構築:
  - 候補選定、等金額／スコア加重、リスクベースの株数決定
  - セクターキャップ適用、レジーム乗数
- リサーチ:
  - モメンタム、ボラティリティ、バリュー等ファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携:
  - ニュース記事からの銘柄別センチメントスコア生成（news_nlp）
  - マクロニュースと ETF（1321）の MA を組み合わせた市場レジーム判定（regime_detector）
- ユーティリティ:
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型ヒント等を使用）
- pip が利用可能

1. リポジトリをクローン / 展開する。

2. 必要な依存ライブラリをインストールする（最低限の例）。
   - duckdb（分析用 DB）
   - psutil（システム情報・プロセス操作）
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config の YAML 検証を使う場合）
   例:
   pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本コードでは明示されていません）。

3. .env の作成:
   対話式ウィザードを使用して .env を作成できます。
   python -m kabusys.config_setup

4. 設定検証（任意だが推奨）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリ等の作成:
   デフォルトで data/ と logs/ を使用します。起動時に自動作成される場合もありますが、権限等で失敗することがあるため必要に応じて手動で用意してください。

重要な環境変数（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に書き込みます
- OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db） — Monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。0 以下や不正値はデフォルトにフォールバック。
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）

使い方（主要 CLI / 起動方法）
----------------------------
- .env 作成（対話式ウィザード）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン開始
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレードモード（MockBrokerClient）となり data/paper_trading.db を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）を作ることで行えます。

- 監視ループ開始
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログを本番 DB に集約する設計）。
  - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます（デフォルト data/paper_trading.db）。

- AI 関連（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してください（.env に記載）。
  - モジュール関数を呼んで利用します（スクリプト経由のラッパーはないため、適宜スクリプトを作成して呼び出すか、既存の工程から呼ぶ設計です）。
  - OpenAI API 呼び出しはリトライ・バックオフ等を備えますが、API キーが未設定なら例外になります。

停止・Kill Switch
-----------------
- 実行エンジン / 監視は data/stop_requested.flag を検知して自己終了します（停止フラグ）。
- KillSwitch（監視側のリスク判定により）:
  - 条件に応じて data/kill.flag（パスは Settings.kill_flag_path）を書き込みます。ExecutionEngine はこの kill.flag を検出して停止する仕組みを持ちます。
  - Kill Switch はドローダウンやポジション上限などの重大リスクで作動します。KILL_FLAG_CLEAR_ON_START の取り扱いに注意してください（本番では自動クリアを無効にすることを推奨）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一的に行います。
- デフォルトのログディレクトリ: logs/
- 各アプリ（execution/monitoring 等）は app_name を指定して日次ローテートファイル（<log_dir>/<app_name>.log）に出力します。
- 環境変数 LOG_DIR / LOG_LEVEL で挙動を調整できます。

ディレクトリ構成（主なファイル）
------------------------------
以下はパッケージ内の主要ファイル一覧（提供されたコードファイルに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI でセンチメント解析）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite を使った監視 DB 層
    - monitoring_engine.py    — 個別モニタを束ねるエンジン
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （該当ファイルが存在する想定: 注文/約定監視）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch（flag 書き込み）
    - alert_manager.py        — （アラート送信管理、LINE 等を想定）
  - execution/
    - broker_factory.py       — ブローカークライアント生成
    - execution_engine.py     — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ... (実装ファイル群)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

注意事項 / 運用メモ
------------------
- 監視は常に SQLITE_PATH（monitoring.db）を参照します。監視ログは本番の監視 DB に集約する設計です。
- ペーパートレードは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録され、本番 DB と分離されます。
- ローカルの .env は絶対にリポジトリにコミットしないでください（config_setup でもその旨を出力します）。
- OpenAI を利用する処理は API 利用料が発生します。キー管理と利用頻度に注意してください。
- process_priority 等は OS によって動作しないケースや権限不足で失敗する可能性があります（ロギング上で警告されます）。
- validate_config は PyYAML が無い場合に YAML 検証をスキップします。可能であれば PyYAML を入れて設定ファイルの妥当性を確認してください。

開発 / 拡張
------------
- モジュール単位でのユニットテストを追加してください（特にポートフォリオ計算、ポジションサイジング、AI レスポンスのパース）。
- OpenAI 呼び出し部分はテスト容易性のため外部呼び出し関数をモック可能な実装にしています（ユニットテスト時は該当関数をパッチしてください）。
- 将来的に銘柄ごとの単元株数（lot_size）を銘柄マスタ化するといった拡張がコメントに示唆されています。

以上がリポジトリの概要・セットアップ・使い方およびディレクトリ構成の説明です。必要であれば .env.example のサンプルや systemd / Supervisor 用の起動スクリプト例、よくあるトラブルシューティング項目を追加で作成します。どのドキュメントを次に整備したいか教えてください。