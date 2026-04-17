# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

このリポジトリは日本株の自動売買システム（KabuSys）の一部実装です。取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース解析等のコンポーネントを含みます。本 README はコードベース（src/kabusys 以下）を参照して作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 主要環境変数（.env）
- ディレクトリ構成（ファイル一覧の要約）

---

プロジェクト概要
- KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。
- 実行エンジン（ExecutionEngine）・注文管理・リスク管理・監視（Monitoring）・アラート送信・ポートフォリオ構築・ファクターリサーチ・AI を用いたニュースセンチメント解析などを含む設計です。
- 設定は .env ファイルから読み込み、環境（development / paper_trading / live）に応じて動作を切り替えます。

---

主な機能一覧
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading DB に記録（本番 DB と分離）。
- 監視ポーリング
  - run_monitoring.py: SystemMonitor を定期実行して system_status 等をログ。MONITOR_POLL_INTERVAL で間隔を調整可能。
- 設定管理・ウィザード・検証
  - config_setup.py: 対話式ウィザードで .env を生成／更新。
  - validate_config.py: .env / config/*.yaml の事前検証 CLI（--strict オプションあり）。
- 監視関連
  - monitoring_engine.py: 各 Monitor（SystemMonitor, TradeMonitor, RiskMonitor）を束ねる。
  - SystemMonitor: プロセス生存・CPU/メモリ/ディスク・データ鮮度をチェック。
  - TradeMonitor: 滞留注文・約定価格異常を検出。
  - RiskMonitor: ドローダウンやポジション上限を監視しリスクログを作成。
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止。
  - AlertManager: LINE Messaging API への通知（トークン未設定の場合はログに留める）。
- 戦略・ポートフォリオ
  - portfolio/*: 候補選定、重み計算、セクター制限、ポジションサイズ決定ロジック（純粋関数）。
- リサーチ
  - research/*: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）・将来リターン・IC・統計サマリ。
- AI（OpenAI）連携
  - ai/news_nlp.py: raw_news を LLM で解析して銘柄ごとのスコアを ai_scores テーブルへ書き込む。
  - ai/regime_detector.py: ETF（1321）MA 乖離とマクロニュースセンチメントを合成して市場レジーム判定を行い market_regime テーブルへ書き込む。
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析し検証レポート（稼働率・注文成功率・レイテンシ等）を出力。

---

セットアップ手順（ローカル開発用）
1. Python バージョン
   - Python 3.9+ を想定（コードでは型アノテーションと pathlib 等を使用）。
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール
   - 以下の主要ライブラリが利用されています（requirements.txt は含まれていないため手動でインストールしてください）:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config/*.yaml のパース検証をしたい場合）
   - 例:
     - pip install duckdb psutil openai requests pyyaml
4. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出されます）。
5. .env を用意
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に必要な値を設定してください（リポジトリに .env.example がない場合は config_setup を利用）。
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります。
7. DB 初期化
   - 実行スクリプトで内部的に監視テーブル等は初期化されます（MonitoringDB.init_monitoring_db が冪等に作成）。

---

使い方（主要スクリプト・CLI）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（デフォルト）に記録します（本番 DB と分離）。
    - 実行中停止は data/stop_requested.flag を作成することで行います（プロジェクト内の stop フラグファイルパスを参照）。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視では常に本番 sqlite_path を使用（Monitoring は環境に依らず本番の sqlite_path を参照する設計）。
- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）
- AI 機能（モジュール利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と OpenAI API キー（引数 or OPENAI_API_KEY 環境変数）を必要とします。
- 停止フロー
  - 監視側が KillSwitch を発動すると data/kill.flag を作成し、ExecutionEngine 側は起動または稼働中にこのフラグを検知して停止する仕組みです。
  - stop ファイル: data/stop_requested.flag（run_* スクリプトで参照）

---

主要環境変数（.env）
- 必須（validate_config でもチェック）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行モード
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading 特有
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合必須）
- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN — LINE チャネルアクセストークン（任意）
  - LINE_USER_ID — 通知先ユーザー ID（任意）
- ログ/プロセス管理
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill flag path（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill_flag を自動クリアするか（0/1, 本番では 0 推奨）
- 監視ポーリング間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト 60）

注意: .env は絶対にコミットしないでください（API キーやパスワードを含むため）。

---

監視・停止に関する実装上のポイント
- Monitoring は system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを作成・更新します（init_monitoring_db）。
- KillSwitch はリスク条件（ドローダウンやポジション上限）を評価して data/kill.flag を書き込みます。ExecutionEngine は起動時・実行中にこのフラグを参照して停止します。
- run_execution/run_monitoring は data/stop_requested.flag を参照して優雅に終了します（手動停止のためのファイル）。
- Process priority と CPU affinity 設定ユーティリティ（utils/process_priority.py）を使用して、実行時に優先度を設定します。設定に失敗しても警告を出して続行します。

---

依存関係（主要）
- duckdb — データ分析・ファクタ計算に使用
- psutil — プロセス/リソース監視
- openai — LLM 呼び出し（news_nlp, regime_detector）
- requests — LINE API 呼び出し（AlertManager）
- PyYAML — config/*.yaml の検証（任意だが推奨）

requirements.txt がない場合は上記を手動でインストールしてください。

---

ディレクトリ構成（src/kabusys の主要ファイル／フォルダ）
- __init__.py (バージョン情報)
- config.py — 環境変数読み込み / Settings クラス（自動 .env ロード機能あり）
- config_setup.py — .env 作成ウィザード（CLI）
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・読み書き）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
- execution/ (一部参照されるモジュール群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など)
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
- tools/
  - paper_verification_report.py

注: 上記はこのリポジトリに含まれるモジュールのサブセットを示しています。execution パッケージ内の完全な実装はこの抜粋に含まれない場合があります。

---

運用上の注意
- 本番（KABUSYS_ENV=live）では env の値と config/*.yaml を慎重に確認してください（validate_config は live 時に追加警告を出します）。
- .env の KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch が自動でクリアされるため）なので 0 推奨。
- OpenAI API を使う処理はコストやレート制限に注意してください。news_nlp / regime_detector は 429 やネットワークエラーに対してリトライロジックを実装していますが、運用時の監視は必要です。
- DuckDB / SQLite のパスはデフォルトで data/ 以下に作られます。必要に応じて .env で変更してください。

---

開発・拡張のヒント
- research と portfolio のモジュールは純粋関数的に実装されているためユニットテストを書きやすく、外部副作用がほとんどありません。
- AI 呼び出し部分は API 呼び出し関数をテスト時にモックする想定で設計されています（unittest.mock.patch が想定されています）。
- monitoring_db.init_monitoring_db は冪等でスキーママイグレーション（カラム追加）にも対応しています。既存 DB 互換性を保ちつつ拡張可能です。

---

この README はコードベースのコメントと設計に基づいて作成しています。実際の運用にあたっては .env の設定、外部 API の認証情報、および production 用の運用手順（プロセスマネージャー、ログ集約、バックアップ等）を別途整備してください。必要であれば README を拡張してデプロイ手順や運用 Runbook を追加できます。