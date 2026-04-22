# KabuSys

日本株向けの自動売買／リサーチ基盤（プロジェクトスニペットの README）。  
このリポジトリは、発注エンジン、監視、ポートフォリオ構築、ファクター算出、LLM を用いたニュース解析等を含むモジュール群で構成されています。

概要
- 日本株の自動売買ワークフローを想定したモジュール群（ExecutionEngine、Monitoring、Portfolio、Research、AI、Tools 等）。
- 本番/ペーパートレードを環境変数で切り替え可能（KABUSYS_ENV）。
- DuckDB を分析用 DB、SQLite を監視／発注ログ用 DB に使用。
- OpenAI API を用いたニュースセンチメント（ai.news_nlp）や市場レジーム判定（ai.regime_detector）に対応。
- ログは標準出力と日次ローテートのファイル出力（logs/）に出力。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパーの DB 分離、Broker クライアント抽象化、リスク管理、注文・照合ロジックの統合。
- Monitoring（run_monitoring.py、monitoring/*）
  - システム稼働監視（CPU/メモリ/ディスク、プロセス生存）、
  - 注文・約定ログ検査、リスク（ドローダウン・ポジション上限）監視、
  - Kill Switch（条件を満たすと data/kill.flag を作成して ExecutionEngine を停止）。
- Portfolio（portfolio/*）
  - 候補選定、重み計算、セクターキャップ適用、ポジションサイズ計算（単元株調整含む）。
- Research（research/*）
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン計算、IC 計算、統計サマリ。
- AI（ai/*）
  - news_nlp: raw_news を OpenAI に投げて銘柄毎の sentiment を ai_scores に格納。
  - regime_detector: ETF + マクロニュースを合成して market_regime を決定・永続化。
- Tools
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成。
- 設定管理 / ツール
  - config_setup.py: .env を対話式で作成／更新
  - validate_config.py: 起動前チェック（必須環境変数・config/*.yaml 等の検証）
  - Settings クラス（config.py）で環境変数を一元取得

動作要件（推奨）
- Python >= 3.10（型ヒントの union 演算子 etc. を使用）
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（Python 標準ライブラリ）
- （実運用時）kabuステーション API などブローカーの接続情報

セットアップ手順（ローカル開発向け）
1. リポジトリを取得
   - git clone ...（省略）
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt があればそちらを利用）
   - pip install duckdb psutil openai PyYAML
   - （実運用に応じて追加パッケージをインストール）
4. 環境変数設定
   - 対話式で .env を作成: python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）
   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI モジュール利用時必須)
     - LOG_LEVEL (DEBUG/INFO/...)
     - LOG_DIR (ログ出力先, デフォルト: logs/)
     - PAPER_FILL_MODE (paper_trading の約定振る舞い: instant|partial|never|reject)
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再実行

基本的な使い方（コマンド例）
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップ
  - 実行中に data/stop_requested.flag が作られると安全に停止する
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
  - 監視は常に本番 sqlite_path を使う（環境にかかわらず同じ監視 DB を使用）
  - 監視ループも stop_requested.flag により停止
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI 関連（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY の設定が必要（引数で渡すことも可）

警告・運用上の注意
- .env は絶対に Git にコミットしないこと（config_setup.py のヘッダにも注記）。
- KABUSYS_ENV=live は本番発注が行われるため、設定（API パスワード・通知設定等）を慎重に確認すること。
- Monitoring の KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で停止される仕組み。KILL_FLAG_CLEAR_ON_START に注意（本番では 0 推奨）。
- ログディレクトリ作成に失敗した場合、コンソール出力のみで継続する設計。
- OpenAI API 呼び出しは rate-limit・一時エラーに対してリトライを実装しているが、API キーや利用上限に注意。

ログ
- デフォルト: logs/<app_name>.log（アプリ起動時に setup_logging が適用される）
- ローテーション: 日次、30 日分保持
- コンソール出力は stdout に送られる（cron 等でリダイレクトしやすい）

データ / フラグファイル（デフォルト）
- data/monitoring.db — 監視 DB（SQLite。Settings.sqlite_path）
- data/paper_trading.db — ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — 分析用 DuckDB（Settings.duckdb_path）
- data/stop_requested.flag — run_* スクリプトの外部停止フラグ（存在を検知してループを抜ける）
- data/kill.flag — KillSwitch が書き込む実行停止フラグ（ExecutionEngine が検出して停止）
- data/execution.pid — ExecutionEngine の PID（Settings.pid_file_path）

主なディレクトリ構成（src/kabusys 配下の抜粋）
- __init__.py
- config.py — Settings クラス、.env 自動読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト
- execution/ — ExecutionEngine 関連（broker_factory, execution_engine, order_manager, risk_manager, reconciler, order_repository 等）
- monitoring/
  - monitoring_db.py — SQLite 永続化層 / API
  - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、プロセス監視
  - trade_monitor.py — 注文ログ監視（滞留注文・約定異常等）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成・管理
  - monitoring_engine.py — 各監視を束ねるエンジン
  - alert_manager.py —（アラート送信の抽象化、LINE 等への通知を想定）
- portfolio/ — 候補選定・重み算出・リスク調整・ポジションサイジング
- research/ — ファクター計算、特徴量探索、IC 等
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/ — 実行時に使用する DB / フラグファイル等（プロジェクトルート直下に作成される）
- tools/ — 実用スクリプト（paper_verification_report 等）
- utils/
  - logging_setup.py — ロギング初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・拡張のヒント
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）に依存するモジュールがあるため、分析用 DB のスキーマ整備が必要です。
- AI モジュールは OpenAI SDK の戻り値構造に依存するため、SDK 変更時はラッパー箇所を確認してください（_call_openai_api 等）。
- MonitoringDB は単純な CRUD 層に留めてあり、ビジネスロジックは各 Monitor 側にあります。DB マイグレーションは init_monitoring_db 内で最小限対応しています。

補足（トラブルシュート）
- MONITOR_POLL_INTERVAL が不正値（0 や非整数）の場合はデフォルト 60 秒にフォールバックします。
- 実行中にプロセス優先度の設定やログディレクトリ作成で権限エラーが出る場合は、実行ユーザーの権限・パス設定を確認してください。
- AI モジュール呼び出しは API キーが必須です。キー未設定のまま呼ぶと ValueError を投げます。

この README はコードベースの主要点をまとめたものです。詳細な実装や追加ファイル（broker 実装、strategy 実装、DB スキーマ定義等）は各サブモジュールのドキュメントやコメントを参照してください。必要であれば、導入手順（具体的な requirements.txt、DB 初期データ生成スクリプト等）や運用手順ドキュメントを追加で作成します。