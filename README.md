README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスク監視と Kill Switch
- ポートフォリオ構築：候補選定、重み付け、株数決定、セクター制限など
- Research：DuckDB 上で動くファクター計算・特徴量解析
- AI モジュール：ニュースのセンチメントスコアリング、レジーム判定（OpenAI を使用）
- 開発用ツール：.env 生成ウィザード、設定検証、ペーパートレード検証レポート 等

この設計は本番口座へのアクセスと研究処理を切り分けること、外部 API 呼び出しの失敗に対してフェイルセーフにすることを重視しています。

主な機能
--------
- Execution
  - 本番（live）・ペーパートレード（paper_trading）を環境変数 KABUSYS_ENV によって切り替え
  - paper_trading 時は MockBrokerClient を使い、専用 SQLite（デフォルト data/paper_trading.db）に記録
  - プロセス優先度設定・PID ファイル管理・停止フラグによる安全停止
- Monitoring
  - CPU / メモリ / ディスク / Execution プロセスの監視
  - 注文滞留・約定異常・ドローダウン・ポジション上限の検出
  - kill.flag による ExecutionEngine の強制停止（Kill Switch）
  - アラート送信フック（LINE 等を想定）
- Portfolio（純粋関数）
  - 候補選定、等金額・スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB 上でのファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - raw_news を OpenAI（gpt-4o-mini 等）で解析して ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定（market_regime テーブルへ書き込み）
  - API 呼び出しはリトライ・バックオフ・バリデーション済みで堅牢に設計
- ツール
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（コンソール + 日次ローテート）
  - プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <project-root>

2. Python 環境（推奨）
   - Python 3.10+ を想定
   - 仮想環境作成/有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 主要な必須パッケージ（repo に requirements.txt がなければ手動で）
     - pip install duckdb psutil openai pyyaml
   - sqlite3 は標準ライブラリ、DuckDB は外部パッケージです。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（例は config/.env.example を参照してください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要な環境変数（デフォルト値あり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START など

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. ディレクトリ作成
   - data/ および logs/ は起動時に自動作成されますが、手動で作ることも可能です。

基本的な使い方
--------------
- ExecutionEngine を起動する
  - 本番/ペーパーは KABUSYS_ENV で切り替え
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - ExecutionEngine は pid ファイルを data/execution.pid（デフォルト）に書きます

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - run_monitoring は常に本番 sqlite_path を使います（監視は環境に関わらず同じ DB を参照）
  - 停止は data/stop_requested.flag を作成

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- AI 機能（プログラムから呼ぶ）
  - 例: kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します
  - レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key)

- 停止フラグ / Kill Switch
  - run_execution と run_monitoring はプロジェクト内 data/stop_requested.flag を監視して終了します。
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に強制停止を指示するためのフラグです。
    - KillSwitch.evaluate によって条件が一致すると書き込まれます（冪等）。
    - KillSwitch.clear で削除できます。KILL_FLAG_CLEAR_ON_START が 1 に設定されていると起動時に自動的にクリアされます（本番では 0 推奨）。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- デフォルト: コンソール出力 + logs/<app_name>.log（日次ローテート、30世代保持）
- 環境変数 LOG_DIR でログディレクトリを変更可能

データベース
-----------
- DuckDB（分析データ）: デフォルト data/kabusys.duckdb（設定 DUCKDB_PATH）
- SQLite（監視ログ）: デフォルト data/monitoring.db（設定 SQLITE_PATH）
- Paper Trading 専用 SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- init_monitoring_db により監視用テーブルは自動で作成・マイグレーションされます

ディレクトリ構成（抜粋）
------------------------
プロジェクトの主要ファイル・ディレクトリ構成（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings クラス
  - config_setup.py          # .env ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       # ログ設定ユーティリティ
    - process_priority.py    # プロセス優先度・CPU affinity
  - execution/               # Execution 関連（BrokerFactory, Engine 等）
  - monitoring/
    - monitoring_db.py       # SQLite 用永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            # ニューススコアリング（OpenAI）
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（プロジェクトルート）
- .env                    # 環境変数（通常 Git 管理下に置かない）
- data/                   # DB、フラグファイルなど（起動時自動生成可能）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                   # ログ出力先（デフォルト）
- config/                 # 各種 YAML 設定テンプレート（system_config.yaml 等）

開発・運用上の注意
-----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番実行時は KABUSYS_ENV=live を設定します。validate_config の警告をよく確認してください。
- Kill Switch や stop flag の扱いには十分注意してください（本番では自動クリアを無効推奨）。
- OpenAI API を利用する機能は API キーと利用コストが発生します。テスト時はモック化して実行してください。
- DuckDB のクエリは大規模データを扱うため、メモリ設定やファイルパスの管理に注意してください。

問い合わせ / 貢献
----------------
バグ報告や改善提案はリポジトリの Issue にお願いします。プルリクエストは歓迎します。変更を加える際はテスト（ユニットテスト）と validate_config の通過を確認してください。

以上。必要であれば、README にチュートリアル（例: ローカルでペーパートレードを動かす手順）や推奨設定のテンプレートを追加します。どの情報を詳しく載せたいか教えてください。