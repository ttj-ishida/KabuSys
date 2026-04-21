README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
本リポジトリには下記の機能（バックテスト以外の実行／監視／研究／AI支援）を実装しています。主に以下を含みます:

- 実行エンジン（ExecutionEngine）起動／発注（本番 / ペーパートレード）
- 監視サブシステム（System / Trade / Risk の定期チェック）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- ファクター計算・特徴量探索（DuckDB を用いた研究向けモジュール）
- ニュースの NLP スコアリング・市場レジーム判定（OpenAI API 統合）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

機能一覧
---------
主な機能と用途:

- 実行（src/kabusys/run_execution.py）
  - KABUSYS_ENV に応じて本番または paper_trading（MockBroker）で発注を行う。
  - paper_trading 時は data/paper_trading.db に記録して本番 DB と分離。
  - 停止は data/stop_requested.flag / data/kill.flag によるフラグファイルで制御。

- 監視（src/kabusys/run_monitoring.py、monitoring/*）
  - システム稼働状況・データ鮮度・取引ログ・リスク監視をポーリング。
  - KillSwitch による自動停止（条件に応じて data/kill.flag を書き込む）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限、レジーム乗数）
  - 株数決定（単元丸め・aggregate cap スケールダウン等）

- 研究（research/*）
  - DuckDB を用いたモメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ai/*）
  - ニュースを OpenAI（gpt-4o-mini 等）でセンチメント解析して ai_scores に書き込み
  - 市場レジーム判定モジュール（ETF MA + マクロニュースの LLM 判定を合成）

- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

1. Python 環境を作成（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本プロジェクトは次の主要パッケージを利用します:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証で YAML の中身検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考にしてください）。
   - 自動ロード:
     - src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml）を探索し、
       .env および .env.local を自動で読み込みます。自動ロードを無効化する場合は
       KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

5. データディレクトリ等の確認
   - デフォルトの DB / ログ パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じてディレクトリを作成してください（logging_setup が自動作成を試みますが権限によるエラー発生時はコンソール出力のみになります）。

環境変数（主なもの）
-------------------
（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

（主なオプション／デフォルト）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — SQLite (monitoring) パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）。デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時必須）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）。デフォルト: 60
- PAPER_FILL_MODE — ペーパートレードの注文約定挙動（instant/partial/never/reject）。デフォルト: instant
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）。本番では 0 推奨

使い方
------

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - 外部から停止させたい場合はプロジェクトの data/stop_requested.flag を作成するとループは検知して終了します。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録されます。
  - 停止:
    - data/stop_requested.flag を作成すると実行エンジンを安全に停止します。
    - KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させます。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成/更新できます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH より優先)
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（ニュース NLP・レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY）。
  - ニューススコアリング: kabusys.ai.score_news（モジュール関数）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - CLI 例は用意されていませんが、スクリプト/ジョブからこれらを呼び出して利用します。

停止・Kill Flag の挙動
---------------------
- stop_requested.flag: 実行中の run_monitoring/run_execution がこのファイルの存在を検知すると安全に終了します。ファイルの場所はプロジェクト/data/stop_requested.flag（スクリプト実行時のパス解決に基づく）。
- kill.flag: KillSwitch が条件を満たしたときに書き込まれます（ExecutionEngine 側で検出し停止）。本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。

ディレクトリ構成
----------------
（主要ファイル／ディレクトリの概略）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ポーリング起動スクリプト
  - run_execution.py         — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor の実装ファイルあり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

- data/                — データファイル（SQLite / PID / flag 等を配置。実行時に作成される）
- logs/                — ログ出力先（デフォルト）

補足・運用ノウハウ
-----------------
- DB 分離:
  - ペーパートレード（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db と完全に分離します。
- ログ:
  - logging_setup は stdout と 日次ローテーションのファイルハンドラを設定します（logs/<app_name>.log）。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- テストと自動ロード:
  - テスト時や外部制御下では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化できます。
- OpenAI:
  - AI 関連機能は API コールのレートリミットや一時エラーに対してリトライ・フェイルセーフ設計になっています。API キーの漏洩に注意し .env を絶対にコミットしないでください。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義されています。

その他
-----
- ここに書かれていない内部 API（ExecutionEngine の細かい起動引数や BrokerClient 実装など）はソースを参照してください。README に不足があれば、具体的に知りたい箇所を教えてください。