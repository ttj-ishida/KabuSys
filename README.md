KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群を含む小規模フレームワークです。  
主要コンポーネントは ExecutionEngine（発注系）、Monitoring（監視系）、Research / Portfolio / AI（分析系）などで構成されています。

主な特徴
--------
- 実運用を意識した設計（プロセス優先度設定、ログの日次ローテーション、Kill Switch）
- 本番 / ペーパートレード環境の分離（KABUSYS_ENV による切替）
- DuckDB を使ったリサーチ用データ照会・ファクター計算モジュール
- OpenAI を用いたニュース NLP と市場レジーム判定（オプション）
- SQLite を用いた監視・トレースログ保存（monitoring.db / paper_trading.db）
- ユーティリティ: .env 対話式ウィザード、設定検証、ペーパートレード検証レポート生成

主要機能一覧
------------
- 実行スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper DB に記録）
  - run_monitoring.py — SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL で間隔指定）

- 設定関連
  - config_setup.py — 対話式 .env 生成 / 更新ウィザード
  - validate_config.py — .env と config/*.yaml の整合性チェック（--strict オプションあり）
  - config.py — Settings クラス（環境変数読み込み / デフォルト / バリデーション）

- 監視
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマと永続層
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py など — 各種監視ロジック
  - monitoring/monitoring_engine.py — 各 Monitor を束ねたポーリングループ
  - monitoring/kill_switch.py — 条件に応じて data/kill.flag を書き、ExecutionEngine を安全停止

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py

- リサーチ / 特徴量
  - research/factor_research.py, feature_exploration.py — DuckDB を用いたファクター計算・IC 等の統計処理

- AI（OpenAI）
  - ai/news_nlp.py — ニュースを集約して LLM に投げ、銘柄別センチメントを ai_scores に保存
  - ai/regime_detector.py — ETF の MA とマクロニュースを組み合わせて日次レジーム判定

- ツール
  - tools/paper_verification_report.py — ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
前提:
- Python 3.10+ を想定（type hints に union syntax 等を使用）
- システム依存の二次要件: duckdb, psutil, openai（AI 機能を使う場合）

推奨インストール手順（例）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - optional: PyYAML（validate_config の YAML 検証を有効にする場合）: pip install PyYAML

3. .env の初期作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に J-Quants トークン、kabu API パスワード 等を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ等の作成（任意）
   - デフォルトでは data/ 以下に DB や PID/フラグを作成します。必要に応じて権限等を確認してください。

主要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使用し data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ格納ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に data/kill.flag を自動クリアするか (0/1)

短い .env 例（.env は絶対に Git にコミットしないでください）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_kabu_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- OPENAI_API_KEY=sk-...

使い方（コマンド例）
-------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときは paper_trading.db に書き込みます
  - 外部停止: data/stop_requested.flag を作成すると起動中のスクリプトは終了を検知します
  - Execution 起動時は execution.pid（デフォルト: data/execution.pid）を生成します

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings の sqlite_path（デフォルト monitoring.db）を使用します（環境に関わらず本番 DB を参照する設計）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で渡す）
  - 例（プログラムから呼ぶ）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

制御フラグ・ファイル
-------------------
- data/kill.flag — KillSwitch により作成される停止フラグ（ExecutionEngine はこれを検出して安全停止）
- data/stop_requested.flag — run_execution / run_monitoring の起動ループから即時停止を指示するフラグ
- data/execution.pid — ExecutionEngine の PID ファイル（存在確認や stale 判定に使用）

ログ
----
- ログは stdout にも出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- ログディレクトリは環境変数 LOG_DIR、ログレベルは LOG_LEVEL で制御できます。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — Settings / .env 自動読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLP（OpenAI）関連
  - regime_detector.py     — 市場レジーム判定（OpenAI と価格データ合成）

- monitoring/
  - monitoring_db.py       — SQLite スキーマ / 永続層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート送信の抽象化、実装により LINE などへ通知）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py       — 統一ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意点 / 運用メモ
------------------------
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60秒）。0 以下は無効としてデフォルトにフォールバックします。
- Monitoring の DB 初期化（テーブル作成）は init_monitoring_db() で冪等に行われます。既存 DB のマイグレーション（カラム追加）ロジックも含まれます。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、Mock ブローカを使用して paper_trading 用 DB へ記録します。本番 DB と完全分離する設計です。
- AI モジュールは OpenAI API を利用します。API 失敗時はフェイルセーフ（スコアを 0.0 にする / スキップ）が組み込まれていますが、API のコストとレート制限に注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- kill.flag の自動クリア設定（起動時に自動で clear するか）は KILL_FLAG_CLEAR_ON_START で制御します。本番では 0（クリアしない）を推奨します。

トラブルシューティング
---------------------
- DuckDB / SQLite のファイル権限や親ディレクトリが存在しない場合、validate_config が警告を出します。起動ユーザーに書き込み権限があることを確認してください。
- psutil によるプロセス優先度設定は OS によって制限されます（権限不足や未対応 OS では警告が出てスキップされます）。
- OpenAI 呼び出しで JSON パースエラーやレート制限が起きることがあります。AI 関連機能はログを確認し、API キーや利用制限を見直してください。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。
- ライセンスファイル（LICENSE）がリポジトリにあればそちらを参照してください。

最後に
------
この README はソース内の設計コメント・ドキュメント文字列を基に作成しています。実運用前に必ず python -m kabusys.validate_config で設定を検証し、テスト環境で動作確認を行ってください。質問や補足が必要であれば教えてください。