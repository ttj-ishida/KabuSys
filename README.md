KabuSys — 日本株自動売買システム
=================================

本ドキュメントはこのコードベースの概要、セットアップ方法、主要な使い方、ディレクトリ構成をまとめた README です。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主に以下の機能を持つモジュールで構成されています。

- 注文実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント（OpenAI API 利用）
- Paper Trading 用の検証レポート生成ツール
- 環境設定ウィザード、設定検証 CLI、ログ設定ユーティリティ 等

主要な特徴・機能一覧
-------------------
- ExecutionEngine の起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用、paper_trading 用の DB に完全分離して記録
- Monitoring（run_monitoring.py）
  - システム／注文／リスク監視をポーリングで実行
  - MONITOR_POLL_INTERVAL でポーリング周期を上書き可能（デフォルト 60 秒）
  - 監視データは SQLite（monitoring.db） と DuckDB（分析用）へ保存
- Kill Switch
  - 監視で重大事象が検知された場合に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重／スコア重み、リスク制約（セクターキャップ等）、ポジションサイズ計算（単元丸め含む）
- Research（kabusys.research）
  - Momentum / Volatility / Value ファクターや将来リターン・IC 計算、統計サマリー
- AI モジュール（kabusys.ai）
  - ニュース記事を集約して OpenAI でセンチメント算出（score_news）
  - 市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成
  - config_setup: .env を対話式に作成
  - validate_config: 起動前の設定検証（警告・エラーチェック）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

システム要件（目安）
-------------------
- Python 3.10+ を推奨
- 必要パッケージ（少なくとも下記をインストールしてください）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config 検証で必要）

セットアップ手順
----------------
1. リポジトリをクローン／展開し、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストールします（requirements.txt が無い場合は個別指定）。
   - pip install duckdb psutil openai
   - （検証用に PyYAML が欲しい場合）pip install pyyaml

3. .env の作成
   - 対話式ウィザードで作成する:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動で消すか。開発用）

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります

5. ディレクトリ作成
   - data/ と logs/ は起動時に自動作成する処理がありますが、権限などで失敗する場合があるため事前に作ると安全です。
   - mkdir -p data logs

使い方
------
起動／主要コマンドの例を示します。

- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV による:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live / development: 通常のブローカークライアント（本番接続等の注意が必要）
  - ExecutionEngine は data/execution.pid（デフォルト）をPIDファイルとして扱います。
  - 停止は data/stop_requested.flag を作成することで行えます（run_execution は起動時にこのフラグが立っていれば起動しません）。

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可、デフォルト 60 秒
  - 注意: run_monitoring は設定にかかわらず production 用の sqlite_path（settings.sqlite_path）を使用します（監視 DB は本番 DB を参照）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

- AI（ニューススコアリング）を呼び出す（プログラム内から）
  - 例（簡易）:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date.fromisoformat("2026-04-10"), api_key="YOUR_OPENAI_KEY")
  - OpenAI API キーは OPENAI_API_KEY 環境変数でも指定できます。
  - AI モジュールは失敗時にフェイルセーフ（部分スコア保存、または macro_sentiment のフォールバック）を行う設計です。

- 市場レジーム判定（regime_detector）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=...)

停止・Kill Switch・フラグ
-----------------------
- data/stop_requested.flag
  - run_execution / run_monitoring の起動ループはこのファイルを検出すると安全に終了します。管理操作で停止したいときに書き込んでください。

- data/kill.flag（Kill Switch）
  - 監視（MonitoringEngine / KillSwitch）がリスク条件（ドローダウンやポジション上限など）を検知した場合に書き込まれます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定が有効でない限り、このフラグがあると起動しません（安全設計）。
  - KillSwitch.clear() を呼ぶか手動でファイルを削除してクリアします。

ログ
---
- ログは stdout（StreamHandler）とファイル（logs/<app_name>.log 日次ローテート）に出力されます。
- LOG_DIR / LOG_LEVEL 環境変数で出力先・レベルを変更可能。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップしてコンソールのみで継続します。

設定に関する注意
----------------
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を検出できれば自動で .env（および .env.local）を読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途等）。
- PAPER_FILL_MODE（paper_trading の約定挙動）
  - instant | partial | never | reject のいずれか。デフォルト "instant"。
- 監視 DB の扱い
  - run_monitoring は本番 sqlite_path を使う設計です（監視は常に本番 DB を見る想定）。
  - run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用します（本番 DB と分離）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要なファイル/パッケージ一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings クラス（.env 自動読み込み）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 開発者向けメモ
--------------------
- DuckDB 接続を受け取り SQL+Python で分析を行う設計が多く、データ取得→処理→結果書き込みの流れが明確です。
- OpenAI API まわりはリトライ・バックオフやレスポンスバリデーションを含む堅牢化が施されています。API キー漏洩に注意して .env を管理してください。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等性を保つ実装になっており、新しいカラム追加時の処理も含まれます。

さらに知りたいこと・実行例が必要であれば、どの機能（例: Execution 起動フロー、AI スコアリングのサンプルコード、ポジションサイズ計算の入力例 等）について README に追加するか教えてください。