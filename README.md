KabuSys
=======

日本株向けの自動売買システム用ライブラリ／スクリプト群。  
トレード実行、監視、ポートフォリオ構築、リサーチ（ファクター計算）、
LLM を使ったニュースセンチメント評価など、運用に必要なコンポーネントを含みます。

プロジェクトの目的
-----------------
- 自動売買エンジン（ExecutionEngine）とその周辺ユーティリティ群を提供する
- 運用監視（System / Trade / Risk）と Kill Switch による安全停止機構
- DuckDB / SQLite を用いたデータ解析・ログ永続化
- Paper Trading（模擬発注）モードを用いた検証ワークフロー
- ニュース NLP（OpenAI）を用いたセンチメント評価・レジーム判定
- ポートフォリオ構築・サイズ計算などの純粋関数群（テスト容易）

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag）や kill.flag による外部停止をサポート
- Monitoring（run_monitoring.py / monitoring_engine）
  - SystemMonitor: プロセス・CPU/メモリ/Disk/データ鮮度監視
  - TradeMonitor: 発注ログの整合性/滞留注文/約定異常検出
  - RiskMonitor: ドローダウン／ポジション上限アラート、dashboard 更新
  - KillSwitch: 条件を満たした場合 data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager 経由で LINE などへ通知（トークン設定があれば）
- AI（kabusys.ai）
  - news_nlp.score_news: OpenAI を用いた銘柄ごとのニュースセンチメント評価（ai_scores への書き込み）
  - regime_detector.score_regime: ma200 とマクロニュースの LLM スコアを合成して market_regime を決定
- Research（kabusys.research）
  - ファクター計算（momentum / volatility / value）や将来リターン・IC 計算・統計要約
  - DuckDB を用いた高速集計処理
- Portfolio（kabusys.portfolio）
  - 候補選定、等比率／スコア重み計算、セクター上限適用、ポジションサイズ算出（lots/aggregate cap 考慮）
- Tools
  - paper_verification_report: Paper Trading DB から期間指定で検証レポート作成
- 設定管理ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前に必須環境変数や config/*.yaml をチェック

前提 (推奨)
-----------
- Python >= 3.10
- 必要なパッケージ（例、pip インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に必要だが必須ではない）
- 環境変数は .env に保存する想定（config_setup.py で作成可能）

セットアップ手順
---------------
1. リポジトリをクローン／配置してプロジェクトルートへ移動
2. Python 仮想環境を用意して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（任意の方法で）
   - pip install duckdb psutil openai PyYAML
   - （運用環境に合わせて追加のパッケージをインストールしてください）
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成
5. 設定検証（必須環境変数や DB パス等をチェック）
   - python -m kabusys.validate_config
   - 問題があれば修正して再度検証

重要な環境変数（例）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用（監視は環境に関わらず本番 sqlite を参照）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
- LOG_LEVEL（例: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に既存 kill.flag を自動クリアするか、0/1）

使い方（起動コマンド）
---------------------

- 環境設定ウィザード（.env の初期作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading として起動すると paper_trading 用 Mock ブローカーを用い、data/paper_trading.db に記録
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を利用

- 監視モード起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は MonitoringDB（SQLite）に状態を記録し、必要時に kill.flag を書き込む等のアクションを行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定することも可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先）

- AI / スコアリング（プログラムから呼び出す）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)（モジュール関数を直接呼べます）

停止 / Kill Switch
------------------
- 外部から ExecutionEngine を停止するには data/kill.flag を書き込む（KillSwitch を経由している場合）
- run_execution/run_monitoring は data/stop_requested.flag を検知して安全にループを抜けます
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に既存の kill.flag を自動で削除します（本番では注意）

データベースとログ
-----------------
- デフォルト DB:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- ログ:
  - logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30 日分保持）
  - 標準出力にもログ出力（stdout）

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定取得ユーティリティ
- config_setup.py           — 対話式 .env 作成ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — レジーム判定（MA + マクロニュース LLM）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py       — システム状態・データ鮮度チェック
  - trade_monitor.py        — （注文ログ監視）※詳細実装ファイルあり
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        — 通知送信（LINE 等）※実装依存
- execution/
  - execution_engine.py     — ExecutionEngine 本体（run_session 等）
  - broker_factory.py       — BrokerClient の生成
  - order_manager.py        — 発注管理
  - order_repository.py     — 発注履歴保存（SQLite 等）
  - reconciler.py           — ブローカーステータス同期
  - risk_manager.py         — 実行時リスクチェック
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 発注数量算出
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/volatility/value）
  - feature_exploration.py  — IC / 将来リターン / 統計要約
- utils/
  - logging_setup.py        — 共通ロギングセットアップ
  - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力ツール

注意点 / 運用上のヒント
-----------------------
- Monitoring の init_monitoring_db は冪等でスキーマを作成・簡易マイグレーションを行います。
- run_monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を使います。監視 DB を分離したい場合は環境変数で SQLITE_PATH を変更してください。
- Paper Trading は settings.is_paper を判定して paper_sqlite_path を使用します（本番 DB とは完全分離）。
- OpenAI を使用する機能は API キー（OPENAI_API_KEY）の設定が必須です。API 失敗時は多くの箇所でフェイルセーフ（スコア 0.0 やスキップ）を採用していますが、運用ではリトライや監視を必ず行ってください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。Kill Switch を自動クリアすると想定外の発注が行われる危険があります。
- ローカルテストは KABUSYS_ENV=development で行い、paper_trading モードで発注挙動を確認してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"

おわりに
--------
この README はコードベースの主要機能と運用フローの概要を示しています。細かな設定や実装の詳細はソースコード内の docstring / コメントを参照してください。運用前には必ず python -m kabusys.validate_config で設定検証を行って下さい。