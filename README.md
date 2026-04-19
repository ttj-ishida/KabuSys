KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・運用支援）です。  
主要コンポーネントは ExecutionEngine（発注実行）、Monitoring（システム / 注文 / リスク監視）、Research（ファクター計算・特徴探索）、Portfolio（候補選定・配分・リスク調整）および AI 補助（ニュースセンチメント／レジーム判定）です。  
本リポジトリは純粋関数スタイルで設計された計算ロジック、軽量な DB 永続化層、外部 API 呼び出しラッパーを含みます。

主な機能
--------
- ExecutionEngine
  - 本番（kabuステーション） / ペーパートレード（MockBroker）での発注実行（KABUSYS_ENV により切替）
  - 発注管理・オーダーリポジトリ・リスクマネージャ統合
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 注文の滞留・約定異常など監視（ソース内に実装）
  - RiskMonitor: ドローダウン・ポジション上限監視 / ダッシュボード更新
  - KillSwitch: 危険条件で data/kill.flag を書き込み ExecutionEngine に停止信号を送る
  - MonitoringEngine: 複数の Monitor をまとめてポーリング、アラート管理との連携
- 設定管理
  - .env 対話式ウィザード（config_setup.py）
  - 起動前チェック（validate_config.py）: 必須環境変数・パス・YAML 構文チェック等
- Portfolio construction
  - 候補選定、等比率 / スコア重み、ポジションサイズ算出（単元株丸め・キャップ・利用可能現金でのスケール等）
  - セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）など統計解析ユーティリティ
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM（gpt-4o-mini 等）でセンチメント化して ai_scores テーブルへ格納
  - regime_detector: ETF・ニュースを融合して日次市場レジームを判定して DB に格納
  - API 呼び出しはリトライ、バリデーション、フェイルセーフ（失敗時は中立扱い）を備える
- ツール
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを生成

セットアップ手順
----------------
1. 必要環境（主な例）
   - Python 3.10+
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config で YAML 検証を行う場合）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - プロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - ない場合は個別に:
     - pip install duckdb psutil openai PyYAML

4. 初期設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...
   - 注意: .env は絶対にリポジトリにコミットしないこと。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリ
   - デフォルトの DB / フラグ / PID / ログディレクトリは data/ と logs/（config で変更可）
   - 必要に応じて手動で作成するか、起動時に自動作成されることがある

基本的な使い方
--------------
- ExecutionEngine 起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
    - 例（ペーパートレード）:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
    - 例（ローカル開発）:
      - export KABUSYS_ENV=development
      - python -m kabusys.run_execution
  - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB とは分離されます。
  - 実行中は data/execution.pid に PID を書き込み、停止フラグ（data/stop_requested.flag）を検出すると停止します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - Monitoring は常に production（本番）用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存しない）。

- Kill Switch / 手動停止
  - data/kill.flag に理由文字列を書き込むと ExecutionEngine 側で停止シグナルとして検出できます。
  - 通常は Monitoring の KillSwitch が自動で書き込む（ドローダウンやポジション上限超過等）。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI 機能（OpenAI）
  - OPENAI_API_KEY を設定して news_nlp / regime_detector を利用
  - API 呼び出しはリトライ・バリデーション・スコアクリップを行う（失敗時はフェイルセーフ）

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject, デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ポーリング秒, デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（0/1）

ディレクトリ構成（抜粋）
---------------------
プロジェクトの主要モジュールを抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の読み取り / .env 自動ロードのロジック
  - config_setup.py
    - .env を対話的に作成・更新するウィザード
  - validate_config.py
    - 起動前検証 CLI（必須 env/パス/YAML 検証 等）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて挙動を切替）
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — 注文滞留/約定異常検出（参照）
    - monitoring_engine.py     — 各 Monitor を束ねる
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — アラート送信（LINE 等）との連携（参照）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数計算・キャップ・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — モメンタム/ボラ/バリュー計算（DuckDB 経由）
    - feature_exploration.py   — 将来リターン・IC / 統計サマリ
  - ai/
    - news_nlp.py              — ニュース -> センチメント（OpenAI）
    - regime_detector.py       — マクロ + MA によるレジーム判定（OpenAI 補助）
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成
  - utils/
    - logging_setup.py         — ログ初期化（stdout + 日次ローテーションファイル）
    - process_priority.py      — プラットフォーム横断のプロセス優先度設定

設計における重要ポイント
------------------------
- 安全性重視
  - AI 呼び出しや外部 API はリトライ / バリデーション / フェイルセーフを備え、例外で全体が止まらない設計。
  - Kill Switch により重大なリスク条件で自動停止が可能（本番でのワンボタン停止）。
- ルックアヘッドバイアス防止
  - 研究・AI モジュールは内部で datetime.today() を直接参照せず、target_date を明示的に渡す設計。
- 本番 / ペーパーの分離
  - ペーパートレード用 DB を分離し、実測データと本番データを混同しない。
- ロギングと運用性
  - 統一的な logging 設定（stdout + ローテートファイル）で運用ログを追跡可能。
  - プロセス優先度設定や PID ファイル、停止フラグなど運用に必要な機能を用意。

よくある実行例
--------------
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Monitoring 起動:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- コンポーネントレベルでさらに詳細な挙動や API（OrderRepository, ExecutionEngine, RiskManager 等）はソース内ドキュメントおよび docstring を参照してください。  
- 本 README はコードベースの主要点を要約したものです。運用前に必ず validate_config を実行し、.env の値と DB パス・ログ設定を確認してください。

ライセンス / バージョン
----------------------
- パッケージバージョン: src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

質問や追加で README に含めたい情報（例: systemd ユニット / Dockerfile / CI 手順など）があれば教えてください。必要に応じて追記します。