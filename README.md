KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / リサーチ / モニタリングを目的とした Python パッケージです。  
主要機能は以下を含みます:

- 注文実行エンジン（ExecutionEngine）: 本番 / ペーパートレード対応
- 監視 (Monitoring): システム状態、注文・リスクの定期チェックとアラート
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出
- リサーチ: ファクター計算・特徴量探索
- AI モジュール: ニュースを LLM（OpenAI）でスコアリング、レジーム判定
- 開発支援ツール: 環境設定ウィザード、設定検証、ペーパートレード検証レポート

機能一覧
--------
- config_setup: .env を対話式に作成/更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env / config/*.yaml の設定検証 CLI（python -m kabusys.validate_config）
- Execution 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
  - 停止は data/stop_requested.flag の作成または kill.flag による Kill Switch によって制御
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - 環境にかかわらず本番用 sqlite_path を使用して監視ログを記録
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
- tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（python -m kabusys.tools.paper_verification_report）
- portfolio: 銘柄選定（select_candidates）、重み計算（等金額/スコア）、ポジションサイズ計算（risk_based / equal / score）
- research: DuckDB を用いたファクター計算（momentum, volatility, value）および特徴量解析ユーティリティ
- ai: ニュース NLP（OpenAI 呼び出し）、市場レジーム判定（OpenAI を利用したマクロセンチメント合成）
- utils: ロギング設定、プロセス優先度 / CPU affinity のユーティリティ
- monitoring: SQLite ベースの永続化層、各種モニタ（System / Trade / Risk）、Kill Switch、アラート連携ロジック

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型アノテーションと pathlib 等を利用しています）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルを検証したい場合、任意）
  - これらはプロジェクトの requirements.txt があれば pip install -r requirements.txt を推奨

推奨手順:
1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があればそれを利用）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定
   - KABUSYS_ENV の値: development | paper_trading | live
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. データディレクトリの作成（必要に応じて）
   - デフォルト DB / ログパス: data/, logs/

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading 環境向け）
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方
------
基本的な実行例:

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作中に停止したい場合:
    - data/stop_requested.flag を作成すると監視ループ / エンジンは終了処理を行います（daemon スレッド停止など）
    - リスクベースの停止は KillSwitch が data/kill.flag を出力し ExecutionEngine 側で検知して停止します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で変更可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

- AI / レジーム判定 / ニューススコア
  - これらはモジュール関数として呼び出すことを想定（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）
  - OpenAI API キー (OPENAI_API_KEY) が必要

停止 / Kill Switch の運用:
- 手動停止:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループは停止または Engine.stop() を呼んで終了します
- 自動停止:
  - Monitoring の KillSwitch（RiskMonitor が DRAWDOWN や POSITION_LIMIT を検出）により data/kill.flag が書き込まれます
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

ログ
---
- デフォルトは logs/<app_name>.log（daily rotation、30世代保持）
- ログディレクトリは環境変数 LOG_DIR で変更可
- 起動スクリプトは内部で共通の setup_logging を呼び出します

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主なファイル・モジュールと概要です:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py — .env 対話ウィザード CLI
  - validate_config.py — 設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — （trade 関連の監視。コード内実装参照）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — data/kill.flag の管理
    - monitoring_engine.py — 複数モニタの統合ループ
    - alert_manager.py — （アラート送信を統括）

  - execution/
    - execution_engine.py — ExecutionEngine（注文実行の中核）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注・リスク管理・ブローカー抽象化）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 注文株数計算（lot 単位丸め、aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリなど

  - ai/
    - news_nlp.py — ニュースを LLM でスコア化し ai_scores に保存
    - regime_detector.py — ETF(MA200) とマクロセンチメントを組み合わせて日次レジーム判定

  - data/ （実行時・運用）
    - kill.flag            — Kill Switch のシグナルファイル
    - stop_requested.flag  — 手動停止要求ファイル
    - execution.pid        — PID ファイル（ExecutionEngine）
    - monitoring.db        — SQLite 監視 DB（デフォルト: data/monitoring.db）
    - paper_trading.db     — ペーパートレード用 DB（paper_trading 環境）

注記 / 運用上のポイント
-----------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）
- validate_config で本番起動前に必須値・ファイルパス等をチェックしてください
- KABUSYS_ENV=live の場合は特に設定（LINE 通知、KILL_FLAG_CLEAR_ON_START 等）に注意してください
- AI 機能を実行するには OpenAI のレート制限やエラーに備えた運用が必要です（コード内でリトライ・フォールバックを実装済）
- DuckDB / SQLite のパスは Settings で管理されます。monitoring は常に本番 sqlite_path を使用します（run_monitoring 側の設計）

開発者向けヒント
-----------------
- 自動で .env を読み込む仕組みは Settings モジュール内にあり、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト時など）
- ロギング設定は kabusys.utils.logging_setup.setup_logging を呼び出して統一してください
- OpenAI 呼び出し部分は内部でラップされており、単体テスト時は該当関数をモック（patch）できます（コード内に注記あり）

ライセンス / 貢献
----------------
- この README はコードベースに基づく概要説明です。実際の配布時は LICENSE と CONTRIBUTING をプロジェクトルートに置いてください。

必要に応じて README に追記します。特定の操作手順（例: systemd サービス化、Docker 化、CI 設定）を追加したい場合は使い方と要件を教えてください。