# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。戦略の研究・ファクター計算・ポートフォリオ構築・ポジションサイズ計算・実行エンジン・監視機能・AI によるニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存ライブラリ
- セットアップ手順
- 使い方（CLI / 実行例）
- 環境変数（主要項目）
- ディレクトリ構成（主要ファイルの説明）
- 運用メモ（監視・停止・ペーパートレードなど）

---

プロジェクト概要
- DuckDB / SQLite をデータストアに使い、価格データや財務データ、監視ログを保存・集計します。
- 戦略研究（ファクター計算・特徴量解析）、ポートフォリオ構築（候補選定・重み付け）、ポジションサイズ計算、リスク制御、注文管理（ExecutionEngine）を提供します。
- 監視サブシステムはプロセス状態、データ鮮度、注文滞留、ドローダウンなどをチェックし、必要に応じて LINE 通知や Kill Switch（停止フラグ）を発動します。
- OpenAI を使ったニュース NLP（センチメントスコア付与）や市場レジーム判定モジュールを組み込めます（API キー必須）。

主な機能
- 環境設定ウィザード（.env の対話的作成・更新）: `kabusys.config_setup`
- 設定検証ツール（.env と config/*.yaml のチェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト（実取引 / ペーパートレード切替）: `run_execution.py`
- Monitoring 起動スクリプト（定期ポーリング）: `run_monitoring.py`
- 監視機能群:
  - SystemMonitor: CPU/メモリ/Disk、プロセス PID、データ鮮度
  - TradeMonitor: 滞留注文、約定異常価格
  - RiskMonitor: ドローダウン・ポジション上限チェック
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み・LINE 通知
- ポートフォリオ構築ユーティリティ:
  - 候補選定、等重/スコア重み、セクター制限、レジーム乗数、株数決定（単元丸め／aggregate cap）
- 研究用モジュール:
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン・IC や統計サマリ
- AI モジュール:
  - ニュースセンチメント付与（OpenAI）
  - 市場レジーム判定（MA + マクロニュース + LLM）
- 解析ツール:
  - Paper Trading 検証レポート生成スクリプト

前提・依存ライブラリ
- Python 3.9+
- 必須（使用する機能に依存）:
  - duckdb
  - psutil
  - requests
- AI 機能を使う場合:
  - openai（OpenAI Python SDK、v1系）
- config YAML 検証（任意）:
  - PyYAML
- （※ requirements.txt があればそちらを参照してください）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を準備します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
2. 依存ライブラリをインストールします（例）:
   - pip install duckdb psutil requests openai PyYAML
   - （AI を使わない場合は openai は不要）
3. 環境変数を設定します:
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成する（プロジェクトルート）。主なキーは以下参照。
4. 設定検証（任意）:
   - python -m kabusys.validate_config
   - 問題がある場合は指摘メッセージに従って修正してください。
5. DB 初期化は各起動スクリプト内で自動的に行われます（init_monitoring_db を呼ぶ）。

使い方（実行例）
- 環境変数の例（.env）
  - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  - KABU_API_PASSWORD=your_kabu_station_password_here
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=sk-...
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - PAPER_FILL_MODE=instant
  - KILL_FLAG_CLEAR_ON_START=0

- 起動・操作コマンド
  - 環境ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - Strict モード（警告を失敗扱い）: python -m kabusys.validate_config --strict
  - 実行エンジン起動:
    - python -m kabusys.run_execution
      - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 監視ループ起動:
    - python -m kabusys.run_monitoring
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）。
      - 監視は常に本番の sqlite_path を参照します（KABUSYS_ENV に依らず）。
  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を指定する場合:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - AI モジュール（ニュースセンチメント / レジーム判定）
    - ニューススコア付与:
      - Python API から kabusys.ai.score_news を呼ぶ（DuckDB 接続と target_date を渡す）。OPENAI_API_KEY が必要。
    - レジーム判定:
      - kabusys.ai.regime_detector.score_regime を呼ぶ（DuckDB 接続と target_date を渡す）。OPENAI_API_KEY が必要。

主要な環境変数（要点）
- KABUSYS_ENV: execution 動作モード
  - development / paper_trading / live
  - paper_trading の場合、MockBrokerClient を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- OPENAI_API_KEY: OpenAI を使う場合（ai.news_nlp、regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログ出力レベル（INFO 等）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（デフォルト 0。本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種パスは Settings で取得可能（デフォルト data/ 以下）

運用メモ（監視・停止）
- 停止フラグ:
  - run_execution / run_monitoring はプロジェクト data ディレクトリ以下の停止フラグファイルを監視します（stop_requested.flag / data/kill.flag／経緯に応じたフラグ）。
  - KillSwitch は条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止を促します。
- PID ファイル:
  - ExecutionEngine は data/execution.pid を作成してプロセス存在チェックに使用します。SystemMonitor はこの PID を見てプロセスの稼働を判定します。
- 自動 .env 読み込み:
  - 起動時にプロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env` と `.env.local` を自動ロードします。
  - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LOG_LEVEL / クールダウン:
  - AlertManager は同一種の通知を一定期間で抑止（クールダウン、既定 30 分）します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス：環境変数読み込み・検証・自動 .env ロード
  - config_setup.py — 対話式 .env ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - data/（運用時に生成される想定）
    - *.db, *.pid, kill.flag, stop_requested.flag など
  - execution/ — Execution エンジン関連（OrderManager, BrokerFactory, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル作成・永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/Disk・PID・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE 通知クライアント（push）
  - portfolio/ — ポートフォリオ構築（候補選定・重み・ポジションサイズ・セクター制限・レジーム乗数）
  - research/ — ファクター計算・特徴量探索・IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py — MA + マクロニュース + LLM によるレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発時の補足
- DB スキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db 内で冪等に実行しています（存在確認 → ALTER を行う箇所あり）。
- DuckDB 接続は research / ai などの計算モジュールへ直接渡して SQL を実行する設計です（パフォーマンス重視）。
- AI 呼び出しでは JSON Mode を利用し、レスポンス検証・リトライ・スコアクリップを行っています（堅牢化実装）。
- process priority / CPU affinity はプラットフォーム差を吸収しており、権限不足時は警告を出してスキップします。

トラブルシューティング
- .env が自動で読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルートの検出（.git / pyproject.toml）に失敗していないかを確認してください。
- OpenAI 呼び出しで失敗する／スロットリングされる場合:
  - OPENAI_API_KEY の有効性、レート制限、ネットワーク状況を確認。モジュールはリトライとフォールバック（0.0）を実装しています。
- 実行スクリプトがすぐ終了する:
  - data/stop_requested.flag が存在していないか確認してください（起動直後にフラグがあると実行を開始せず終了します）。

ライセンス・貢献
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（無ければ管理者に確認してください）。
- 貢献方法については CONTRIBUTING.md がある場合はそちらを参照してください。

---

追加の質問や README の拡張（例: 開発ガイド、詳細な API リファレンス、ユニットテストの実行方法）をご希望であれば教えてください。README を用途に合わせて詳細化します。