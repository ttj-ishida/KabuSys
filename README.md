KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群（戦略・発注・監視・リサーチ・AI 補助）を提供する Python パッケージです。  
主な設計方針は「本番環境とテスト（ペーパートレード）を分離」「外部 API 呼び出しは明示的・制御可能」「フェイルセーフ（API 失敗時は安全側にフォールバック）」です。

主要機能
--------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - KABUSYS_ENV による挙動切替（paper_trading 時は MockBrokerClient を使用し専用 DB に記録）
  - リスク管理（RiskManager）、注文マネージャ、リコンシリエーション等の統合
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）起動スクリプト（run_monitoring）
  - システム稼働率・データ鮮度・ポジション制約・ドローダウン監視
  - Kill Switch（特定条件で data/kill.flag を書き込み ExecutionEngine を停止）
  - MONITOR_POLL_INTERVAL でポーリング間隔指定（デフォルト 60 秒）
- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式で .env を生成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在・基本整合性チェック（--strict オプションあり）
- ペーパートレード検証レポート（tools/paper_verification_report）
  - 成果指標（稼働率・注文成功率・レイテンシなど）を期間指定で出力
- 研究用モジュール（research）
  - ファクター計算（momentum / value / volatility など）や IC 計算
- AI 補助モジュール（ai）
  - ニュースセンチメント（OpenAI を利用）や市場レジーム判定
- ポートフォリオ構築ユーティリティ（portfolio）
  - 候補選定、重み計算、位置サイズ計算、セクター制約やレジーム乗数

前提・重要な環境変数
--------------------
必須（少なくとも本番運用では設定必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に利用する主な設定（デフォルトあり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト：development）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB データベースパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を利用する場合）
- PAPER_FILL_MODE: paper_trading 時のモック成行処理（instant / partial / never / reject）

セットアップ手順
---------------
1. リポジトリをチェックアウト / 展開
2. Python 環境を作成・アクティベート
   - 推奨: Python 3.10+
   - 仮想環境を作る: python -m venv .venv && source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は必要に応じて duckdb, psutil, openai, PyYAML などをインストール）
4. .env の準備（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザード完了後、python -m kabusys.validate_config で検証
5. データディレクトリ作成（必要に応じて）
   - デフォルト例: mkdir -p data logs
6. DB の初期化
   - 監視 DB は起動スクリプト実行時に init_monitoring_db() が実行されるため通常は明示的初期化不要
   - DuckDB のテーブルは研究/パイプライン側のスクリプトで準備

使い方（主要コマンド）
--------------------
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit 1）
- 実行エンジン起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - 実行前に .env の KABUSYS_ENV を設定してください（paper_trading の場合は paper 用 DB に書き込まれる）
  - 実行はデーモン化などでプロセスマネージャに任せて運用可能（スクリプト内で PID ファイルや stop flag を扱います）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは常に本番の sqlite_path を参照（環境に依らず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI 周り（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - ai モジュールは明示的に呼び出すか上位のスケジューラから実行

停止・Kill Switch
-----------------
- 実行中の ExecutionEngine を手動で停止したい場合:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検出して安全に停止処理を行います（run_execution は起動前にこのフラグが既にあると起動しません）。
- Kill Switch（自動停止条件）
  - RiskMonitor 等が条件を満たすと data/kill.flag を作成して ExecutionEngine に停止指示を出す設計です。
  - KILL_FLAG_CLEAR_ON_START 環境変数で起動時に kill.flag を自動クリアするか制御（本番では 0 推奨）

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一管理
- デフォルトは logs/<app_name>.log に日次ローテーションで出力、30日保持
- すべての起動スクリプト（monitoring, execution 等）は最初に setup_logging を呼びます

データベース（概略）
-------------------
- SQLite（監視・発注ログ）
  - デフォルト: data/monitoring.db
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - init_monitoring_db() にてテーブルと必要なマイグレーションを作成・保証
- DuckDB（時系列価格・リサーチ）
  - デフォルト: data/kabusys.duckdb
  - research/ai モジュールは DuckDB 接続を受けて計算・クエリを実行

設定例（.env の抜粋）
-------------------
例（ファイルに保存しないでください。ウィザードで生成してください）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（KABUSYS_ENV, パス類, 各種閾値）
- config_setup.py
  - .env 対話ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID ファイル / stop flag 対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- execution/
  - BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等（発注関連）
- monitoring/
  - monitoring_db.py — SQLite 永続層（init + MonitoringDB）
  - system_monitor.py — CPU/MEM/DISK/データ鮮度 / プロセス検出
  - trade_monitor.py — 発注ログ監視（滞留注文検出・レイテンシ異常など）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の作成 / クリア
  - alert_manager.py — （LINE 等への通知管理、別ファイルとして存在）
  - monitoring_engine.py — 各 monitor を統合してポーリング
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・解析
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF + LLM）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — psutil を使った優先度・affinity 設定

注意点 / 運用上のヒント
--------------------
- paper_trading は本番 DB と「完全分離」される設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI 等の外部 API はキーが必須で、呼び出しで失敗した場合は多くの処理でフォールバック（0.0 等）して例外を上位に伝えない設計になっています。API 呼び出しのリトライやエラー処理は各モジュールで実装済みです。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限不足で失敗した場合は警告ログが出ますが処理は継続します。
- ローカル開発では KABUSYS_ENV=development を推奨。KABUSYS_ENV=live は本番扱いとなり注意喚起が出ます。
- .env は絶対に Git にコミットしないでください。

トラブルシュート
----------------
- 設定検証でエラーが出る場合: python -m kabusys.validate_config を実行して指摘箇所を修正
- ログファイルが作成されない場合: LOG_DIR / 権限を確認。logging_setup はディレクトリ作成に失敗した場合にコンソール出力のみで継続します
- OpenAI 呼び出し関連: OPENAI_API_KEY の有無、ネットワーク、API 使用上限を確認

ライセンス・開発情報
-------------------
- パッケージメタ情報は kabusys.__version__（現状 0.1.0）に格納されています。
- コード/設計に変更を加える場合は、テストと validate_config の実行を忘れないでください。

お問い合わせ
------------
実装上の疑問や運用に関する質問があれば、ソースコメントや各モジュール（特に config.py / monitoring_db.py / logging_setup.py）を参照してください。README にない運用上の慣習や追加設定はプロジェクト内のドキュメント（例: PortfolioConstruction.md, StrategyModel.md）が存在する場合そちらも参照してください。

以上。