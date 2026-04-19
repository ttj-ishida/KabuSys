KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・調査・監視を目的とした小規模なシステムです。
主要コンポーネントは以下の通りです。

- ExecutionEngine: 発注・注文管理・リスク管理（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文状況・リスク監視、Kill Switch（停止フラグ）
- Research / Portfolio: ファクター計算・ポートフォリオ構築・ポジションサイジング
- AI モジュール: ニュースセンチメント（OpenAI）を用いたスコアリング / レジーム判定
- Tools: ペーパートレード検証レポート生成など

特徴
----
- 環境変数 / .env による設定管理（config_setup による対話式ウィザード）
- 本番用とペーパートレード用 DB の分離（PAPER_TRADING モード）
- DuckDB（分析用）と SQLite（監視・履歴）を併用
- psutil によるプロセス優先度設定 / リソース監視
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定（任意）
- ログは標準出力 + 日次ローテーションで logs/<app>.log に保存

前提条件
--------
- Python 3.10+
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- 環境に合わせた設定（下記参照）

セットアップ手順
--------------
1. リポジトリをクローン／チェックアウトする

2. Python 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを利用）
   - pip install duckdb psutil openai PyYAML

4. 対話式設定ウィザードで .env を作成
   - python -m kabusys.config_setup
   これにより .env に主要な環境変数が書き込まれます。必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   その他:
   - KABUSYS_ENV (development | paper_trading | live)
   - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
   - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証
   - python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

使い方
------

基本的な起動例
- ExecutionEngine を起動
  - 本番または開発モード
    - KABUSYS_ENV を .env で設定してから:
      - python -m kabusys.run_execution
  - ペーパートレード（DB が分離され、MockBroker を利用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 監視モジュールは Settings の env にかかわらず本番 sqlite_path を使用する点に注意

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

停止・Kill スイッチ
- 停止フラグ（外部からの強制停止）:
  - data/stop_requested.flag : run_execution / run_monitoring のループ停止に利用
  - data/kill.flag : KillSwitch による ExecutionEngine 停止トリガー（監視側が書き込む）
- 実行中の ExecutionEngine は data/execution.pid（デフォルト）に PID を書きます

設定／環境変数の主要項目
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要:
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（paper_trading 時）
  - OPENAI_API_KEY: AI 機能を利用する場合に必要
  - LOG_LEVEL / LOG_DIR
- Monitoring での上書き:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

ログ
----
- ログは stdout に流れると共に logs/<app_name>.log に日次ローテーション（30日分保持）されます。
- setup_logging() が全起動スクリプトで呼ばれるため、ログの書式・出力先は一貫しています。

主なコマンドまとめ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要）
---------------------
（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み & Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （LINE など通知管理）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py
  - tools/
    - paper_verification_report.py
- data/                      — データファイル (SQLite, PID, flags 等)
- logs/                      — ログ出力先（デフォルト）
- config/                    — 各種 YAML テンプレート（system_config.yaml 等）

注意事項・運用メモ
-----------------
- KABUSYS_ENV=paper_trading の場合、Execution は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
- Monitoring の monitoring_db (SQLite) は監視用に本番 sqlite_path を参照します（環境に依らず本番 DB を利用する設計）。
- OpenAI や外部 API 呼び出しはネットワークエラー／API 失敗に対してリトライやフォールバック処理を行う設計ですが、API キー未設定の場合は該当機能は使えません。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。

開発者向け
----------
- DuckDB を用いた解析関数（research/*）は副作用を持たず、DuckDB 接続を渡して使用します。ユニットテストしやすい設計です。
- ローカルでの動作確認は KABUSYS_ENV=development（発注無し）で行うと安全です。
- config/*.yaml の自動検証には PyYAML が必要です。validate_config.py は YAML がない場合に検証をスキップして警告します。

ライセンス / 著作権
------------------
（ここにプロジェクトのライセンスを記載してください）

お問い合わせ
------------
問題点や改善案があれば Issue を作成するか、プロジェクト管理者に連絡してください。

以上。README に他に追加したい情報（例: サンプル .env.example、requirements.txt 内容、デプロイ手順など）があれば教えてください。