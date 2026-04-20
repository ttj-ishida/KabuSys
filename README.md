KabuSys
======

日本株自動売買システムのライブラリ / ランタイムスクリプト群。  
このリポジトリには取引実行エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築・リスク制御ロジック、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などの主要機能が含まれます。

概要
----
KabuSys は以下を目的としたモジュール群を提供します。

- 日次の銘柄選定と配分（Portfolio construction）
- 発注・注文管理・リスク制御を行う ExecutionEngine（本番 / ペーパートレード分離）
- システム稼働状況・注文状況を監視してアラート・Kill Switch を起動する Monitoring
- DuckDB を用いたリサーチ／ファクター計算モジュール
- OpenAI を使ったニュースのセンチメント解析・市場レジーム判定（任意）
- 各種ユーティリティ（ログ設定、プロセス優先度など）
- ペーパートレード検証レポート生成ツール

主な機能一覧
-------------
- 実行環境管理（Settings）
  - .env / .env.local を自動ロード（無効化可能）
  - KABUSYS_ENV により development / paper_trading / live を切替
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（paper_trading 時は MockBroker を使用し DB を分離）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
- 監視機能
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor：ドローダウンやポジション上限の監視・ログ記録
  - KillSwitch：重大事象で data/kill.flag を書き実行エンジンを停止
  - MonitoringEngine：上記を束ねて定期実行、アラート発行
- ポートフォリオ構築（純粋関数群）
  - select_candidates / calc_equal_weights / calc_score_weights
  - セクター制限、レジーム乗数適用
  - position sizing（単元株で丸め、aggregate cap スケーリング）
- リサーチ（DuckDB 前提）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（OpenAI）
  - ニュース NLP（raw_news -> ai_scores）
  - レジーム判定（ETF MA200 とマクロニュースのセンチメント合成）
  - いずれも OPENAI_API_KEY が必要（任意機能）
- ツール
  - config_setup.py：対話式 .env ウィザード
  - validate_config.py：起動前検証（必須環境変数・ファイルの有無など）
  - tools.paper_verification_report：ペーパートレード検証レポート生成

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... または適切に展開

2. Python 環境（推奨）
   - Python 3.10 以上（型注釈のパイプ型等を使用）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 最低限（機能に応じて追加）
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を有効にする場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt が用意されている場合は pip install -r requirements.txt を使用）

4. 環境変数設定 (.env)
   - 対話式ウィザードで初期 .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OPENAI_API_KEY は AI 機能利用時に必要
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB)
     - その他は config_setup のプロンプト参照
   - 自動ロードの無効化:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合: python -m kabusys.validate_config --strict

使い方
------
基本的にパッケージの起動スクリプトをモジュール実行します。

1. ExecutionEngine を起動（本番 / ペーパートレード共通インターフェース）
   - python -m kabusys.run_execution
   - 動作概要:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に接続して本番 DB とは分離します。
     - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
     - 起動中に同ファイルが作成されると実行エンジンは安全に停止します。
   - 停止方法:
     - stop：プロセスに対する通常のシグナル（Ctrl+C）または data/stop_requested.flag を作成
   - PID ファイル:
     - 実行中は data/execution.pid（デフォルト）に PID を出力

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 動作概要:
     - SystemMonitor をポーリングし system_status / trade_logs / risk_logs / dashboard を更新
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
     - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用する点に注意
   - stop: data/stop_requested.flag を作成すると監視ループが終了

3. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH より優先して DB を指定）
   - 出力: 標準出力に検証結果（稼働率、注文成功率、レイテンシ等）

4. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
   - モジュール:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - リトライ・フェイルセーフ実装あり。API 失敗時は基本的にスコアを 0（中立）として継続します。

5. 設定読み込みの挙動（Settings）
   - Settings クラスは .env/.env.local をプロジェクトルートから自動読み込み（OS 環境 > .env.local > .env）
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db） — Monitoring 用
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- PAPER_FILL_MODE（paper_trading の MockBroker の挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0 推奨）

停止 / Kill Switch
------------------
- 手動停止（Execution / Monitoring）:
  - data/stop_requested.flag を作成するとループが検知して終了します
- 自動停止（リスクによる Kill Switch）:
  - Monitoring 内の KillSwitch が data/kill.flag を作成すると ExecutionEngine に停止信号を送ります（ExecutionEngine は kill.flag を監視し停止します）
  - 本番で KILL_FLAG_CLEAR_ON_START=1 は危険（デフォルト 0）

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging によって統一設定されます
- デフォルトログディレクトリ: logs/
- ログファイル名は app_name に応じて logs/<app_name>.log（日次ローテーション・30 日保持）
- コンソール出力は stdout

ディレクトリ構成（抜粋）
---------------------
（主要ファイルを示した簡易ツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py  (参照: TradeMonitor 実装あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py  (通知周り)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
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
    - data/   （ランタイムで生成される想定のディレクトリ）
      - monitoring.db (デフォルト)
      - paper_trading.db (ペーパートレード)
      - kabusys.duckdb (DuckDB)
      - stop_requested.flag
      - kill.flag
      - execution.pid
- logs/  （ログ出力先・自動生成）

開発・運用のヒント
------------------
- 開発環境では KABUSYS_ENV=development にして外部発注を行わない設定にしておくと安全です。
- ペーパートレードは本番 DB と完全に分離されるよう PAPER_TRADING_SQLITE_PATH を使用してください。
- validate_config.py を CI に組み込み、必須環境変数や config/*.yaml の欠落を事前に検出することを推奨します。
- AI 機能を利用する場合は API コストやレート制限に注意してください（モジュールにリトライ/バッチ化ロジックあり）。
- DuckDB を使ったリサーチは大量データを高速に処理できるため、バックテスト・ファクター開発に便利です。

ライセンス、貢献
----------------
- 本リポジトリのライセンス・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

お問い合わせ
------------
問題報告や実装上の不明点は README の ISSUE 手順に従って Issue を作成してください。