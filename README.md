KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための Python コードベースです。  
主要機能は戦略（ファクター計算）、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視（システム状態／リスク監視）、AI を用いたニュース評価・レジーム判定、ならびに運用支援ツール群です。

主な特徴
--------
- ExecutionEngine（発注エンジン）／Paper Trading をサポート
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による自動停止機能
- DuckDB（分析用）・SQLite（監視／トレードログ）を利用した永続化
- ニュースを LLM（OpenAI）で評価する AI モジュール（ニュースセンチメント、レジーム判定）
- Portfolio 構成・ポジションサイズ計算などの純粋関数群（テストしやすい設計）
- 起動用ユーティリティ：.env ウィザード、設定検証ツール、検証レポート生成スクリプト等
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）

セットアップ
-----------

1. Python とパッケージ
   - 推奨: Python 3.10+
   - 必要な外部ライブラリ（代表例）:
     - duckdb
     - psutil
     - openai (AI 機能利用時)
     - PyYAML（config YAML の詳細検証を行う場合）
   - 例: 仮想環境作成後にインストール
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt がない場合は上記を参考に依存をインストールしてください）

2. プロジェクトルートと .env
   - プロジェクトルート（.git または pyproject.toml がある階層）を基準に .env 自動読込を行います。
   - 初回は対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - 主要な任意 / 推奨変数:
     - KABUSYS_ENV: development | paper_trading | live（default: development）
     - DUCKDB_PATH: 分析 DB（default: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - OPENAI_API_KEY: OpenAI を使う機能利用時に必要
   - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

3. ディレクトリ・データ準備
   - デフォルトの DB / ログ / data ディレクトリは起動時に自動作成されますが、
     必要に応じて手動で作成しておくこともできます。
   - デフォルトファイル:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db (paper_trading 用)
     - logs/<app_name>.log

基本的な使い方
--------------

- 設定検証
  - .env と config/*.yaml の存在・基本整合性チェックを行う:
    - python -m kabusys.validate_config
    - --strict を付けると警告も失敗扱い（exit 1）になります

- 実行（ExecutionEngine）
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（ペーパートレード）が使われ、データは paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます
    - 起動時に data/stop_requested.flag が既に存在すると起動を回避
    - 実行中に同フラグを書き込むことでエンジンを停止可能

- 監視（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして監視ログを SQLite に保存
    - デフォルトポーリング間隔: 60 秒
      - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
      - 無効な値 (<=0 / 非数) はデフォルトにフォールバック
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - 停止はプロジェクトルート/data/stop_requested.flag の作成で検知

- Kill Switch（自動停止トリガ）
  - RiskMonitor / TradeMonitor / SystemMonitor の結果に基づいて KillSwitch が評価され、
    異常があれば data/kill.flag（デフォルト）を書き込みます。ExecutionEngine はこのファイルを検出して停止します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリア（本番では 0 を推奨）

- ロギング
  - setup_logging が全起動スクリプトで使用されています
  - 出力:
    - コンソール（stdout）
    - 日次ローテートファイル: logs/<app_name>.log（30 日分保持）
  - ログディレクトリは LOG_DIR 環境変数で上書き可能

- Paper Trading 検証レポート
  - ペーパートレード履歴を分析して PASS/FAIL 判定するスクリプト:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD --to YYYY-MM-DD
      - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - 報告内容: 稼働率、注文成功率、送信率、レイテンシ（P95）等

- AI（OpenAI）機能
  - ニュースを LLM でスコアリングして ai_scores に保存する関数:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（MA200 + マクロニュース LLM）:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはライブラリ関数として提供されており、環境変数 OPENAI_API_KEY で API キーを渡すか、引数で直接渡します
  - OpenAI SDK のエラーやレート制限はエクスポネンシャルバックオフ等でリトライする実装が入っています

主要スクリプト (実行コマンドまとめ)
---------------------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

注意事項・運用上のポイント
-------------------------
- 本番運用時 (KABUSYS_ENV=live) は環境変数の設定ミスが重大な結果を招くため validate_config によるチェックを行ってください。
- KILL_FLAG_CLEAR_ON_START は本番環境では 0 を推奨（自動クリアは危険）。
- .env は絶対にリポジトリにコミットしないでください。
- OpenAI を利用する機能は API コストが発生します。API キーは安全に管理してください。
- ローカルで複数インスタンスを動かす場合、使用する SQLite/DB のパスが衝突しないように注意してください。
- run_monitoring は監視用 DB（SQLITE_PATH）を常に使用します（KABUSYS_ENV に依存しない）ので、ペーパートレードと混在させたくない場合はパスを明示的に設定してください。

ディレクトリ構成
----------------
（主要なファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py                    — パッケージ定義・バージョン
  - config.py                      — Settings クラス（環境変数読み込み・自動 .env ロード）
  - config_setup.py                — .env 対話式ウィザード（CLI）
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py          — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py            — SQLite のスキーマ／DB 操作用ユーティリティ
    - system_monitor.py           — システム状態 / データ鮮度監視
    - trade_monitor.py            — （トレード監視ロジック）※詳細はコード参照
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みユーティリティ
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — （通知管理：LINE 等への送信を想定）
  - execution/
    - execution_engine.py         — 発注エンジンのエントリ（EngineConfig など）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数決定・集約キャップ処理
    - risk_adjustment.py          — セクター制約・レジーム乗数
  - research/
    - factor_research.py         — ファクター（Momentum/Value/Volatility）計算
    - feature_exploration.py     — IC 計算等の解析ユーティリティ
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

開発・拡張のヒント
-------------------
- 多くのロジックは純粋関数（副作用なし）で設計されており、ユニットテストが書きやすくなっています（例: portfolio/*.py, research/*.py）。
- DB 書き込み部分は monitoring_db.py のようにラッパーで抽象化されているため、テスト時にはメモリ上の SQLite 接続を渡すと良いです。
- OpenAI 呼び出しは内部で _call_openai_api が分離されているため、ユニットテスト時にパッチしてモックレスポンスを返すことができます。

ライセンス
---------
（本リポジトリに LICENSE ファイルがあればその記載に従ってください）

お問い合わせ
------------
コードの理解や運用方法について不明点があれば、該当モジュールのドキュメントコメント（docstring）を参照するか、開発チームにお問い合わせください。

--- 
この README はコードベースの主要点をまとめたものです。詳細はそれぞれのモジュールのソースと docstring を参照してください。