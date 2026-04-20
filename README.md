README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のリポジトリです。  
主要機能は以下の通りです。

- 発注エンジン（ExecutionEngine）と監視（Monitoring）プロセスの分離実行
- ペーパートレード（モックブローカー）対応（設定で本番と分離）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を使ったオフライン研究）
- ニュース NLP を使った銘柄スコアリング / レジーム判定（OpenAI 統合）
- 監視ログ（SQLite）保存、Kill Switch による安全停止
- 設定ウィザード・設定検証・各種ユーティリティ

主な設計方針：
- 本番データベースとペーパートレードは分離（環境による）
- ルックアヘッドバイアスを避ける実装（date/time の扱いに注意）
- フェイルセーフ：API 失敗時はスキップやデフォルト値で継続

機能一覧
--------
- 実行（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視（run_monitoring.py / monitoring/*）
  - SystemMonitor, TradeMonitor, RiskMonitor を定期ポーリングしログ保存
  - KillSwitch により条件で data/kill.flag を書き込み ExecutionEngine を停止可能
  - MONITOR_POLL_INTERVAL で間隔を上書き（デフォルト 60 秒）
- ポートフォリオ（portfolio/*）
  - 候補選定、等重/スコア重み付け、リスク調整（セクター制限・レジーム係数）
  - ポジションサイズ計算（単元株丸め・利用キャッシュによるスケール調整）
- 研究（research/*）
  - DuckDB 接続でファクター（モメンタム・ボラティリティ・バリュー）を計算
  - 将来リターン・IC（Spearman）・統計サマリーのユーティリティ
- AI（ai/*）
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ銘柄ごとのスコアを ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロセンチメントを合成して market_regime に書込
- ツール（tools/paper_verification_report.py）
  - ペーパートレード DB からレポートを生成（稼働率・成立率・レイテンシ等）
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を作成
  - validate_config.py: 環境変数・config/*.yaml の検証
- ユーティリティ
  - logging_setup: コンソール + 日次ローテートログの設定（logs/）
  - process_priority: プロセス優先度 / CPU affinity の設定

セットアップ手順
---------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - （パッケージのルートには pyproject.toml または .git がある想定）

2. Python 仮想環境作成・有効化
   - 推奨: Python 3.10 以上（typing などの構文を使用）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（実行に必要な主要ライブラリ）:
     - duckdb, psutil, openai
   - 開発/任意:
     - PyYAML（config.yaml の構文検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt が無い場合は上記を個別にインストール）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザード後は .env に API トークン等が保存されます（.env は絶対にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: execution 環境 ("development" / "paper_trading" / "live")
  - paper_trading のとき execution は paper DB を使う
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパー注文の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

使い方（実行例）
----------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は paper DB を使用（本番 DB と分離）
    - data/stop_requested.flag を作ると実行スレッドは停止します
    - PID ファイル: data/execution.pid（設定で変更可能）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒）
  - 監視は Settings.sqlite_path を使用（環境にかかわらず本番 sqlite_path を参照）
  - 監視は logs/monitoring.log に出力（default）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - DB を指定する場合: --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も利用可能

- AI 機能
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - いずれも OPENAI_API_KEY が必要。失敗時はフェイルセーフで進む実装

ログ・データベース
-------------------
- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - logging_setup.setup_logging を各スクリプトで呼び出して統一設定

- データベース:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite 監視 DB: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
  - 監視 DB スキーマは monitoring/monitoring_db.init_monitoring_db で自動作成・マイグレーション

監視 / 安全停止（Kill Switch）
------------------------------
- RiskMonitor・SystemMonitor・TradeMonitor の結果を MonitoringEngine が集約
- KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み
- ExecutionEngine は起動時やループ中に kill.flag を検知すると安全に停止します
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 推奨）

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                    — 環境変数 / Settings 管理
    config_setup.py              — .env ウィザード
    validate_config.py           — 設定検証 CLI
    run_execution.py             — ExecutionEngine 起動スクリプト
    run_monitoring.py            — Monitoring 起動スクリプト

    execution/                   — 発注エンジン関連（broker, order_manager, engine など）
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py?
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    data/                        — データパイプライン・DuckDB 周り（prices_daily 等）
    ai/
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    utils/
      logging_setup.py
      process_priority.py

注意事項 / トラブルシューティング
---------------------------------
- .env を作成し忘れると必須環境変数が不足して起動できません。まず python -m kabusys.config_setup を実行してください。
- validate_config.py は PyYAML が無ければ YAML の内容検証をスキップします（インストールを推奨）。
- OpenAI を使用する機能は API キーと通信可能な環境が必要です。エラーはログに残り、処理は可能な範囲で継続します。
- MONITOR_POLL_INTERVAL に 0 や負値を設定すると無効値として 60 秒にフォールバックします（警告ログあり）。
- ログディレクトリ作成に失敗するとファイル出力が無効になりコンソールのみ出力されます（stderr に警告が出ます）。
- psutil によるプロセス優先度 / CPU affinity の設定が権限不足で失敗する場合は警告を出してスキップします。

ライセンス・貢献
----------------
- 本リポジトリのバージョンは __version__ = "0.1.0"（src/kabusys/__init__.py）。
- 貢献・バグ報告は PR / Issue でお願いします。

以上が README の要点です。実行や設定で不明点があれば、どのコマンドやどのファイル（例: run_execution.py）について詳しく知りたいか教えてください。