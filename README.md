KabuSys — 日本株自動売買システム
================================

このリポジトリは、KabuSys（日本株向け自動売買システム）のコアユーティリティ群を含みます。  
本 README はプロジェクト概要、主要機能、セットアップ手順、起動/利用方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下のようなコンポーネントを持つシステムです。
- 注文実行エンジン（ExecutionEngine）
- 監視サブシステム（MonitoringEngine: システム稼働状況、注文状況、リスク監視）
- ポートフォリオ構築・ポジションサイズ計算ロジック（Portfolioモジュール）
- ファクター計算 / リサーチツール（Research）
- ニュース NLP によるセンチメント評価・レジーム判定（AI モジュール、OpenAI 利用）
- ユーティリティ: ログ設定、プロセス優先度設定、環境変数ウィザード、設定検証
- ペーパートレード用の分離 DB と検証レポート作成ツール

主な設計方針（抜粋）
- .env / 環境変数ベースで設定を管理（Settings クラス）
- 本番・ペーパートレードは明確に分離（PAPER_TRADING 用 SQLite）
- 監視は SQLite（軽量）／分析は DuckDB（高速分析）
- 外部 API（OpenAI 等）は明示的な API キー指定を要求（テスト時に差し替え可能）
- ログは統一的な setup_logging で stdout と日次ローテーションファイルに出力

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度（high）設定、PID ファイル管理、停止フラグ検知（data/stop_requested.flag）
- 監視エンジン起動スクリプト: run_monitoring.py
  - 定期ポーリングで System / Trade / Risk モニタを実行
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視ログは常に本番用 sqlite_path に書き込む（環境にかかわらず）
- 環境設定ウィザード: config_setup.py
  - .env の対話式生成 / 更新
- 設定検証 CLI: validate_config.py
  - .env と config/*.yaml の存在・簡易妥当性をチェック
- Paper Trading 検証レポート生成: tools/paper_verification_report.py
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL を表示
- ポートフォリオ構築ユーティリティ:
  - 候補選定、等重/スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- AI モジュール:
  - news_nlp: ニュース記事をまとめて OpenAI でセンチメント評価 → ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ:
  - setup_logging: stdout + 日次ローテーションログ
  - process_priority: OS に依存せずプロセス優先度 / CPU affinity を設定
  - monitoring_db: 監視用 SQLite の初期化と CRUD 操作

セットアップ手順
----------------

1. Python 仮想環境を作成
   - 推奨: Python 3.10+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements を用意している場合はそれを使う（本リポジトリに明示的な requirements.txt がない想定）
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML パースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env を用意（推奨: 対話式ウィザードで生成）
   - 対話式:
     - python -m kabusys.config_setup
   - 必須環境変数（validate_config.py / Settings に基づく）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 重要な設定（デフォルト値）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LOG_LEVEL: INFO（DEBUG 等に変更可能）
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）
   - .env の自動読み込み:
     - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動適用します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になる

5. DB 初期化
   - 実行スクリプトが内部で init_monitoring_db を呼び出すため、通常手動での初期化は不要です。
   - DuckDB ファイルは初回接続時に作成されます。

使い方（起動 / コマンド）
------------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に process priority を "high" に試みます（OS 権限に依存）
    - PID ファイルを data/execution.pid（デフォルト）に書きます
    - data/stop_requested.flag が既に存在する場合は起動せず終了します
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL （秒）でポーリング間隔を上書き可能（デフォルト 60）
  - run_monitoring は monitoring 用 SQLite（Settings.sqlite_path）を常に使用して記録します
  - data/stop_requested.flag を検知するとループを終了します

- 環境ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH より優先して指定可能

- AI 関連（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上

停止・Kill Switch の運用
-----------------------
- 強制停止（ExecutionEngine を止めたい場合）の仕組み:
  - kill.flag（デフォルト Settings.kill_flag_path → data/kill.flag）を書き込むと KillSwitch evaluated によって ExecutionEngine に停止シグナル送出される（run_execution は kill.flag を監視して起動後の停止判定を行う設計）。
  - run_execution と run_monitoring が監視する停止トリガー: data/stop_requested.flag（存在で停止）
- 設定:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリア（本番では危険なので 0 推奨）

ログ
----
- ログは setup_logging によりルートロガーに設定される:
  - stdout（StreamHandler）
  - 日次ローテートファイル（logs/<app_name>.log、30 日保持）
- 環境変数:
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）

注意事項・運用上のポイント
-----------------------
- 本番（KABUSYS_ENV=live）では設定値を慎重に確認すること（validate_config で警告が出る）
- OpenAI 関連は API コストとレイテンシに注意。API キーは漏洩しないよう .env を git 管理に含めないこと
- psutil による優先度変更や CPU affinity は OS と権限に依存し、失敗時は警告ログが出力されるが処理は継続する
- DuckDB / SQLite のパスはデフォルトで data/ 配下。バックアップや保存場所に注意
- ペーパートレードは本番 DB と分離して扱うため、ペーパートレードのデータが本番に混ざることはありません

ディレクトリ構成
----------------
主要ファイル/ディレクトリ（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート自動生成
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — monitoring 用 SQLite DB 初期化とラッパ
    - monitoring_engine.py         — 各モニタを束ねるエンジン
    - system_monitor.py            — システム稼働・データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - trade_monitor.py             — 注文監視（滞留注文等） ※実装に依存
    - kill_switch.py               — kill.flag 書き込みユーティリティ
    - alert_manager.py             — 通知（LINE 等） ※実装に依存
  - execution/
    - execution_engine.py          — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py                   — データ取得 / 最終日取得ユーティリティ 等
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - monitoring/monitoring_db.py    — 監視 DB スキーマ初期化 / MonitoringDB クラス

（上記は実装の一部を抜粋しています。詳細は各ファイルの docstring を参照してください）

補足（よく使うコマンドまとめ）
----------------------------
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb psutil openai PyYAML

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（開発・検証用）
  - python -m kabusys.run_execution

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

最後に
------
この README はリポジトリ内のコードの docstring / コメントをもとに作成しています。実運用前に必ず以下を行ってください：
- .env を正しく設定する（特に API トークン・パスワード）
- validate_config.py でチェックする
- ペーパートレードで十分に動作確認を行う

必要があれば、起動スクリプトや各モジュールの使い方を具体的なユースケースに合わせて追記します。お気軽にどの部分を詳しくドキュメント化したいか指定してください。