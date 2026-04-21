KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム群（データ処理 / リサーチ / ポートフォリオ構築 / 発注実行 / 監視 / AI補助）をまとめたパッケージ実装です。  
以下はコードベースに含まれる主要機能、セットアップ、使い方、ディレクトリ構成の概要ドキュメントです。

概要
----
KabuSys は以下のような役割を持つコンポーネント群で構成されています。

- データ取得・蓄積（DuckDB / SQLite を利用）
- ファクター計算・リサーチ（momentum, volatility, value 等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- Execution Engine（実際の発注、ペーパートレード対応）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用ツール（設定ウィザード、設定検証、検証レポート生成）

主な機能
---------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
- 設定検証 CLI（python -m kabusys.validate_config）で起動前のチェック
- Execution エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading DB に記録（本番 DB と分離）
  - 起動時にプロセス優先度を高く設定
  - 停止はフラグファイルで制御（data/stop_requested.flag / kill.flag）
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリング（環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能、デフォルト 60 秒）
  - 監視用 SQLite は環境に関係なく本番 sqlite_path を使用して監視情報を記録
- AI モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp.score_news）：OpenAI を使って銘柄ごとのセンチメントを算出し ai_scores に保存
  - レジーム判定（kabusys.ai.regime_detector.score_regime）：MA200 とマクロ記事の LLM センチメントを合成して市場レジームを判定
- 運用ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ポートフォリオモジュール
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算、セクター上限適用 等

依存関係（代表）
----------------
- Python 3.10+（タイプヒントに | を利用しているため）
- pip パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの検査用、必須ではない）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- その他、環境に応じて broker クライアント等の実装依存

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実際の運用で必要な追加依存（ブローカークライアント等）があればそれらもインストールしてください。

3. .env を作成
   - 対話式に作る: python -m kabusys.config_setup
   - もしくは手動でルートに .env を作成（参照する主な環境変数は下記参照）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります: python -m kabusys.validate_config --strict

5. DB ファイルやログディレクトリ
   - デフォルトでは data/ 配下に SQLite / DuckDB ファイルが置かれ、logs/ にログが出力されます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を設定してください。
   - monitoring 起動時に SQLite のテーブル作成・マイグレーションが自動で行われます。

主要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY : AI モジュール利用時に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: "1" で有効）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数を上書き、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の MockBrokerClient 挙動: instant | partial | never | reject）

使い方 (コマンド例)
------------------
- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中に停止したい場合: プロセスに対して stop フラグ（data/stop_requested.flag）または kill.flag を利用（下記参照）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止・Kill スイッチ
-------------------
- run_execution と run_monitoring は停止フラグ（stop_requested.flag）を監視します。ルートの data/stop_requested.flag を作成するとループを早期終了します（運用時の graceful stop に使用）。
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件（ドローダウン超過など）で data/kill.flag を書き込み、ExecutionEngine に停止を指示します。kill.flag は存在すると ExecutionEngine の起動や継続に影響するため、明示的に削除するか KILL_FLAG_CLEAR_ON_START を使って起動時にクリアすることができます。
- 手動でフラグを削除するには: rm data/kill.flag または python スクリプトから KillSwitch.clear を呼ぶ。

ロギング
--------
- 共通のログ設定ユーティリティが用意されています（kabusys.utils.logging_setup.setup_logging）。  
  デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力します。LOG_DIR 環境変数や引数で変更可能です。

注意点 / 運用上の留意
--------------------
- OpenAI を使う機能（ニューススコアリング・レジーム判定）は OPENAI_API_KEY を必要とします。API コストとレート制限に注意してください。
- run_execution は KABUSYS_ENV に応じて実際の発注を行います（live では実際に発注）。本番環境では設定を十分に確認してください（validate_config は live 時に警告を出します）。
- process priority の設定は psutil を使い、権限不足などで設定できない場合は警告を出してスキップします。
- DuckDB / SQLite のパスやログディレクトリの親ディレクトリがない場合は警告が出ますが、多くは起動時に自動作成されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内部の主要なファイル・モジュールの一覧（抜粋）。プロジェクトルートはパッケージ配布後も同様の構成を想定しています。

- kabusys/                      — パッケージ本体
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — 環境変数の自動ロード・Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py        — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py          — SQLite 監視 DB の初期化・読み書き
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — (該当実装あり) 注文ログ監視
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 制御
    - monitoring_engine.py      — 各 Monitor を束ねる
    - alert_manager.py          — (アラート送信管理)
  - execution/
    - execution_engine.py       — 発注エンジン本体（EngineConfig, run_session 等）
    - order_manager.py          — 注文管理
    - order_repository.py       — 注文永続化
    - reconciler.py             — ブローカーと DB の整合処理
    - broker_factory.py         — ブローカークライアント生成（Mock含む）
    - risk_manager.py           — 実行時のリスクチェック
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・集約制限
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — momentum / volatility / value 等の計算
    - feature_exploration.py    — forward returns / IC / 統計サマリ
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py          — 共通ログ設定
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/monitoring_db.py  — 監視用 DB スキーマ定義・マイグレーション

（上記はコードベースの抜粋です。実際のリポジトリには追加の補助モジュールやデータ変換モジュールが含まれる場合があります）

開発者向けメモ
----------------
- 自動で .env を読み込む仕組み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探し、.env → .env.local の順で読み込みます。OS 環境変数は保護されます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- DB 初期化・マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡単なカラム追加を行います。
- テスト / モック:
  - OpenAI 呼び出しや外部 API は関数単位で差し替えやすい設計（_call_openai_api のパッチ等）になっています。ユニットテスト時は patch してください。

最後に
------
この README はコードベースを見て要点をまとめた運用・開発向けの説明です。実運用に移す前に必ず python -m kabusys.validate_config 等で設定を検証し、ステージング（paper_trading）環境で十分に動作確認してください。質問やドキュメント追記の希望があれば教えてください。