# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（モジュール群）。  
このリポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース NLP などの機能を含むコンポーネント群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数一覧（主要）
- 実行時の停止 / Kill Switch の動作
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのモジュール群です。取引実行（ExecutionEngine）、モニタリング（System / Trade / Risk）、ポートフォリオ構築関数群、リサーチ（ファクター計算／特徴探索）、およびニュースの NLP スコアリング（OpenAI を使用）を提供します。
- 実行用 DB に SQLite を、分析用 DB に DuckDB を使用します。
- Paper Trading（シミュレーション）モードをサポートし、本番 DB とロジックを分離して動作できます。

---

機能一覧
- Execution
  - ExecutionEngine を起動してブローカーへ発注（本番/ペーパー切替可能）
  - 注文管理、リスク管理、再整合（reconciler）等
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在確認、データ鮮度監視
  - TradeMonitor: 注文滞留、約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - MonitoringEngine: 上記モニタを束ねポーリング、AlertManager 経由で LINE へ通知
  - KillSwitch: 条件を満たすと kill.flag を書き込み ExecutionEngine を停止
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア重み配分、リスク調整（セクター上限、レジーム乗数）、株数算出（単元処理、スケーリング）
- Research（リサーチ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメントスコアを生成して ai_scores に保存
  - 市場レジーム判定（ETF MA200 とマクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト

---

セットアップ手順（ローカル開発向け）
1. Python 環境を作成する（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）
     - pip install duckdb psutil openai requests PyYAML
   - 実際の環境ではプロジェクトに requirements.txt があればそれを使用してください。

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードで生成される .env はプロジェクトルートに保存されます（Git にコミットしないでください）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - 監視用 SQLite / DuckDB は起動スクリプトが初回にテーブルを作成します。手動操作は不要です。

注意:
- config モジュールはプロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- OpenAI を使う機能（ニュース NLP / regime_detector）は OPENAI_API_KEY の設定が必要です。

---

主要な環境変数（抜粋と説明）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使い paper_trading 用 DB へ記録
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）SQLite（デフォルト data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動消去するか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。無効値はデフォルトにフォールバック。

---

実行例（使い方）
- 実行エンジンを起動（本番 / paper_trading は環境変数 KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 起動前に stop フラグ（data/stop_requested.flag）が存在すると起動せず終了します。
  - 起動中は data/execution.pid に PID を書きます（実装上の挙動）。
  - paper_trading モードでは MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録されます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
  - run_monitoring はモニタリング用に Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します（KABUSYS_ENV に依存しません）。
  - 停止指示はプロジェクトルートの data/stop_requested.flag を作成すると監視ループが終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニュース NLP / regime 判定）
  - OPENAI_API_KEY を設定の上、該当モジュール（kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime）を呼び出してください。
  - これらは DuckDB 接続と target_date を引数に取る関数 API です。

---

停止・Kill/pause の仕組み
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring の外部停止フラグ（存在するとループが終了）
  - data/kill.flag: KillSwitch が発動すると作成され、ExecutionEngine に対する停止要求（ExecutionEngine 側で参照する仕組み）
- KillSwitch は RiskMonitor の結果（ドローダウン超過、ポジション上限超過等）により kill.flag を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を消去します（本番では 0 を推奨）。

---

注意事項 / 実運用メモ
- run_monitoring は監視のために本番 monitoring DB（Settings.sqlite_path）を使用します。paper_trading でも変更されません。
- Paper Trading は発注処理を模擬しますが、各種ロジック（ポートフォリオ計算、リスク制御など）は本番と同等に実行されます。
- OpenAI 連携部分は API コスト・レスポンス不安定性を考慮してリトライやフォールバック（失敗時に 0.0）等を実装していますが、運用時は API キー管理とレート制御に注意してください。
- psutil でプロセス優先度 / CPU affinity を操作します。権限不足や未対応 OS の場合は警告が出てスキップされます。

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                 — 実行エンジン関連（OrderManager, RiskManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化・永続化ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py        — 市場レジーム判定（MA + LLM）
  - monitoring/                 — （上に記載）
  - tools/
    - paper_verification_report.py
  - data/                       — デフォルトで DB/フラグ等を置く想定のディレクトリ（実行時に作成される）
  - その他：order_repository, order_manager, reconciler, etc.（execution 以下）

---

よくあるトラブルと対処
- .env を作成しても Settings が読み込まれない
  - プロジェクトルートの判定は .git または pyproject.toml を基準にしています。パッケージ配布後や別フォルダから実行する場合、環境変数を直接 export するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って手動で設定してください。
- OpenAI 呼び出しが失敗する
  - OPENAI_API_KEY が正しく設定されているか確認。API レートやネットワーク障害の可能性もあるためログを確認してください。
- run_execution がすぐ終了する
  - data/stop_requested.flag や data/kill.flag が存在していないか確認してください。

---

貢献・拡張のヒント
- BrokerClientFactory を拡張して別のブローカー実装を追加可能
- Portfolio / Position Sizing は純粋関数群なのでテストと改善が容易
- AI 部分は API レートやプロンプト改良で性能改善が行えます
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）を更新する際は research / ai のクエリを合わせて更新してください

---

ライセンス / コントリビューション
- 本 README はコードベースの説明を目的としたドキュメントです。実際のリポジトリにはライセンスファイルを配置してください。

以上。運用や導入で不明点があれば使用するモジュール名やエラーログを添えて質問してください。