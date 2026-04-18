README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリです。  
主な機能は以下のとおりです。

- ExecutionEngine（発注エンジン）: 実際のブローカー/モックブローカーと連携して発注を行う
- Monitoring（監視）: システム稼働状況、データ鮮度、取引・リスク指標を定期的に記録・アラートする
- Portfolio construction: 候補選定・重み計算・ポジションサイジング等の純粋関数群
- Research モジュール: ファクター計算、特徴量解析、IC 等の研究用ユーティリティ
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存／市場レジーム判定
- 付帯ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成など

主な設計方針
- 実取引とペーパートレードを分離（KABUSYS_ENV により挙動切替）
- DuckDB を使った分析向けデータ、SQLite を使った監視ログ保存
- LLM 呼び出しは失敗してもフェイルセーフで継続（部分的なスコア取得）
- .env を用いた環境設定、対話式ウィザード・検証機能を提供

機能一覧
--------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 環境設定 / 検証
  - python -m kabusys.config_setup : .env 作成ウィザード（対話式）
  - python -m kabusys.validate_config : .env と config/*.yaml の簡易検証 CLI
- 研究 / ポートフォリオ
  - kabusys.research: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等
  - kabusys.portfolio: 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI
  - kabusys.ai.news_nlp.score_news : raw_news を LLM でスコア（OpenAI 必須）
  - kabusys.ai.regime_detector.score_regime : 市場レジーム判定（OpenAI 必須）
- ツール
  - python -m kabusys.tools.paper_verification_report : ペーパートレード DB から検証レポートを出力
- 監視用 DB ヘルパー: monitoring_db.py（テーブル作成 / 永続化 API）
- ログ / プロセスユーティリティ
  - 設定済みのロギングセットアップ（logs/<app>.log 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトの具体的なバージョン要件は pyproject.toml 等で調整してください）
- 外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai （AI機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合）

例（仮想環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば pip install -r requirements.txt）

3. プロジェクトルートに移動（README と同じ階層に pyproject.toml/.git 等があることが望ましい）

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を生成（例を下記に記載）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う環境変数（一部）
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使い data/paper_trading.db に記録
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR : ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY : OpenAI を使う場合に必要（ai モジュール・regime_detector）

.env の最小例
- 以下をプロジェクトルートの .env に保存（機密情報は実際のトークンに置き換える）
  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

使い方
------
起動スクリプト（プロダクション / 開発）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が存在する場合は起動しません
    - 実行中は data/execution.pid に PID を書きます（設定により変更可）
    - 停止は stop_requested.flag の作成または ExecutionEngine.stop 呼び出し（監視側からの kill.flag によるシグナル）で行います

- Monitoring を起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは共通にしたい設計）
    - 停止はプロジェクトルート/data/stop_requested.flag を置くことで行います

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)

AI 機能
- OpenAI を利用する機能（news_nlp / regime_detector）は OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡してください
- 例: kabusys.ai.news_nlp.score_news(conn, date_obj, api_key="sk-...")

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を使用

停止 / Kill Switch
- Monitoring の KillSwitch は条件（ドローダウン・ポジション上限など）を満たすと data/kill.flag に理由を書き込みます。
- ExecutionEngine は kill.flag の存在を検知し安全に停止することで、運用者がフラグで強制停止できます。
- また start/stop フラグとして data/stop_requested.flag が利用されています（run_* スクリプトが参照）。

ログ設定
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテートで出力されます
- 環境変数 LOG_DIR や LOG_LEVEL で制御できます
- logging を統一的に設定するユーティリティ: kabusys.utils.logging_setup.setup_logging

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 以下の主要構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               # 環境変数読み込み・Settings クラス
  - config_setup.py         # .env 対話式ウィザード
  - validate_config.py      # 起動前検証 CLI
  - run_execution.py        # ExecutionEngine 起動スクリプト
  - run_monitoring.py       # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               # ExecutionEngine 周りの実装（OrderManager, BrokerFactory 等）
  - data/                    # データパイプライン・DuckDB スキーマ関連
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の内容を慎重に管理してください（.env は絶対に Git へコミットしない）
- KILL/STOP フラグの扱いに注意:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では危険（デフォルト 0 を推奨）
- OpenAI API を利用する機能は API コストとレイテンシに注意。失敗時はフェイルセーフで継続する設計ですが、期待する結果が得られない可能性があるためログ監視を推奨
- データベースファイル（DuckDB / SQLite）は適切なバックアップ・ディスク容量管理をしてください

開発者向けメモ
---------------
- DB 初期化: monitoring_db.init_monitoring_db は冪等にテーブルを作成し、必要ならマイグレーション（カラム追加）を行います
- テスト: 各モジュールは副作用を抑えた純粋関数（portfolio 等）と副作用を持つ IO 層（monitoring_db, ai モジュール）に分かれているためユニットテストが書きやすい設計です
- LLM 呼び出し部分はテスト時に _call_openai_api をモックする想定になっています

追加情報・問い合わせ
--------------------
- 実運用上の細かいパラメータ（リスク閾値、ポージション上限、ロットサイズなど）は config/*.yaml で管理することを想定しています（config ディレクトリ参照）
- さらに詳しい運用手順やデプロイ手順はプロジェクトの運用ドキュメントを参照してください（別途作成推奨）

以上。必要であれば README に含める具体的な .env サンプルや起動シーケンス図、systemd / supervisor 用のサービス定義テンプレートを追記します。どの情報が必要か教えてください。