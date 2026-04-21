KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ基盤（KabuSys）のコアモジュール群を含みます。
小規模な戦略エンジン、監視（Monitoring）、ペーパートレード用ロジック、ファクター計算、LLM を使ったニュース NLP などを備えています。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（完全分離 DB）対応
  - リスク管理（最大ポジション比率・利用率・ドローダウン等）
  - Order 管理、Reconciler による整合性維持
- Monitoring（監視）
  - システム稼働監視（CPU/メモリ/ディスク/プロセス）
  - 注文ログ・リスクログ・ダッシュボード保存（SQLite）
  - Kill Switch による安全停止（kill.flag の生成）
- Portfolio 建設ユーティリティ（候補選定、重み付け、ポジションサイズ決定、セクター制限など）
- Research / Factor 計算（DuckDB を用いたファクター・リターン計算、IC/統計）
- AI モジュール（OpenAI を使ったニュースセンチメント／レジーム判定）
- Tools（Paper Trading 検証レポート生成など）
- 複数のユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード・検証 CLI）

必須/推奨要件
-------------
- Python 3.10+
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に必要）
- OS: Linux / macOS / Windows（ただし一部の機能（nice/affinity 等）はプラットフォーム差分あり）

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実行環境や用途に応じて必要なライブラリを追加してください。

4. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（デフォルトはプロジェクトルートの .env を読み込みます）。
   - 必須環境変数（最低設定）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY（OpenAI API キー）
   - 主要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live
       - paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と分離）。
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/...）
     - PID_FILE_PATH / KILL_FLAG_PATH 等

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

基本的な使い方
--------------

- 実行（ExecutionEngine）
  - 本番（通常）起動:
    - python -m kabusys.run_execution
  - ペーパートレード起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全分離されます。
  - 停止:
    - 実行ファイル起動時にプロセスは data/stop_requested.flag の存在を監視します。外部から停止を要求するにはこのファイルを作成してください（例: touch data/stop_requested.flag）。
    - また Monitoring 側の KillSwitch は data/kill.flag を書き込み ExecutionEngine の停止を促します（設定に応じて）。

- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保持します。
  - ログ設定は共通ユーティリティ経由（kabusys.utils.logging_setup）で行われ、logs/<app_name>.log に日次ローテーションで保存されます。

- .env 管理
  - ウィザード: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます。デフォルト: data/paper_trading.db

- AI 機能（ニュース NLP / レジーム検出）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - kabusys.ai.news_nlp.score_news および kabusys.ai.regime_detector.score_regime が主要関数です。
  - 使用するモデル: gpt-4o-mini（コード内で指定）。API 呼び出し時はリトライやレスポンス検証が組み込まれています。

ログ / デバッグ
----------------
- ログ出力:
  - デフォルトは stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次）に出力されます。
  - LOG_LEVEL / LOG_DIR 環境変数で調整可能。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil を利用、権限がない場合は警告を出してスキップします）。

安全とフェイルセーフ
--------------------
- Monitoring 側で検出された重大な事象（過度のドローダウン、ポジション上限超過等）は KillSwitch により kill.flag を生成し ExecutionEngine の停止を促します。
- AI API のエラー（429/タイムアウト/5xx 等）は指数バックオフでリトライし、最終的にフォールバック値（例: macro_sentiment=0.0）で継続する設計です。
- DB 書き込みは可能な限りトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に行います。

ディレクトリ構成（主要ファイル）
-----------------------------
- src/kabusys/
  - __init__.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - config.py                  — 環境変数 / 設定管理（自動 .env 読込）
  - config_setup.py            — 対話式 .env 生成ウィザード
  - validate_config.py         — 設定検証 CLI
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — 監視用 SQLite 永続化層
    - monitoring_engine.py     — 複数 Monitor を束ねるループ
    - system_monitor.py        — システム／データ鮮度監視
    - trade_monitor.py         — （注文監視ロジック）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag の生成・管理
    - alert_manager.py         — （LINE等に通知するコンポーネント、実装に依存）
  - execution/
    - execution_engine.py      — ExecutionEngine（発注セッション管理）
    - order_manager.py         — 注文発行ロジック
    - order_repository.py      — 注文履歴永続化（SQLite 等）
    - broker_factory.py        — Broker クライアント生成（本番 / mock 切替）
    - reconciler.py            — 注文状態整合処理
    - risk_manager.py          — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - risk_adjustment.py       — セクターキャップ / レジーム乗数
    - position_sizing.py       — 発注株数決定ロジック
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py              — ニュースセンチメントスコア取得（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

補足 / トラブルシューティング
-------------------------------
- .env 自動読み込み:
  - プロジェクトルートの .env（および .env.local）を自動で読み込みます（OS 環境変数を上書きしない扱い）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。
- config/*.yaml の検証は PyYAML が必要です。未インストールの場合は検証がスキップされ警告が出ます。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合、起動時に自動作成される場合がありますが、その旨 validate_config は警告します。
- OpenAI API 呼び出し周りはレートリミットや課金に注意してください。テスト時はモック化（unittest.mock）で置き換える設計になっています。

最小動作確認の例
-----------------
1. 仮想環境作成・依存インストール
   - python -m venv .venv && source .venv/bin/activate
   - pip install duckdb psutil openai

2. .env を作成（ウィザード推奨）
   - python -m kabusys.config_setup

3. 設定検証
   - python -m kabusys.validate_config

4. 監視プロセスを起動（開発環境）
   - python -m kabusys.run_monitoring

5. ペーパートレードで ExecutionEngine を起動
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

ライセンス・貢献
----------------
- 本 README はコードベースの説明用です。ライセンス・貢献ガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。必要に応じて README にサンプル .env のテンプレートや具体的なコマンドのスクリーンショット等を追加できます。どの部分を詳細化したいか教えてください。