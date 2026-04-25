KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株の自動売買・研究・監視のための内部ライブラリ群と起動スクリプトを含みます。README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下の機能を提供するモジュール群です。

- 自動売買エンジン（ExecutionEngine）
  - 本番 / ペーパートレードをサポート。ペーパートレード時は MockBrokerClient を使用し DB を分離。
- 監視（Monitoring）
  - システム / 注文 / リスク監視を行い、kill flag による停止やアラート発行を行う。
- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイズ決定、セクター制約、レジーム調整等の純粋関数群。
- リサーチ
  - DuckDB 上の価格・財務データからファクター計算・特徴量解析を実施。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュースセンチメント評価・市場レジーム判定（gpt-4o-mini 想定）。
- ユーティリティ
  - ロギング設定、プロセス優先度設定、設定ウィザード / 検証ツール等。

主な特徴・設計方針
- .env による設定管理を行い、プロジェクトルートの .env / .env.local を自動読み込み（無効化可）。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に利用（ペーパートレード時は専用 SQLite を使用）。
- LLM 呼び出しは冗長対策（バッチ、リトライ、レスポンス検証）を組み込む。
- 起動スクリプトは process priority を高く設定して実行。

機能一覧
---------
主要機能（抜粋）:

- 実行系
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV に応じてペーパー/本番切替）
  - order_manager / order_repository / reconciler / risk_manager 等を統合
- 監視系
  - run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔制御可）
  - monitoring_engine: System/Trade/Risk Monitor を束ねてアラート・Kill Switch 評価
  - monitoring_db: SQLite スキーマ初期化および永続化 API
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment
- リサーチ
  - factor_research: momentum/volatility/value 等のファクター計算（DuckDB ベース）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- AI
  - ai.news_nlp: ニュース記事を集約して LLM で銘柄ごとのセンチメントを算出・保存
  - ai.regime_detector: ETF MA とマクロセンチメントを合成して市場レジーム判定
- 開発支援ツール
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env と config/*.yaml の妥当性チェック
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

システム要件（想定）
-------------------
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 任意 / 開発時
  - PyYAML (validate_config の YAML 検証に使用)
- SQLite（組み込み）
- ネットワーク（OpenAI / kabu API を使う場合）

セットアップ手順
----------------

1. リポジトリをクローン / 作業ディレクトリへ移動
   - 例: git clone … && cd repo

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がなければ: pip install duckdb psutil openai
   - 開発用: pip install pyyaml

4. .env を作成
   - python -m kabusys.config_setup
     - 対話式で必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定できます。
   - もしくは .env.example を参考に手動で作成
   - 自動ロードは kabusys.config で行われる（プロジェクトルートの .env / .env.local）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit 1）になります。

6. データディレクトリの準備（必要に応じて）
   - デフォルトで以下のファイル/ディレクトリを使用します:
     - data/kabusys.duckdb (DuckDB のパスは DUCKDB_PATH)
     - data/monitoring.db (SQLite 監視 DB; PAPER_TRADING_SQLITE_PATH 指定で切替可)
     - logs/（ログ出力先）
   - 自動でディレクトリ作成する処理もありますが、権限や配置に注意してください。

使い方（起動例）
----------------

- .env の準備後、各種モジュールを起動できます。

1) ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV で制御）
   - python -m kabusys.run_execution
   - ペーパートレード環境:
     - KABUSYS_ENV=paper_trading を .env または環境変数で設定すると MockBroker を使用し、デフォルトで data/paper_trading.db に記録されます。

   - 停止:
     - data/stop_requested.flag を作成すると実行スクリプト側で検知して停止します。
     - Kill Switch（リスクからの強制停止）は data/kill.flag を書き込みます（ExecutionEngine はこれを検出して停止する設計）。

2) 監視ループを起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を秒で指定（デフォルト 60）。
     例: export MONITOR_POLL_INTERVAL=30

   - run_monitoring は Settings に基づき sqlite_path / duckdb_path を使用します（監視は本番 sqlite_path を参照）。

3) 設定ウィザード / 検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config [--strict]

4) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging により統一設定されます。
  - stdout に StreamHandler（標準出力）
  - ファイルは logs/<app_name>.log に日次ローテーション（30 日保持）
- ログレベルは LOG_LEVEL 環境変数で制御（デフォルト INFO）

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring 用ポーリング間隔）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止のためデフォルト 0 を推奨）

停止・Kill 動作
----------------
- run_execution/run_monitoring ではプロジェクトルートの data/stop_requested.flag を監視して正常停止します。
- KillSwitch（監視側）は data/kill.flag を作成して ExecutionEngine に停止を促します。
- PID ファイル: data/execution.pid が実行時に使われます（設定で変更可能）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと説明です（抜粋）。

- src/kabusys/
  - __init__.py                       — パッケージ定義（バージョン等）
  - config.py                         — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py                   — 対話式 .env ウィザード
  - validate_config.py                — 起動前チェック CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/               — 発注 / エンジン関連（Engine, BrokerFactory 等）
- src/kabusys/monitoring/
  - monitoring_db.py                  — SQLite スキーマ初期化 / 永続化 API
  - system_monitor.py                 — システム / データ鮮度監視
  - trade_monitor.py                  — 注文ログ監視（滞留注文・約定異常等）
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - monitoring_engine.py              — 各 Monitor を束ねる
  - kill_switch.py                    — kill flag の生成 / 管理
  - alert_manager.py                  — （アラート発行の抽象）
- src/kabusys/portfolio/
  - portfolio_builder.py              — 候補選定・重み付け
  - position_sizing.py                — 株数決定・スケーリング
  - risk_adjustment.py                — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py                — モメンタム・ボラティリティ・バリュー計算（DuckDB）
  - feature_exploration.py            — IC/将来リターン/統計
- src/kabusys/ai/
  - news_nlp.py                       — ニュースセンチメント（OpenAI）
  - regime_detector.py                — 市場レジーム判定（MA + マクロセンチメント）
- src/kabusys/tools/
  - paper_verification_report.py      — ペーパートレード検証レポート生成ツール
- src/kabusys/utils/
  - logging_setup.py                  — 共通ログ設定
  - process_priority.py               — プロセス優先度 / CPU affinity 設定

注意事項 / ベストプラクティス
----------------------------
- 本番環境（KABUSYS_ENV=live）では .env の管理に注意してください（.env をリポジトリに含めないこと）。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（キルフラグが自動でクリアされるため）。
- OpenAI を使う処理は API キーと費用に注意して運用してください。失敗時はフェイルセーフで継続する実装が多いですが、期待どおりの結果が得られない可能性があります。
- DuckDB / SQLite ファイルはバックアップを推奨します（データ損失リスクを考慮）。

開発・寄稿
-----------
- 新しい機能追加やバグ修正は PR を送ってください。重要な設計決定（DB スキーマ変更など）はドキュメント化をお願いします。
- config/*.yaml（各種設定テンプレート）の変更は validate_config に影響します。validate_config は PyYAML が無ければ内容検証をスキップします。

ライセンス
----------
（この README にはライセンス情報が含まれていません。適宜 LICENSE ファイルをリポジトリに追加してください。）

付録: よく使うコマンドまとめ
----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

以上。何か特定のファイルやモジュールについて詳しいドキュメント（関数仕様、DB スキーマ、設定例など）が必要であれば教えてください。必要に応じて README に追記します。