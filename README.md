README
=====

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
戦略計算（ファクター、ポートフォリオ構築、ポジションサイズ計算）、注文実行エンジン、監視・アラート、ペーパートレード検証、LLMを使ったニュースセンチメント評価などのコンポーネント群を含みます。  
コードは純粋関数的なポートフォリオロジックと、SQLite / DuckDB を用いたデータ永続化・分析基盤、kabuステーション等のブローカークライアントを組み合わせて設計されています。

主な機能
--------
- 戦略・リサーチ:
  - モメンタム、ボラティリティ、バリュー等のファクター計算（duckdb を用いた高速集計）
  - 将来リターン計算、IC（Information Coefficient）や基本統計量の算出
- ポートフォリオ構築:
  - 候補選定、等配分／スコア加重、リスクベースのポジションサイズ計算
  - セクター集中制限、レジームに応じた乗数調整
- 注文実行（ExecutionEngine）:
  - 実際のブローカーまたは MockBroker を用いたペーパートレード対応
  - 注文管理、リコンシリエーション、リスク管理（利用率・ポジション上限・サーキットブレーカー等）
- 監視（Monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard テーブルを SQLite に永続化
  - LINE を使ったアラート送信（AlertManager）
  - Kill Switch：ルールに基づいて data/kill.flag を書き込み、ExecutionEngine を安全に停止
- AI（OpenAI）連携:
  - ニュース集合を LLM へ送り銘柄ごとのセンチメントスコアを ai_scores に保存（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF ma200 とマクロ記事の LLM 評価を合成）
- ツール:
  - ペーパートレード検証レポート生成ツール（paper_verification_report）
  - .env 作成ウィザード（config_setup）と起動前検証（validate_config）

前提・依存
-----------
主な依存ライブラリ（環境によってバージョンが必要です）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- (オプション) PyYAML（config/*.yaml の中身検証に使用）

インストール（例）
-----------------
1. リポジトリをクローンして仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がある前提）:
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも以下を入れてください:
     - pip install duckdb psutil requests openai

環境変数 (.env)
----------------
本システムは .env ファイルまたは環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml が存在する場所）で行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（必須 / 推奨）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラートを LINE で受ける場合)

.env 作成ウィザード:
- python -m kabusys.config_setup

設定整合性検証:
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱いになります。

主な実行方法
-------------
1. ExecutionEngine（注文実行）
   - 本番/ペーパートレードを切り替える:
     - KABUSYS_ENV=paper_trading で起動すると MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
   - 起動:
     - python -m kabusys.run_execution
   - 実行中は data/execution.pid を作成し、停止は data/stop_requested.flag を作るか Kill Switch（data/kill.flag）で行います。

2. Monitoring（監視ループ）
   - モニタリングのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可（デフォルト 60 秒）。
   - 起動:
     - python -m kabusys.run_monitoring
   - 検出されたアラートは LINE に通知可能（設定されている場合）。監視は常に本番用 sqlite_path を参照します（監視 DB は環境に依らず本番のパスを使用する設計）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスの指定:
     - --db /path/to/paper_trading.db（または環境変数 PAPER_TRADING_SQLITE_PATH）

4. AI 周り
   - ニュースのセンチメント付与:
     - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY が必要（api_key を直接渡すことも可）
   - 市場レジーム判定:
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill Switch・フラグファイル
--------------------------------
- run_execution / run_monitoring はプロジェクトルート/data 配下のフラグファイルを参照します。
  - data/stop_requested.flag : 物理的に存在すると run_* スクリプトのループを止めます（外部プロセスからの停止依頼用）。
  - data/kill.flag : KillSwitch が書き込むファイルで、ExecutionEngine に「安全停止」を要求します（実際の挙動は設定に依存）。
- 起動時の挙動について:
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアする（本番では危険なのでデフォルト 0 推奨）。

注意点 / 設計上の重要事項
--------------------------
- Monitoring は常に本番用の sqlite_path を参照する設計です。環境（KABUSYS_ENV）にかかわらず監視 DB を分離して運用してください。
- Paper Trading 時は paper_sqlite_path を使用し、本番 DB と分離します。
- OpenAI 呼び出しはエラー時にリトライとフォールバックを行うが、APIキーの管理は慎重に行ってください。
- process priority / CPU affinity は psutil を使って設定します。権限不足や未対応 OS の場合は警告を出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                      — パッケージ定義、バージョン
- config.py                        — 環境変数／設定管理（自動 .env ロード、Settings クラス）
- config_setup.py                  — .env 生成ウィザード（対話式）
- validate_config.py               — 起動前設定検証 CLI
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py                     — ニュース→LLM→銘柄スコア処理
  - regime_detector.py              — 市場レジーム判定
- monitoring/
  - monitoring_db.py                — SQLite テーブル初期化／永続化 API
  - system_monitor.py               — CPU / メモリ / データ鮮度 / PID チェック
  - trade_monitor.py                — 注文滞留・約定異常チェック
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - monitoring_engine.py            — 各 Monitor を束ねる実行ループ
  - alert_manager.py                — LINE 通知
  - kill_switch.py                  — Kill Switch（flag 書込み）
- execution/                        — (実行エンジン関連: broker_factory, execution_engine 等)（実装の一部がサンプル）
- portfolio/
  - portfolio_builder.py            — 候補選定・重み計算
  - position_sizing.py              — 株数算出、丸め、aggregate cap
  - risk_adjustment.py              — セクター上限制御、レジーム乗数
- research/
  - factor_research.py              — momentum/value/volatility 等の計算
  - feature_exploration.py          — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py    — ペーパートレードの PASS/FAIL レポート生成
- utils/
  - process_priority.py             — プロセス優先度／CPU-affinity 設定ユーティリティ

サンプル .env（最低限）
---------------------
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI（AI機能を使う場合）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

よく使うコマンドまとめ
--------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
本リポジトリのライセンス表記や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（本コード断片には含まれていません）。

---

必要であれば README を英語版にする、依存の具体的なバージョンを列挙する、または起動時のログ例やトラブルシューティングを追加で作成します。どの情報を追加しますか？