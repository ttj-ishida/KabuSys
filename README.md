KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。  
主な役割は以下の通りです。

- 注文実行（ExecutionEngine / Broker クライアント、リスク管理、オーダー管理）
- システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存監視）
- リスク監視（ドローダウン・ポジション上限監視）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- ペーパートレード検証レポート作成ツール

設計上のポイント
- .env（環境変数）により挙動を切替可能（KABUSYS_ENV: development / paper_trading / live）
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）
- 監視（monitoring）は環境に関わらず本番の sqlite_path を使用してログを残す
- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力
- OpenAI を用いる処理は API キー（OPENAI_API_KEY）が必要。API 失敗時はフェイルセーフで継続する実装がなされています

機能一覧
--------
- 設定管理
  - .env 自動ロード / 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行系
  - run_execution.py: ExecutionEngine の起動スクリプト（本番 / ペーパー切替）
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整）
  - 各種 Monitor（SystemMonitor, TradeMonitor, RiskMonitor）と MonitoringEngine
  - KillSwitch（data/kill.flag による停止シグナル）
- ポートフォリオ構築
  - 候補選定・等重/スコア重み、ポジションサイズ算出、セクター制限、レジーム乗数
- 研究（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー 等）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM で評価して ai_scores に保存
  - regime_detector: ETF/ニュースから日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
---------------
前提
- Python 3.10 以上（コード中の型記法および動作環境を想定）
- DuckDB（Python パッケージ）、psutil、openai（AI 機能を使う場合）、PyYAML（設定検証で YAML を検査する場合）

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

（必要に応じて pip freeze で requirements.txt を作成してください）

.env の作成
- 対話式で .env を生成する:
  - python -m kabusys.config_setup
- もしくは .env.example を参考に .env を手動作成
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要オプション（抜粋）:
  - KABUSYS_ENV (development / paper_trading / live)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用、任意）

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

使い方
------

設定ウィザード・検証
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
  - 問題があれば出力に従って修正してください

実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録（本番 DB と分離）
  - 停止制御: data/stop_requested.flag を置くと監視スレッドが検出して停止を試みます
  - 実行プロセスは data/execution.pid に PID を書きます

監視ループ（Monitoring）
- 起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
- 監視対象:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、実行プロセス存在）
  - TradeMonitor（約定/滞留注文の検出等）※実装の詳細に依存
  - RiskMonitor（ドローダウン・ポジション上限）
- 注意:
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite）を使用します（監査ログ一元化）

Kill Switch（手動停止）
- KillSwitch は data/kill.flag を書いて ExecutionEngine に停止を促します
- KillSwitch は監視・リスク条件に基づいて自動的に書き込まれることがあります
- 起動時に KILL_FLAG_CLEAR_ON_START を 1 にすると自動クリアしますが、本番では 0 を推奨

Paper Trading 検証レポート
- 生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- 確認できる指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など

AI（プログラム呼び出し）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行。api_key 未指定なら OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に市場レジームを計算して DB に書き込む

ログ
- ログは stdout と logs/<app_name>.log（日次ローテーション・30日保持）に出力
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます

停止・強制終了
- run_execution / run_monitoring は stop フラグファイル（data/stop_requested.flag）や kill.flag を監視して停止します
- 必要に応じて flag ファイルを削除して再起動してください

ディレクトリ構成
----------------
（リポジトリの src/kabusys を基準にした主要ファイル・モジュール一覧）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - data/                    — （デフォルトの DB / PID / flag 保存先）
  - logs/                    — ログファイル出力先（デフォルト）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・MonitoringDB ラッパー
    - system_monitor.py      — システム監視ロジック
    - risk_monitor.py        — ドローダウン・ポジション監視
    - trade_monitor.py       — 注文監視（実装参照）
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 操作用ユーティリティ
    - alert_manager.py       — 通知管理（LINE など、実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選択・重み計算
    - position_sizing.py     — 株数計算・キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py     — レジーム判定（ETF + マクロニュース）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート CLI

開発・運用上の注意
-----------------
- KABUSYS_ENV=live の場合は本番環境です。LINE 通知設定や Kill Switch の設定値を十分に確認してください。
- .env は絶対に VCS にコミットしないでください。
- OpenAI API を使用する機能は外部 API 呼び出しのため、API 利用料・レート制限に注意してください。失敗時のフォールバックはコード内に実装されていますが、重要な本番判定に使う際は運用ポリシーを検討してください。
- Monitoring は本番監査用の sqlite DB を更新します。テスト時は PAPER_TRADING_SQLITE_PATH を使うか、監視 DB のバックアップを取ってください。

よくあるコマンド一覧
-------------------
- .env を対話作成: python -m kabusys.config_setup
- 設定検証:          python -m kabusys.validate_config
- 実行エンジン起動:  python -m kabusys.run_execution
- 監視起動:          python -m kabusys.run_monitoring
- レポート生成:      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート・拡張
---------------
- 研究モジュール（research）は DuckDB に保存した prices_daily / raw_financials を前提としています。データ投入パイプラインは kabusys.data.pipeline を参照してください（別モジュール）。
- Broker クライアント実装は execution/broker_factory.py を通じて差し替え可能（モック / 実ブローカーの切替）。
- alert_manager（LINE等）や通知方法は拡張しやすい設計です。必要に応じて実装を追加してください。

ライセンス・責任
----------------
この README はリポジトリ内のコードから生成された要約です。実際の運用ではコードの各 docstring・ログ出力や config/*.yaml 等の設定も参照してください。自動売買は資金リスクを伴うため、十分なバックテストとモニタリング・運用ルールを確立してから本番運用してください。