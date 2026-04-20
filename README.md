KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 運用支援ツール群です。本リポジトリは以下の役割を持つ主要コンポーネントを提供します。

- Execution：注文発行・注文管理・リスク管理を担う ExecutionEngine（本番 / ペーパートレード対応）
- Monitoring：システム稼働監視、取引・リスク監視、Kill Switch による停止制御
- Research：DuckDB を使ったファクター計算・特徴量解析
- Portfolio：銘柄選定・重み計算・ポジションサイズ計算（純粋関数）
- AI：ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定、各種 CLI（設定ウィザード・検証）

主な特徴
--------
- 本番 / ペーパートレードの切り替え（KABUSYS_ENV）
- Execution と Monitoring の分離（停止フラグ / PID 管理）
- DuckDB/SQLite を用いたデータ保存・分析
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（オプション）
- 日次ローテーションのログ出力（logs/<app>.log）
- .env 対話式作成ウィザードと設定検証ツール

セットアップ
------------
1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール
   - requirements.txt 等がある場合はそれに従ってください。
   - 主要依存例: duckdb, psutil, openai, pyyaml（任意: YAML 検証用）
3. プロジェクトルートに .env を作成する（対話ウィザード推奨）
   - ウィザード実行:
     python -m kabusys.config_setup
   - 主要環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に設定
     - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 用; デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1、デフォルト 0）
   - 自動 .env 読み込み:
     - プロジェクトルートが検出される場合、.env/.env.local を自動ロードします。
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定検証
-------
起動前に設定や必須ファイルを検証できます。

- 検証実行:
  python -m kabusys.validate_config
- 警告をエラー扱いにする（CI 等で使用）:
  python -m kabusys.validate_config --strict

使い方（実行例）
----------------
- Monitoring を起動（ポーリングで各監視を実行）:
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（監視データは本番 DB に記録）。

- ExecutionEngine を起動（注文発行）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録し本番 DB と分離します。
  - 起動時に data/stop_requested.flag が既に存在すると起動を行いません。
  - 実行中は data/execution.pid に PID を出力します（設定に依存）。

- Paper Trading 検証レポートの生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- ログの設定:
  - 全アプリケーション共通で kabusys.utils.logging_setup.setup_logging を使用。
  - デフォルトログディレクトリ: logs/
  - ログローテーション: 日次、30世代保持

停止 / Kill Switch
------------------
- 強制停止フラグ:
  - モジュールの多くはプロジェクトルート/data/stop_requested.flag を監視しています（run_monitoring/run_execution も参照）。
  - Monitoring 側の KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で停止トリガーとなります（冪等に書き込み）。
- 起動時に kill.flag を自動でクリアしたい場合:
  - KILL_FLAG_CLEAR_ON_START=1（本番では 0 を推奨）

AI 機能について
---------------
- OpenAI を使う機能:
  - kabusys.ai.news_nlp.score_news: ニュースを集約して銘柄別センチメントを ai_scores に書き込む。
  - kabusys.ai.regime_detector.score_regime: ETF の MA200乖離とマクロニュースを用いて市場レジームを判定し market_regime に保存する。
- 必要: OPENAI_API_KEY（引数として渡すことも可能）
- 再試行・エラーハンドリング: レート制限や一時的な通信エラーに対してエクスポネンシャルバックオフを実装（部分失敗でのフェイルセーフあり）

主要モジュール一覧（抜粋）
------------------------
- run_monitoring.py — SystemMonitor ポーリング起動
- run_execution.py  — ExecutionEngine 起動（本番 / ペーパートレード分離）
- config.py         — 環境変数/.env の読み込みと Settings クラス
- config_setup.py   — 対話式 .env 作成ウィザード
- validate_config.py— 設定検証 CLI
- tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ai/
  - news_nlp.py     — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（OpenAI + MA200）
- research/
  - factor_research.py    — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py— 将来リターン計算、IC、統計サマリ
- portfolio/
  - portfolio_builder.py  — 候補選定・重み計算
  - position_sizing.py    — 株数・投下資金計算
  - risk_adjustment.py    — セクターキャップ・レジーム乗数
- monitoring/
  - monitoring_db.py      — SQLite のスキーマ初期化・永続化 API
  - system_monitor.py     — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - trade_monitor.py      — (取引監視ロジック)
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag の作成/評価
  - monitoring_engine.py  — 各 Monitor を束ねたポーリングエンジン
- utils/
  - logging_setup.py      — ログ初期化ユーティリティ
  - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

監視用 SQLite スキーマ（monitoring_db が作成）
--------------------------------------------
monitoring_db.init_monitoring_db により以下テーブルが作られます（冪等）:

- system_status: CPU/MEM/DISK/プロセス正常性の時系列ログ
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等、latency_ms カラム含む）
- positions: 保有ポジション
- risk_logs: リスクイベントログ（DRAWDOWN_ALERT, POSITION_LIMIT 等）
- dashboard: 集計情報（id=1 の単一行。portfolio_value/cash/drawdown/open_order_count/position_count/peak_value）

プロジェクト構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_monitoring.py
- run_execution.py
- tools/
  - __init__.py
  - paper_verification_report.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - (trade_monitor.py など)
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py
- execution/ (ExecutionEngine 関連; BrokerFactory, OrderManager 等)

注意事項 / ベストプラクティス
-----------------------------
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config で複数の警告チェックあり）。
- .env は機密情報を含むため、絶対に Git にコミットしないでください。
- Monitoring は常に本番の sqlite_path を参照して監視ログを保存します。ペーパートレードは run_execution 側で paper_sqlite_path に分離されます。
- OpenAI API を有効にする場合、APIキーの管理に注意してください（使用料・レート制限）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ログ設定は堅牢に実装されています）。

問い合わせ / 開発メモ
--------------------
- 各モジュールは比較的疎結合に設計されています。ユニットテストやモック差し替えがしやすいように、外部呼び出し（OpenAI, ブローカー）はファクトリ/ラッパー経由で扱われています。
- 追加の CLI やデータパイプラインは research / data サブパッケージに実装を追加してください。

以上がこのコードベースの概要と基本的な使い方です。必要があれば、各モジュールの詳細な API ドキュメントや起動時のトラブルシューティングを別途作成します。