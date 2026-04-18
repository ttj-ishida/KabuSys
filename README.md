README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。  
戦略のためのファクター計算、ポートフォリオ構築、ポジションサイジング、発注エンジン、監視・アラート、Paper Trading 検証、ならびにニュース系の NLP を用いた補助機能を含むモジュール群を提供します。

主な特徴
--------
- ポートフォリオ構築: シグナル選定、等配分 / スコア加重、リスク調整（セクターキャップ、レジーム乗数）
- ポジションサイジング: リスクベース / 等分配 / スコアベースの株数計算、単元株丸め、aggregate cap のスケール調整
- ファクター計算・リサーチ: モメンタム、ボラティリティ、バリュー等のファクター、将来リターン・IC 計算、統計サマリー
- 実行エンジン: BrokerClient の抽象化（実売買 / モックを切替）、注文管理、リスク管理、リコンサイル
- 監視 (Monitoring): システム状態、データ鮮度、注文滞留・約定異常、ドローダウン監視、Kill Switch による停止制御
- ニュース NLP / レジーム検知: OpenAI を利用した銘柄別ニュースセンチメントおよびマクロセンチメントからの市場レジーム判定
- ユーティリティ: .env ウィザード、設定検証、ログ設定、プロセス優先度設定
- Paper Trading 向けの検証レポート生成ツール

準備・セットアップ
------------------
1. リポジトリをクローンして作業ディレクトリに移動します（パッケージ構成は src/kabusys 以下）。
2. Python の依存パッケージをインストールしてください（プロジェクトが依存するライブラリ例: duckdb, psutil, openai, PyYAML 等）。例:
   - pip install -r requirements.txt
   （requirements.txt がない場合は必要ライブラリを個別にインストールしてください）
3. 初期設定 (.env) を作成します:
   - 対話ウィザードで作成:
     python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env ファイルを作成して必要な環境変数を設定します。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、実取引を行わず MockBrokerClient を使用し、Paper 用 SQLite (PAPER_TRADING_SQLITE_PATH) に記録します
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API を使う機能で必要（news_nlp, regime_detector）
- PAPER_FILL_MODE: paper_trading の約定挙動 (instant|partial|never|reject)（デフォルト: instant）
- その他: LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START 等

設定検証
--------
作成した .env や config/*.yaml を起動前に検証できます:
- 設定検証 CLI:
  python -m kabusys.validate_config
- 警告をエラー扱いにする:
  python -m kabusys.validate_config --strict

基本的な使い方
------------

1. 実行エンジン (ExecutionEngine) の起動
   - 目的: 発注・注文管理・リスク管理を行うエンジンを開始します。
   - 実行:
     python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
     - プロセス優先度を "high" に設定（可能な場合）。
     - data/stop_requested.flag の存在で起動を抑止 / 実行中に検知で停止します。
     - PID ファイルを書き出します（デフォルト: data/execution.pid）。

2. 監視ループ (SystemMonitor) の起動
   - 目的: システム状態、データ鮮度、監視ログの定期記録・アラート発火、Kill Switch 評価などを行います。
   - 実行:
     python -m kabusys.run_monitoring
   - オプション / 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリングの間隔（秒、デフォルト 60）。1 未満や不正な値は無視されデフォルトにフォールバックします。
   - 挙動:
     - 監視は monitoring.db（Settings.sqlite_path）を使用して永続化。Monitoring は環境にかかわらず本番 sqlite_path を参照する設計になっています。
     - data/stop_requested.flag によりループを安全に停止できます。

3. Paper Trading 検証レポート
   - 目的: paper_trading の SQLite DB から稼働率・注文成功率・レイテンシなどを集計して PASS/FAIL 判定するレポートを出力します。
   - 実行:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

4. ニュース NLP / レジーム判定（AI 機能）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。
   - ニューススコアリング:
     - kabusys.ai.score_news を呼ぶことで raw_news から銘柄別スコアを ai_scores テーブルへ書き込みます。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼ぶと市場レジームを market_regime テーブルに書き込みます。
   - どちらも API エラー時は安全にフォールバック（例: macro_sentiment=0.0）するロジックがあります。

運用上の仕組み（重要）
--------------------
- Kill Switch:
  - リスク条件（ドローダウン、ポジション上限など）を監視し、条件を満たした場合に data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は kill.flag を見て安全停止する設計です。
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します（運用上の手動停止用）。
- ログ:
  - ログは stdout（StreamHandler）と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 LOG_DIR で上書き可能。30 日保持。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成だけでなく既存 DB への列追加（簡易マイグレーション）を含みます。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py              — 環境変数 / Settings 管理（自動 .env ロード機能含む）
- config_setup.py        — .env 対話ウィザード
- validate_config.py     — 起動前の設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- ai/
  - news_nlp.py           — ニュースセンチメントの LLM 連携処理
  - regime_detector.py    — 市場レジーム判定（ma200 + マクロセンチメント）
- portfolio/
  - portfolio_builder.py  — 候補選定・重み算出
  - position_sizing.py    — 発注株数計算・スケールダウンロジック
  - risk_adjustment.py    — セクターキャップ / レジーム乗数
  - __init__.py
- research/
  - factor_research.py    — Momentum / Volatility / Value 計算（DuckDB ベース）
  - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - __init__.py
- monitoring/
  - monitoring_db.py      — SQLite 監視ログ永続化層
  - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py      — （注文/約定の監視、該当ファイル参照）
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag 書き込みロジック
  - monitoring_engine.py  — 各 Monitor を束ねるエンジン
  - alert_manager.py      — アラート送信（LINE 等、実装依存）
- execution/
  - execution_engine.py   — ExecutionEngine 本体（run_session 等）
  - broker_factory.py     — BrokerClient の生成（本番 / Mock 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- monitoring/             — 上記監視関連
- utils/
  - logging_setup.py      — 共通ロギング設定
  - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py
- research/               — 上記リサーチ関連
- portfolio/              — 上記ポートフォリオ関連

運用上のヒント
--------------
- 本番運用（KABUSYS_ENV=live）時は特に LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を確認してください。validate_config は live の場合に注意喚起を行います。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番では 0 を推奨します（誤って自動クリアすると危険）。
- run_execution / run_monitoring を systemd や supervisor、コンテナでラップしてデプロイすると運用が楽になります。ログは logs/ 以下に自動で蓄積されます。
- DuckDB は分析用途のローカル高速 SQL エンジンとして使います。prices_daily や raw_financials などのテーブルを配置してファクター計算等を行います。

よく使うコマンドまとめ
--------------------
- .env ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- 実行エンジン起動:
  python -m kabusys.run_execution
- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス情報や開発への貢献方法を記載してください。）

補足
----
README に記載した内容はコードベースの主要機能とエントリポイントに基づく概要です。詳細な設計・API（Engine のパラメータや BrokerClient 実装、alert_manager の具体的実装など）は該当モジュールの docstring やコードを参照してください。README の補足情報やサンプル設定ファイル（.env.example、config/*.yaml のテンプレート）があれば運用開始がさらに簡単になります。