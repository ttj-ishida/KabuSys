KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ基盤の一部実装です。
主要コンポーネントとして、ExecutionEngine（発注実行）、Monitoring（監視）、ポートフォリオ構築、ファクター計算、AI を使ったニュース NLP / レジーム判定、ツール類を含みます。

主な特徴
-------
- ExecutionEngine：実際の発注処理を行うエンジン（kabuステーション API と連携）。KABUSYS_ENV に応じて paper_trading（モック）/ live（本番）を切替。
- Monitoring：CPU/メモリ/ディスク/プロセス状態やデータ鮮度、注文ログ・リスクログを定期ポーリングして SQLite に保存。Kill Switch によるエンジン停止制御。
- Portfolio construction：候補選定、重み付け、ポジションサイズ計算、セクターキャップ／レジーム乗数などの純粋関数群。
- Research：DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー等）と特徴量解析ユーティリティ。
- AI モジュール：OpenAI を使ったニュースのセンチメントスコアリング（ai.news_nlp）、マクロニュース + ETF MA を組み合わせた市場レジーム判定（ai.regime_detector）。
- ツール：.env ウィザード、設定検証、Paper Trading の検証レポート生成など。

セットアップ手順
--------------
1. リポジトリをチェックアウト
   - 通常の git clone → ルートに移動。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最小で必要になりやすいパッケージ:
     - pip install duckdb psutil openai
   - 解析や設定検証で PyYAML を使う場合は:
     - pip install PyYAML

4. .env の初期作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動で作成（.env はリポジトリにコミットしないこと）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

環境変数（重要なもの）
---------------------
主に Settings クラスで参照されます。最低限必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）

任意・上書き可能な主要設定（デフォルト値を示す）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）  デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス  デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（monitoring.db） デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading.db） デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/...） デフォルト: INFO
- OPENAI_API_KEY — OpenAI を使う機能を利用する場合に必須（ai.news_nlp / ai.regime_detector）

その他の設定は config_setup ウィザードや Settings ドキュメントを参照してください。

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- モニタリングループ起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
    - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することで行えます。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（monitoring 用データは本番 DB に保存）。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録し、本番 DB と分離します。
    - 実行中の PID ファイルは data/execution.pid（デフォルト）に書かれます。
    - 停止は data/stop_requested.flag により通知できます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ／ファイル配置（デフォルト）
------------------------------
- ログディレクトリ: logs/（デフォルト。環境変数 LOG_DIR で変更可）
  - 実行スクリプトごとに日次ローテートされるファイルが生成されます（例: logs/execution.log, logs/monitoring.log）。
- データディレクトリ: data/
  - SQLite (monitoring.db, paper_trading.db)
  - DuckDB path のデフォルトは data/kabusys.duckdb
  - PID / フラグ:
    - data/execution.pid （ExecutionEngine 用 PID）
    - data/stop_requested.flag （外部からの即時停止指示）
    - data/kill.flag （Kill Switch が書き込む停止指示）

監視・Kill Switch の概要
-----------------------
- Monitoring は system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化します（init_monitoring_db で自動作成・簡易マイグレーションを実施）。
- RiskMonitor がドローダウンやポジション上限を監視し、条件に応じて risk_logs に記録、さらに KillSwitch が条件を満たすと data/kill.flag を書き込みます（ExecutionEngine は kill.flag を検出して停止する仕組み）。
- run_monitoring/run_execution は data/stop_requested.flag を検出すると即時終了するようになっています（運用者による停止制御）。

AI モジュール（OpenAI）
---------------------
- ai.news_nlp と ai.regime_detector は OpenAI API（gpt-4o-mini を想定）を利用します。
- 実行には OPENAI_API_KEY が必要です（引数で明示することも可能）。
- API 呼出しはリトライ／サニティチェック・JSON バリデーション等フェイルセーフ実装あり。API 未設定時は例外を投げる箇所がありますので注意してください。

DB / マイグレーション
--------------------
- monitoring_db.init_monitoring_db() は必要なテーブルとインデックスを作成します。また既存 DB に対する簡易マイグレーション（dashboard.peak_value、trade_logs.latency_ms の追加）を行います。
- DuckDB は分析用データを格納し、research / ai モジュールが参照します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要なソースツリー（src/kabusys 以下を抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (実装あり)
  - execution/               (発注周りコンポーネント)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に作成されることが多い（DB, pid, flags）

（上記に加えて config/*.yaml、scripts/ 等の構成ファイルが存在する可能性があります）

運用上の注意 / トラブルシューティング
---------------------------------
- 必須環境変数が未設定だと起動できません。validate_config で事前チェックを行ってください。
- KABUSYS_ENV=paper_trading を設定すると発注はモックとなり paper_trading DB に記録され本番 DB と分離されます。テスト運用時はこのモードを推奨します。
- OpenAI を使う機能は API 使用料が発生します。API レート制限やキーの管理に注意してください。
- ログディレクトリを作成できない場合はコンソールログのみで動作します（警告が出ます）。
- psutil を使って優先度や CPU affinity を設定します。権限不足で設定できない場合は警告が出てスキップされます。

開発者向けメモ
--------------
- 設定は .env と環境変数から読み込まれます。プロジェクトルート検出はソースファイル位置から行うため、パッケージ化後も動作するよう設計されています。
- research / portfolio モジュールは副作用がなく純粋関数的に設計されているためユニットテストが容易です。
- AI モジュールの外部 API 呼び出しは個別のプライベート関数でラップしており、テスト時には patch して差し替え可能です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

最後に
------
この README はコードベースの主要機能・運用方法をまとめた概要です。各モジュールの詳細な仕様や設定例はソース内ドキュメント（docstring）および config/*.yaml / scripts/generate_config.py（存在する場合）を参照してください。必要であればインストール手順や運用手順をさらに詳しく追記します。