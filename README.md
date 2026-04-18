README
=====

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を想定した Python パッケージです。本コードベースは次の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行
- 監視コンポーネント: システム状況・取引状況・リスク監視、Kill Switch による停止制御
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ計算・セクター制限など
- リサーチ機能: ファクター計算（モメンタム/バリュー/ボラティリティ）・特徴量探索
- AI モジュール: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定
- 運用ツール: ペーパートレードの検証レポート生成、環境設定ウィザード、設定検証 CLI
- ユーティリティ: ロギング設定・プロセス優先度設定等

主な設計方針:
- DB は DuckDB（分析用）と SQLite（監視 / 発注履歴）を併用
- Paper Trading 環境は本番 DB と分離（data/paper_trading.db を使用）
- LLM 呼び出しは失敗時にフェイルセーフで継続する設計
- ルックアヘッドバイアスに注意し、日付解決は明示的引数で行う

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離。
  - run_monitoring.py: SystemMonitor を定期ポーリングして system_status 等を記録（MONITOR_POLL_INTERVAL で間隔変更可）。

- 設定関連
  - config_setup.py: 対話式で .env を作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - config.Settings: 環境変数ラッパー（必須値チェックやパス解決を含む）

- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - monitoring_db.MonitoringDB: SQLite に対する永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: kill.flag の書き込み/確認/クリア

- 発注・実行（execution） — ファクトリ/エンジン/注文管理/リスク管理（コアは起動スクリプトから組み合わせて起動）
- ポートフォリオ（portfolio）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（research）
  - factor_research: calc_momentum / calc_value / calc_volatility など
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（ai）
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースで市場レジーム判定
- ツール（tools）
  - paper_verification_report: ペーパートレード DB から PASS/FAIL 判定付きレポートを生成

セットアップ手順
---------------
前提
- Python 3.9+（型ヒントに Path | None 等が使われているため新しめを推奨）
- DB: ファイルベース（DuckDB/SQLite）を使用するため特別な外部 DB は不要

1. クローン / 配置
   - リポジトリをクローンし、作業ディレクトリをルートにする（pyproject.toml または .git をルート判定に使います）。

2. 仮想環境
   - 任意の仮想環境を作成して有効化してください。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須パッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - 実際の requirements.txt がある場合はそれを使用してください:
     - pip install -r requirements.txt

4. 環境変数 (.env) の作成
   - 対話式で作成する:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example があれば参照）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ログディレクトリ / DB ディレクトリ作成
   - デフォルトで logs/ と data/ を使用します。起動時に自動作成されますが、適切な権限を確認してください。

基本的な使い方
--------------
- 環境の初期化（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 成功すると exit code 0 を返します。

- ExecutionEngine の起動
  - 本番またはペーパーを設定した上で:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db を使用して本番 DB と分離します。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 起動中は data/execution.pid に PID を書き込みます。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（Monitor は環境に依存せず本番 sqlite_path を使う設計）。
  - 停止は data/stop_requested.flag を作成して検知させるか、プロセスを終了してください。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（デフォルト data/paper_trading.db）

- AI 関連（プログラム的呼び出し）
  - ニューススコア:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数で供給

- リサーチ関数の例（プログラム的呼び出し）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - calc_momentum(conn, target_date)

停止 / Kill Switch
------------------
- 実行ループの外部停止:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
- Kill Switch:
  - RiskMonitor 等の判定により KillSwitch が data/kill.flag を書き込むと、ExecutionEngine はそれを参照して停止シグナルを受け取れます。
  - Settings の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアできますが、本番では 0 を推奨します。

主要な環境変数（要点）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: OpenAI を利用する場合
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading のモック約定挙動: instant|partial|never|reject）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、"1" で有効）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定ラッパー
  - config_setup.py             — .env ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング
    - regime_detector.py        — 市場レジーム判定
  - monitoring/
    - monitoring_db.py          — SQLite テーブル作成 / 永続化 API
    - system_monitor.py
    - trade_monitor.py          — （trade_monitor 実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          — （アラート処理）
  - execution/
    - execution_engine.py       — 実行エンジン（起動時に組み立てる）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（注）一部ファイルはここに抜粋されていないか姉妹モジュールに依存します。上記は主要なモジュール構成の概要です。

運用上の注意・ベストプラクティス
------------------------------
- 本番（KABUSYS_ENV=live）で実行する前に必ず python -m kabusys.validate_config を実行して設定を確認してください。
- .env は絶対にリポジトリにコミットしないでください。
- logs/ に日次ローテーションのログが出力されます。ディスク容量監視を行ってください。
- OpenAI 利用時は API 呼び出し失敗に備え、rate limit とコスト管理を実施してください。
- Paper Trading は本番 DB と分離されますが、必要に応じて PAPER_TRADING_SQLITE_PATH を指定してください。

ライセンス・貢献
----------------
- 本リポジトリに LICENSE が含まれている場合はそちらを参照してください。
- バグ報告・機能改善は Issue / PR を通じてご提出ください。

サポートされるコマンド一覧（まとめ）
----------------------------------
- 環境作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。README に不足・追記してほしい項目（例: 実運用時の systemd ユニット例、詳細な設定例、API の追加ドキュメント等）があれば教えてください。