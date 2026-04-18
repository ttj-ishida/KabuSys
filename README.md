KabuSys — 日本株自動売買システム
================================

この README はこのリポジトリ（src/kabusys 以下）の主要コンポーネントと使い方をまとめたものです。
README は技術ドキュメント向けに日本語で簡潔にまとめています。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買／リサーチ基盤です。主要な機能は以下を含みます。

- 日次・リアルタイム監視（System / Trade / Risk）
- ExecutionEngine（発注管理、リスク制御、ブローカー抽象化）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC評価）
- AI 支援モジュール（ニュースセンチメント解析、レジーム判定） — OpenAI を利用
- Paper Trading 用の分離された DB / モックブローカー
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証、検証レポート生成）

主な機能一覧
-------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env, .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行系
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading を区別）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、プロセス生存チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常、ドローダウン・ポジション数監視
  - KillSwitch: 条件を満たしたら data/kill.flag を書いて Execution を停止
  - MonitoringDB: SQLite に監視ログを永続化
- ポートフォリオ（portfolio）
  - 銘柄選定、等配分/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元丸め、aggregate cap）
- リサーチ（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー
- AI（ai）
  - news_nlp: raw_news を集約して OpenAI に送信し ai_scores を書き込む
  - regime_detector: マクロ記事 + ETF ma200 乖離で市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（型表記に | が使われているため）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML の内容検査を行う場合）
- 仮想環境の作成を推奨（venv / poetry / pipenv 等）

インストール例（概略）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 依存関係をインストール（requirements.txt があればそれに従う）
  - pip install duckdb psutil openai
  - 必要に応じて PyYAML 等を追加

初期設定
1. .env を作成する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参考）
   - 注意: .env は絶対に Git にコミットしないこと

2. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

3. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
   - KABU_API_PASSWORD（kabuステーション API パスワード）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - その他（DUCKDB_PATH, SQLITE_PATH 等はデフォルトあり）

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- LOG_LEVEL, LOG_DIR: ログレベル / ログディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: PID・kill flag のパス（必要に応じて上書き）

使い方
------

基本的な起動方法（簡易）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - run_monitoring は停止フラグ data/stop_requested.flag を検知するとループを終了します

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading.db に記録します（本番 DB と分離）
  - 実行中に data/stop_requested.flag が作成されるとエンジンに停止を要求します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば kill.flag を自動クリアします（本番では 0 推奨）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一されています
- デフォルトは logs/<app_name>.log（日次ローテーション、30日分）
- コンソール出力は stdout に出ます（cron / scheduler と親和性を持たせるため）

停止・Kill Switch
- KillSwitch は RiskMonitor 等の判定で条件を満たすと data/kill.flag を書き、
  ExecutionEngine が起動中であれば停止を促します
- 手動で停止する場合やテスト用に data/stop_requested.flag を作成すると run_* スクリプトが検知して停止します
- stop_requested.flag と kill.flag はプロジェクトルート直下の data/ ディレクトリに置かれます（パスはコード内で設定）

注意点 / 運用上の留意点
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知等の設定を確認してください
- .env は機密情報を含むため絶対にバージョン管理に含めないでください
- OpenAI API を使う機能は API キーやコストに注意してください。API 失敗時にはフォールバックロジックがありますが、振る舞いを理解してから運用してください
- run_monitoring は監視 DB（SQLITE_PATH）に書き込みを行います。monitoring は原則として本番 sqlite_path を使用します（コードの仕様）

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 配下の主要ファイル／パッケージの概観です（この README の作成時点での実装に基づく）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理、自動 .env ロード
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP（OpenAI）
      - regime_detector.py      — 市場レジーム判定（OpenAI を利用）
    - monitoring/
      - monitoring_db.py        — SQLite テーブル定義・ラッパー
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — 注文 / 約定監視（存在）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 管理
      - monitoring_engine.py    — 複数監視を束ねるエンジン
      - alert_manager.py        — アラート送信（LINE など、実装参照）
    - execution/
      - execution_engine.py     — ExecutionEngine 本体（発注ループ等）
      - broker_factory.py       — BrokerClient の生成（実ブローカ / モック切替）
      - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
    - portfolio/
      - portfolio_builder.py    — 銘柄選定・重み付け
      - position_sizing.py      — 株数決定・aggregate cap
      - risk_adjustment.py      — セクター上限・レジーム乗数
    - research/
      - factor_research.py      — momentum/value/volatility 等のファクター計算
      - feature_exploration.py  — 将来リターン・IC・統計
    - utils/
      - logging_setup.py        — 共通ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity 設定
      - __init__.py
    - data/                      — 実行時に使う file-based flag / DB の既定場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）

ドキュメント補足 / 参照先
- コード内コメント（docstring）が実装の設計方針や注意点を多く含んでいます。各モジュールの先頭 docstring を参照してください。
- .env の雛形や config/*.yaml は scripts/generate_config.py 等で生成できる可能性があります（リポジトリの補助スクリプトを確認してください）。

トラブルシューティング（よくある項目）
- .env が読み込まれない:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが .git や pyproject.toml で検出されない場合、自動ロードはスキップされます
- OpenAI 呼び出しの失敗:
  - 環境変数 OPENAI_API_KEY が設定されているか
  - ネットワーク / レート制限によりリトライが発生します。ログを確認してください
- ログファイルが作成されない:
  - LOG_DIR 権限・パスを確認。logging_setup はディレクトリ作成に失敗した場合はコンソール出力のみで継続します

最後に
-------
この README はコードベースの主要点を要約したドキュメントです。詳細な仕様やアルゴリズム（PortfolioConstruction.md 等）や運用手順が別途ある場合はそちらを参照してください。質問や追加のドキュメントが必要であれば、どの部分を詳しくしたいか教えてください。