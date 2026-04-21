KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の軽量な実装です。  
主な目的は次のとおりです。

- 日次のファクター計算や将来リターン計算（DuckDB を利用）
- ポートフォリオ構築（候補抽出・重み算出・株数決定）
- 実行エンジン（実口座 / ペーパートレーディング切替）
- 監視（システム状態・注文ロギング・リスク監視・Kill Switch）
- ニュースの NLP（OpenAI を利用した銘柄センチメント）
- 開発用ユーティリティ（設定ウィザード、設定検証、検証レポート生成など）

このリポジトリはライブラリとしての利用と、コマンドラインスクリプトによる運用の両方を想定しています。

主な機能
---------
- 設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - Settings クラスで環境変数を型安全に取得・検証
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを環境変数 KABUSYS_ENV で切り替え
  - paper_trading 時は MockBrokerClient を使用し、DB を分離（data/paper_trading.db）
  - 実行中停止のための flag ファイル（data/stop_requested.flag / data/kill.flag）
  - プロセス優先度設定（高優先で動かすユーティリティ）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス存在チェック
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine / run_monitoring スクリプトによる定期ポーリング

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分／スコア加重の重み算出
  - セクター集中制限（apply_sector_cap）
  - ポジションサイズ算出（リスクベース／等配分／スコアベース）

- リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント算出（kabusys.ai.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - API 呼び出しはリトライ・検証・部分書き込みなどフェイルセーフ設計

- ツール
  - Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.9+（型ヒント等を利用）
- SQLite（標準ライブラリ sqlite3 を使用）
- 以下の外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config 検証で YAML をチェックする場合）

例（pip）
- 最低限:
  pip install duckdb psutil
- AI 関連を使う場合:
  pip install openai
- 設定検証で YAML を使う場合:
  pip install PyYAML

初期ファイル・ディレクトリ準備
- プロジェクトルートに移動し、data/ と logs/ を作成しておくと便利です。
  mkdir -p data logs

環境変数（.env）
- 対話式ウィザードで .env を生成:
  python -m kabusys.config_setup
- 主要な環境変数（必須 / デフォルト）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (paper_trading 用)
  - OPENAI_API_KEY — OpenAI を使う場合に必要
  - LOG_LEVEL — デフォルト: INFO
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消すか（0/1）

- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定検証
- 生成・編集後は検証を実行:
  python -m kabusys.validate_config
  --strict を付けると警告もエラー扱いになります。

使い方（コマンド）
-----------------

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ（デーモン／システム監視）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は monitoring 用の sqlite_path（Settings.sqlite_path）を常に使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

- 実行エンジン（トレード）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - 実行中の停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書き込まれることで行われます。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

- ライブラリ的利用（サンプル）
  from kabusys.research import calc_momentum
  from kabusys.ai import score_news
  # DuckDB 接続を渡して関数を呼ぶ

重要な運用ポイント
- AI 機能を利用する際は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・検証が入っていますが、API 使用料に注意してください。
- 本番環境（KABUSYS_ENV=live）では、LINE トークン等の通知設定を必ず確認してください（validate_config で注意喚起があります）。
- Kill Switch（data/kill.flag）を自動クリアする設定は本番では危険です。KILL_FLAG_CLEAR_ON_START はデフォルト 0 を推奨します。
- run_execution / run_monitoring は pid ファイル（data/execution.pid など）を作成します。プロセス管理に使用できます。
- ログは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）へ日次ローテーションで保存されます。

ディレクトリ構成（抜粋）
-----------------------

以下は主要モジュールの構成です（src/kabusys 配下）:

- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）

- config.py
  - Settings クラス、.env 自動読み込み、各種設定プロパティ

- config_setup.py
  - .env 対話式作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- __init__.py
  - パッケージメタ情報（__version__ など）

- utils/
  - logging_setup.py — 一貫したログ設定（コンソール + 日次ローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、プロセス監視
  - trade_monitor.py — 発注ログ・約定異常監視（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — data/kill.flag の書き込み
  - monitoring_engine.py — 各 Monitor をまとめて定期実行
  - alert_manager.py — 通知管理（LINE など、実装に依存）

- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数算出・集約キャップ
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティの計算
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー

- ai/
  - news_nlp.py — raw_news を OpenAI に送り銘柄別スコアを算出・ai_scores へ保存
  - regime_detector.py — MA200 乖離 + マクロニュースの LLM センチメントで日次レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- その他
  - data/ — 実行時に利用する SQLite / DuckDB / flag / pid 等を配置（デフォルト）
  - logs/ — ログファイル出力先（デフォルト）

補足（実装上の注意）
-------------------
- DB マイグレーション: monitoring_db.init_monitoring_db は存在チェック + ALTER TABLE による簡易マイグレーションを行います。
- DuckDB / SQLite 接続はスクリプトが管理します。monitoring は環境にかかわらず本番 sqlite_path を参照します（設計上の意図）。
- AI 呼び出しは外部 API の不安定さを考慮して、429 / タイムアウト / 5xx に対して指数バックオフのリトライを行います。レスポンスの JSON バリデーションも厳密に行われます。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

お問い合わせ
-----------
問題や質問があれば issue を立てるか、リポジトリのメンテナに連絡してください。

以上。README のテンプレートとして必要に応じて補足（依存パッケージの pinned バージョン、CI/デプロイ手順、実行例ログ等）を追加してください。