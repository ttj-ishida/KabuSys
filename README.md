KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python ベースの小規模システムです。
本リポジトリには次の主要機能が含まれます:

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム状態・注文状況・リスク監視、Kill Switch による停止制御
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限など
- 研究モジュール: ファクター計算、フォワードリターン、IC 計算、特徴量統計
- AI モジュール: ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI API を利用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード / 検証ツール
- ツール: Paper Trading の検証レポート生成など

主な設計方針:
- DuckDB（分析用）と SQLite（監視・履歴用）を分離して使用
- Paper Trading（シミュレーション）は本番データベースと完全分離
- ルックアヘッドバイアス回避（target_date を明示的に渡す設計）
- フェイルセーフ: API 失敗時は例外を吸収して安全に継続する箇所が多い

機能一覧
--------
- 実行（run_execution.py）
  - ブローカークライアントの抽象化（本番 / モック切替）
  - OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動
  - 停止フラグ（data/stop_requested.flag）検知で安全停止
- 監視（run_monitoring.py, monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン検出
  - MonitoringEngine / KillSwitch / AlertManager による自動通知と停止制御
- 設定管理
  - config_setup.py: .env の対話式生成・更新ウィザード
  - validate_config.py: .env と config/*.yaml の事前チェック
  - Settings クラスで環境変数を一元管理（デフォルト値と検証ロジックあり）
- 研究（research/*）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - forward returns / IC / 統計サマリー
- AI（ai/*）
  - news_nlp: OpenAI でニュースを集約して銘柄別センチメントを計算→ai_scores へ書き込み
  - regime_detector: MA + マクロニュースを合成して market_regime に書き込み
- ツール（tools/*）
  - paper_verification_report: ペーパートレード DB から検証レポート出力
- ユーティリティ（utils/*）
  - logging_setup: 統一ログ設定（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度・CPU affinity のラッパ

前提条件（推奨）
----------------
- Python 3.10+
- DuckDB
- sqlite3（標準）
- psutil
- OpenAI SDK（AI 機能を使う場合）
- （任意）PyYAML（config の内容検証に使用）

セットアップ手順
--------------
1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml
   - 必要に応じてその他ライブラリを追加
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict

主要な環境変数（主なもの）
-------------------------
（Settings クラスに基づく。括弧内はデフォルト値 / 備考）

- KABUSYS_ENV (development | paper_trading | live) — 実行モード（default: development）
- JQUANTS_REFRESH_TOKEN — 必須 (J-Quants API 用)
- KABU_API_PASSWORD — 必須 (kabuステーション API 用)
- KABU_API_BASE_URL (http://localhost:18080/kabusapi) — kabu API ベース URL
- OPENAI_API_KEY — OpenAI を使う場合に必須
- DUCKDB_PATH (data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (data/monitoring.db) — 監視用 SQLite ファイルパス
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- LOG_LEVEL (INFO) — ログレベル
- LOG_DIR (logs) — ログディレクトリ（logging_setup で使用）
- KILL_FLAG_CLEAR_ON_START (0) — ExecutionEngine 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の MockBroker の約定挙動（instant/partial/never/reject）

実行方法（代表例）
------------------
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 監視スクリプトは data/stop_requested.flag を検知して終了します
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live で本番ブローカーが使われます。paper_trading は data/paper_trading.db へ記録して本番と分離
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能
- AI モジュール実行（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・制御関連
---------------
- 停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が存在を確認。作成すると起動中のループに停止シグナルが渡る
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に停止を要求（本番環境で重要）
- PID ファイル:
  - data/execution.pid — ExecutionEngine が書き込む PID ファイル（Settings.pid_file_path で指定可能）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で削除する（本番では 0 推奨）

ログ・DB の場所（デフォルト）
----------------------------
- ログ: logs/<app_name>.log（logging_setup で日次ローテーション）
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — Settings クラス、.env 自動ロードロジック
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite の永続化層（スキーマ初期化、CRUD）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py ...
- execution/  (実際の発注ロジック・OrderManager 等)
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py

運用・開発上の注意点
-------------------
- 本番（KABUSYS_ENV=live）では設定に十分注意してください。validate_config の警告は重要です。
- OpenAI を利用する機能は API コストとレイテンシに注意。APIキーは環境変数 OPENAI_API_KEY で管理してください。
- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- logging_setup はログディレクトリの作成に失敗するとファイル出力を無効化してコンソールのみで動作します（権限等を確認してください）。
- process_priority / cpu_affinity の設定は OS に依存し、権限不足で失敗することがあります（警告ログにより通知されます）。
- DB スキーママイグレーションは init_monitoring_db 内で軽微な追加カラム（例: latency_ms）を扱っています。外形の大きな変更は慎重に。

トラブルシューティング（簡易）
-----------------------------
- ログが書かれない:
  - LOG_DIR の作成権限、環境変数 LOG_LEVEL の設定を確認
- OpenAI 呼び出しでエラー:
  - OPENAI_API_KEY の設定、ネットワーク、API レート制限を確認
- ExecutionEngine がすぐ停止する:
  - data/stop_requested.flag や data/kill.flag の存在を確認
  - KILL_FLAG_CLEAR_ON_START の設定を確認（開発中のみ 1 にすること推奨）

その他
-----
- config/ 以下の YAML は generate 用スクリプトやテンプレートがある想定（存在しない場合は validate_config で警告）
- README に含めた以外の詳細設計（ドキュメント）はソース内の docstring を参照してください（各モジュールの説明・設計意図が記載されています）

必要であれば次の情報を README に追加できます:
- 推奨 requirements.txt の内容
- 具体的な systemd / supervisor 用のサービスユニット例
- デプロイ / CI ワークフローの手順

以上。補足したい項目や、運用手順（systemd サービス化や Docker 化）の雛形が必要であれば教えてください。