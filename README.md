README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムの骨組みを提供するリポジトリです。  
本リポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP / レジーム判定などの主要コンポーネントが含まれます。  
設計方針として、テスト用に paper_trading（ペーパートレード）モードを備え、本番環境（live）と開発環境（development）を切り替え可能です。環境変数および .env で設定を管理します。

主な機能
--------
- ExecutionEngine 起動・セッション管理（kabuステーション等への発注を担当）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading DB に記録して本番 DB と分離
- Monitoring（System / Trade / Risk）による定期的な健全性監視とアラート発行
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - stop_requested.flag による外部停止
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算）
- リサーチ機能（ファクター計算、将来リターン、IC 計算、統計サマリー）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）とレジーム判定（MA + マクロ感情の合成）
- ヘルパーツール
  - 環境設定ウィザード（.env 作成/更新）
  - 設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト

前提条件 / インストール
-----------------------
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証をする場合、必須ではない）
- 仮想環境作成例:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt が無い場合は上記パッケージを必要に応じてインストールしてください）

セットアップ手順（簡易）
--------------------
1. リポジトリルートに移動
2. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成（.env は絶対に Git にコミットしないでください）
3. 設定を検証:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict
4. データディレクトリ作成（必要に応じて）:
   - デフォルトの DB やログは data/ および logs/ 配下に作られます

主要な環境変数（代表）
---------------------
- 必須/重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録
- DB / ファイルパス
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト data/kill.flag）
- ログ
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）
- 監視
  - MONITOR_POLL_INTERVAL — 監視ループの間隔（秒、デフォルト 60）

使い方（起動 / CLI）
-------------------

- 環境設定ウィザード（.env を対話式で生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も FAIL 扱いで exit code 1

- ExecutionEngine を起動する（本番/ペーパートレードに応じて .env の KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づいて SQLite/ DuckDB に接続
    - paper_trading の場合は専用 SQLite を使用
    - 実行中は data/execution.pid を使用
    - data/stop_requested.flag が作成されると安全に停止
    - KILL FLAG: monitoring 側が条件に達すると data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() をループ（デフォルト 60 秒）
    - Monitoring は常に本番 sqlite_path を使用（環境に関わらず）
    - 停止: data/stop_requested.flag の作成でループを抜ける

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易な成功/失敗判定（稼働率・成功率・送信率・P95 レイテンシ等）

- AI 系機能（OpenAI を使う）
  - ニュース NLP / レジーム判定を動かすには OPENAI_API_KEY（環境変数）を設定
  - モジュール: kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime
  - API 呼び出しはリトライ・エラーハンドリングを備えています

停止 / Kill Switch
------------------
- 優雅な手動停止（両プロセス共通）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は次のポーリング/チェックで停止します
- Kill Switch（自動停止）
  - Monitoring の評価結果（ドローダウン超過 / ポジション上限 等）により KillSwitch が data/kill.flag を書き込みます
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定により kill.flag を自動クリアするか制御できます（本番では 0 を推奨）
- 実行中の PID 管理
  - data/execution.pid に PID を記録してプロセス管理に利用します

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます
  - コンソール（stdout）と日次ローテーションのファイルログ（logs/<app_name>.log）を生成
  - LOG_DIR / LOG_LEVEL によって設定を変更可能
  - ファイルハンドラの作成失敗時はコンソールログのみで継続します

データベース / 永続化
--------------------
- DuckDB: 分析用（デフォルト data/kabusys.duckdb）
- SQLite: 監視・発注ログ用
  - monitoring.db（デフォルト data/monitoring.db）
  - paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading 時に使用、デフォルト data/paper_trading.db）
- monitoring_db.init_monitoring_db() は DB スキーマを冪等に作成・マイグレーションします

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py ..................... 環境変数 / Settings 管理
  - config_setup.py ............... .env 対話式ウィザード
  - validate_config.py ............ 起動前設定検証 CLI
  - run_execution.py .............. ExecutionEngine 起動スクリプト
  - run_monitoring.py ............. Monitoring ポーリングループ起動スクリプト
  - data/ ......................... データ関連（DuckDB/SQLite 等、実行時に使用）
  - execution/
    - execution_engine.py (参照)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py ............. 監視用 SQLite の永続化層
    - system_monitor.py ............ システム状態・データ鮮度監視
    - trade_monitor.py (参照)
    - risk_monitor.py .............. ドローダウン・ポジション上限監視
    - kill_switch.py ............... Kill Switch 実装
    - monitoring_engine.py ........ 複数 Monitor を束ねるエンジン
    - alert_manager.py (参照)
  - portfolio/
    - portfolio_builder.py ......... 候補選定・重み計算
    - position_sizing.py ........... 発注株数計算・スケーリング
    - risk_adjustment.py ........... セクターキャップ・レジーム乗数
  - research/
    - factor_research.py ........... モメンタム/ボラティリティ/バリュー等ファクター計算
    - feature_exploration.py ....... 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py .................. ニュース NLP（OpenAI 呼び出し）と ai_scores 書き込み
    - regime_detector.py .......... レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py . Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py ............. ログ設定ユーティリティ
    - process_priority.py .......... プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のヒント
------------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含むため）
- KABUSYS_ENV=live のときは特に注意（LINE 通知の設定、KILL_FLAG_CLEAR_ON_START などを確認）
- monitoring は本番の SQLite を参照するため実運用時にはバックアップや権限制御を検討してください
- OpenAI API の呼び出しはコストやレート制限に注意。API キーの保護を徹底してください
- psutil を使った優先度設定は OS に依存するため、権限不足で失敗する可能性がある（ログに警告が出ます）

開発 / テスト
-------------
- 主要な関数群は副作用をなるべく持たない設計（純粋関数）になっています（portfolio、research 等）
- モジュール間の API 呼び出し（OpenAI 等）は内部で切り離し可能な実装になっており、単体テストでモックしやすく設計されています
- validate_config.py で依存する YAML の簡易検証を行います（PyYAML がない場合はスキップされます）

お問い合わせ / 貢献
-------------------
- バグ報告・機能提案は Issue を立ててください
- プルリクエストは README に記載の開発ルール（テスト、型チェック、ドキュメント）に従ってお願いします

以上がこのコードベースの概要と使い方のまとめです。初回セットアップはまず python -m kabusys.config_setup → python -m kabusys.validate_config → python -m kabusys.run_monitoring / python -m kabusys.run_execution の順を推奨します。