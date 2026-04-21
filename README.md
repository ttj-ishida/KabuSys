README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python コードベースです。本リポジトリには以下の主要機能が含まれます:

- 実行エンジン（ExecutionEngine）起動スクリプト（発注・リスク管理）
- 監視（Monitoring）コンポーネント（システム状態・注文・リスク監視）
- ポートフォリオ構築用の純関数群（銘柄選定・重み計算・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント／レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定）
- 設定ウィザード / 構成検証 / 運用用ツール（ペーパートレード検証レポート等）

主な設計方針:
- データベースは DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- 本番とペーパートレードを分離（KABUSYS_ENV による動作切替）
- ルックアヘッドバイアスに注意し、target_date ベースで計算する設計
- OpenAI API 呼び出しは失敗に寛容にしフェイルセーフ化

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔を指定可能（デフォルト 60 秒）
- 設定 / 検証
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: 環境変数と config/*.yaml の整合性チェック CLI（--strict オプションあり）
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成
- 監視関連
  - monitoring/monitoring_db.py: 監視用 SQLite テーブル初期化・CRUD
  - monitoring/system_monitor.py: CPU/メモリ/Disk・プロセス生存・データ鮮度検査
  - monitoring/trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py 等（監視ループのオーケストレーション）
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 発注株数計算（ロット丸め・aggregate cap）
  - portfolio/risk_adjustment.py: セクター制限・レジーム乗数
- 研究（Research）
  - research/factor_research.py: momentum/value/volatility 等のファクター計算（DuckDB 経由）
  - research/feature_exploration.py: 将来リターン計算・IC 計算・統計サマリー
- AI
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）で評価し ai_scores に書き込む
  - ai/regime_detector.py: ETF ma200 とマクロニュースを組み合わせて日次レジーム判定
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

セットアップ手順（ローカル開発向け）
------------------------------------
1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt が存在する場合: pip install -r requirements.txt
   - 最低限必要なパッケージ（機能に応じて）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証用）
   - 実行環境に応じて追加パッケージが必要となる場合があります。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定
   - 重要な設定例:
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、paper_trading モード時に使用）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

使い方（よく使うコマンド）
-----------------------
- 監視ループを起動（ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- 実行エンジンを起動
  - KABUSYS_ENV によって本番/ペーパーの挙動が切り替わります
  - python -m kabusys.run_execution

- .env の対話的作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でデフォルト DB を指定可能

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の MockBroker fill 動作: instant / partial / never / reject、デフォルト instant）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）

運用上の注意
------------
- Kill Switch / 停止フラグ:
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます。
  - run_execution/run_monitoring は data/stop_requested.flag で外部停止要求を検知する箇所があります。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で有効にするのは危険（kill.flag を意図せずクリアしてしまうため）。
- ログ:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトは呼び出します。
  - デフォルトログディレクトリ: logs/
  - 日次ローテーション（30 日分保持）
- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と単純なカラム追加（マイグレーション）を行います。既存データに注意してください。
- AI 呼び出し:
  - OpenAI API を使う処理（news_nlp, regime_detector）は API エラーに対してリトライやフォールバックを実装していますが、API キーと API 利用量にご注意ください。

ディレクトリ構成（抜粋）
-----------------------
（ソースは src/kabusys 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 — ExecutionEngine ほか（起動エントリと依存コンポーネント）
  - data/                      — 実行時に生成されるファイル例:
    - monitoring.db (SQLite)
    - paper_trading.db (ペーパートレード用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag / stop_requested.flag

開発・拡張のヒント
------------------
- 新しい設定を追加する場合は config.py の Settings クラスにプロパティを追加し、config_setup の _ITEMS に対応項目を追加すると .env ウィザードに反映されます。
- DuckDB を使った分析関数は接続を受け取る純粋関数として設計されており、ユニットテストが書きやすくなっています。
- OpenAI 呼び出しのテストは、各モジュール内の _call_openai_api をパッチして疑似レスポンスを返すことで行えます。
- 監視系（Monitoring）と Execution は DB（monitoring.db）を通じて緩やかに連携しています。kill.flag の運用ルールは運用ドキュメントに明記してください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスは該当ファイルやトップレベルの LICENSE を参照してください。
- 貢献（Issue/PR）は歓迎します。大きな設計変更は事前に Issue で相談してください。

以上。README に掲載してほしい追加情報（サンプル .env、要件ファイルの内容、運用手順の詳細など）があればお知らせください。