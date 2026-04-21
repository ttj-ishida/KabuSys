README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究（ファクター計算 / 特徴量解析）・AI（ニュース NLP / レジーム判定）などの機能を備え、ローカル開発からペーパートレード、本番運用まで想定しています。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番・ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカー実装の抽象化（MockBroker を利用した分離）
  - リスク管理（RiskManager / Reconciler 等）
- Monitoring（監視）
  - システム稼働監視（CPU/メモリ/ディスク・プロセス死活）
  - 取引・注文ログ監視、ドローダウン・ポジション数監視
  - Kill Switch（条件により data/kill.flag を作成して発注エンジンを停止）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア重み、リスクベース配分、セクターキャップ、レジーム乗数
- Research（研究用）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール
  - ニュースのセンチメント評価（OpenAI を用いたバッチスコアリング）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
- ツール群
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（paper_verification_report）

要件（例）
----------
- Python 3.9+（実際の要件はプロジェクトで調整）
- 推奨パッケージ（抜粋）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- ネットワーク／API
  - OpenAI API キー（AI 機能を使う場合）
  - kabuステーション API（実運用時）

主な環境変数
-------------
（デフォルト値や用途は kabusys/config.py を参照してください。主要なものを抜粋します）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能用)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に分離保存
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
- DUCKDB_PATH: data/kabusys.duckdb（分析用 DuckDB）
- SQLITE_PATH: data/monitoring.db（監視 DB。monitoring は環境に関わらず本番 sqlite_path を使用）
- LOG_LEVEL: DEBUG/INFO/…
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

※ .env 自動読み込み:
プロジェクトルートに .env / .env.local が存在すれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

セットアップ手順
----------------
1. リポジトリをチェックアウトして仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt / Poetry 等を用意してください。

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

5. データディレクトリ等の作成
   - デフォルトでは data/ と logs/ が使用されます。OS 権限やパスに注意してください。

起動方法（主なスクリプト）
-------------------------
- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は settings.sqlite_path（監視 DB）を使用（KABUSYS_ENV に依存せず本番 sqlite_path を参照）

- 発注エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に記録（本番 DB と完全分離）
  - 実行中は data/execution.pid が作成されます。停止は data/stop_requested.flag を作成することで行えます。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db
  - 生成されるレポートは稼働率、注文成功率、レイテンシ等を出力します（閾値はスクリプト内に定義）。

実行時のフラグファイル
---------------------
- 停止要求（run_execution/run_monitoring の監視用）
  - data/stop_requested.flag を作成するとループ内で検知して安全に終了します。
- Kill Switch（Execution 停止トリガ）
  - data/kill.flag を書き込むことで ExecutionEngine に停止を指示します（Monitoring の KillSwitch が条件を満たした場合に書き込む）。
  - KILL_FLAG_CLEAR_ON_START が 1 のときは起動時に自動クリアされる設定があるため注意（本番では 0 推奨）。

ログ設定
--------
- 共通の logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定
  - ログディレクトリは LOG_DIR 環境変数 > 引数 > デフォルト logs/ の順で決定

AI 機能
------
- ニュースのセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - OpenAI API（gpt-4o-mini）を用いてニュースをバッチ評価
  - OPENAI_API_KEY を環境変数または関数引数で指定
  - 失敗時は部分的にスキップするフェイルセーフ設計（例: API エラーはリトライ、最終的にはスキップ）
- レジーム判定（kabusys.ai.regime_detector.score_regime）
  - ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して 'bull'/'neutral'/'bear' を判定

開発・研究用モジュール
---------------------
- kabusys.research: ファクター計算（calc_momentum / calc_volatility / calc_value）、forward return、IC、統計サマリー
- kabusys.portfolio: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数

ディレクトリ構成（主要ファイル）
-------------------------------
以下は主要なモジュール/ファイルの概観です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py    — 各 Monitor を束ねる
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - trade_monitor.py        — 注文監視（監視ロジック）
    - alert_manager.py        — アラート送信（LINE 等）
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
    - (その他ユーティリティ)

注意事項 / 運用上のヒント
------------------------
- 監視 DB（SQLITE_PATH）は監視コンポーネントが利用します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するため、テスト時は注意して別 DB を指定してください。
- paper_trading モードは本番 DB と分離する目的で PAPER_TRADING_SQLITE_PATH を利用します。必ず分離された DB を用意してください。
- OpenAI を利用する機能は API キーとコストに注意してください。API 呼び出しはバッチ・リトライ制御がありますが、運用時はレートや料金管理を行ってください。
- ログディレクトリや data/ 配下のファイルは自動作成されますが、実行権限や容量管理（ログローテーション、DuckDB ファイルサイズ）を考慮してください。
- systemd 等のサービスマネージャから実行する場合、PID ファイル・stop flag の取り扱いを確認してください。

貢献 / 拡張ポイント
-------------------
- 銘柄ごとの lot_size をマスタ化して position_sizing を拡張
- リスクモデルやレジーム合成ロジックのチューニング
- 外部実マーケットデータプロバイダのプラグイン化
- テストと CI（特に OpenAI / ブローカー API をモックするユニットテスト）

参考
----
- 各モジュールの詳細な使い方や内部仕様はソースコードの docstring とコメントを参照してください。README は機能の概観と運用手引きに重点を置いています。

もしREADMEに追加してほしいコマンド例（systemd ユニット、docker-compose、サンプル .env）や、より詳細な各モジュールの API ドキュメントが必要であれば教えてください。