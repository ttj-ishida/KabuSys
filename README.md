KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム「KabuSys」のコアライブラリ群です。  
戦略構築、ポートフォリオ設計、発注実行、監視、研究・検証、AI を用いたニュース解析等の機能をモジュール化して提供します。

主な目的
- 戦略のバックテスト／研究（DuckDB を利用）
- 発注・ExecutionEngine（kabuステーション 等 のブローカークライアントを抽象化）
- 監視（System / Trade / Risk）と Kill Switch（自動停止）機能
- Paper Trading（本番と分離した DB）運用サポート
- ニュース NLP を使ったセンチメント評価（OpenAI API 利用）

以下はこのコードベースの README（日本語）です。

機能一覧
--------
- 設定管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行 / 監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、paper_trading 用 DB に記録
    - 停止フラグ（data/stop_requested.flag）で優雅に停止
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - 定期ポーリングで SystemMonitor を実行（MONITOR_POLL_INTERVAL で調整可）
    - 監視は本番 sqlite_path を使用（環境に依らず）
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存判定
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウン・ポジション数上限監視、dashboard 更新
  - KillSwitch: しきい値を満たした場合に data/kill.flag を書き込み Execution を停止
  - MonitoringDB: SQLite に監視ログを永続化（テーブル作成・マイグレーション含む）
- ポートフォリオ構築（portfolio）
  - 候補銘柄選定、等重／スコア重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等） — DuckDB を使用
  - 将来リターン、IC（情報係数）、ファクター統計
- AI（ai）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - logging_setup: 一貫したログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity の設定（クロスプラットフォーム）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.9+（typing の一部構文を利用）
- SQLite（標準で同梱）、DuckDB、外部パッケージ

推奨インストール例（venv）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML があると validate_config が YAML 検証を行います: pip install pyyaml

※ requirements.txt がある場合はそれを使用してください（本リポジトリに付属していない場合は上のパッケージを参照）。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）

.env の作成（対話式）
- python -m kabusys.config_setup
  - .env を対話式に生成・更新します（機密情報はマスク表示）

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

DB 初期化
- 起動スクリプト（run_execution / run_monitoring）が MonitoringDB の初期化を行います。
- DuckDB ファイルはツールや research モジュールから利用可能です（存在しない場合は作成されます）。

使い方（実行方法）
-----------------

1) 監視（Monitoring）を起動する
- 環境変数を設定（.env を用いるか export）
- 実行:
  - python -m kabusys.run_monitoring
- 説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（本番監視 DB）を使用
  - 停止にはプロジェクトルート/data/stop_requested.flag を作成する（スクリプトはこのファイルの存在を検知して終了）

2) 実行エンジン（ExecutionEngine）を起動する
- 環境変数 KABUSYS_ENV によって挙動が変わる:
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - live/development: settings.sqlite_path を使用（実際のブローカー接続は BrokerFactory が提供）
- 実行:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると起動中スレッドが検知して優雅に停止します
  - KillSwitch により data/kill.flag が作成されると Execution 側で検知可能（Settings.kill_flag_path）

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます（--db オプションでも指定可）

4) AI 関連（ニューススコア／レジーム判定）
- プログラムから呼び出す:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
- 注意:
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または引数で指定）
  - API 呼び出しはリトライやフェイルセーフ処理を含みますが、API 負荷やコストに注意してください

運用上の注意
--------------
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用します。監視ログは本番 DB に残ります。
- run_execution は paper_trading 時に paper_sqlite_path を使用し、本番 DB と完全に分離されます。
- kill.flag（Settings.kill_flag_path）は KillSwitch により作成されます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされることがあるので、本番では 0 を推奨します。
- .env は絶対に Git にコミットしてはいけません（config_setup.py のヘッダにも警告あり）。
- logging: setup_logging() により stdout と日次ローテートログが生成されます。LOG_DIR 環境変数でログディレクトリを変更可能。

ディレクトリ構成（主なファイル）
--------------------------------

（src/kabusys 以下の主要モジュールを抜粋）

- __init__.py
  - パッケージ宣言（__version__ 等）
- config.py
  - Settings クラス: 環境変数の解決・型変換・検証、.env 自動ロードの実装
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前チェック CLI（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine 起動スクリプト（stop フラグ・PID ファイル管理）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL）
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API
  - system_monitor.py — CPU / メモリ / データ鮮度 / プロセス生存検査
  - trade_monitor.py — trade_logs をチェック（滞留注文・約定異常 など）
  - risk_monitor.py — ドローダウン・ポジション上限監視、dashboard 更新
  - kill_switch.py — 条件を満たせば kill.flag を書く
  - monitoring_engine.py — 各 Monitor を束ねるランナー
- execution/
  - BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等（発注ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定、等重/スコア重み
  - position_sizing.py — 株数計算・集約キャップ処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py — raw_news を OpenAI で解析し ai_scores に書き込む
  - regime_detector.py — MA200 とマクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

（補足）
- data/stop_requested.flag, data/kill.flag, data/execution.pid といったファイルは運用用の制御フラグや PID 保持に使用します。スクリプトはこれらの存在を監視・作成します。
- monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（カラム追加等）を含みます。

開発・拡張のヒント
-------------------
- research 系は DuckDB 接続を受け取り SQL を実行する純粋関数群です。データ投入（prices_daily, raw_financials 等）さえ用意すれば再利用できます。
- AI 呼び出し部分は API エラーに対するリトライや JSON バリデーションを慎重に扱っています。テスト時は _call_openai_api の差し替えを推奨。
- process_priority.set_cpu_affinity / nice の呼び出しは権限に依存するため、コンテナやサービスでの実行時は注意してください。

ライセンス・貢献
----------------
この README にはライセンス記載が含まれていません。実運用・配布する場合は適切な LICENSE を追加してください。  
バグ報告・プルリクエストは歓迎します。まず Issue を作成し、設計方針に沿った変更を提案してください。

補足質問や、特定モジュール（例: ExecutionEngine の設定方法、AI 部分のローカルテスト方法、DuckDB 用データ準備方法）のドキュメント化が必要であればお知らせください。必要に応じてコマンド例や短いコードスニペットを追加します。