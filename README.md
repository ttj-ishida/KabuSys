README
======

概要
----
KabuSys は日本株の自動売買・リサーチ用ライブラリ兼実行フレームワークです。  
主な機能は売買シグナル生成・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・研究用ファクター計算・AI（ニュース NLP / レジーム判定）です。  
このリポジトリはローカル開発・ペーパートレード・本番運用を想定した設計になっています。

主な特徴
--------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を別プロセスで運用可能
- Paper Trading モードでは MockBroker を利用し、本番 DB と分離された data/paper_trading.db を利用
- DuckDB を用いたリサーチ／ファクター計算（prices_daily, raw_financials 等を想定）
- ニュース記事を OpenAI（gpt-4o-mini）でスコアリングする AI モジュール（score_news）
- マーケットレジーム判定（regime_detector）— MA とマクロニュースを組み合わせたスコアリング
- 監視用 SQLite（monitoring.db）に各種ログ・ダッシュボード情報を永続化
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力
- .env ウィザード（config_setup）／設定検証 CLI（validate_config）を用意

セットアップ
-----------
1. リポジトリをクローンして作業ディレクトリに移動
   - package は src/ 配下にあるため、開発時は PYTHONPATH を適切に設定するか editable install を推奨

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - duckdb
   - psutil
   - openai  （AI 機能を使う場合）
   - PyYAML （config 検証で YAML 内容を検査したい場合）
   例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt はこのリポジトリに含まれていないため、上記パッケージを個別にインストールしてください）

4. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ格納ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（0/1、デフォルト: 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動的な .env 読み込みを無効化

使い方
------

1) .env を作成・編集
   - 対話ウィザード:
     python -m kabusys.config_setup

2) 設定チェック
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

3) ExecutionEngine を起動（発注エンジン）
   - 本番または paper_trading に応じて .env の KABUSYS_ENV が切り替わります
   - 起動:
     python -m kabusys.run_execution
   - ペーパートレード時は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に取引を記録します
   - 起動プロセスは data/execution.pid に PID を書き込みます
   - 停止方法:
     - 外部で data/stop_requested.flag を作成するとスレッド内で検知して停止します
     - kill_switch（監視側）がトリガーすると data/kill.flag を書き込み ExecutionEngine に停止命令を送ります
   - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START により kill.flag を自動削除するよう設定できます（本番では推奨しません）

4) Monitoring を起動（監視プロセス）
   - 監視はデフォルトで sqlite_path（monitoring DB）を使います（monitoring は KABUSYS_ENV にかかわらず本番 sqlite を参照）
   - 起動:
     python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL で polling 間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
   - モニターは SystemMonitor / TradeMonitor / RiskMonitor を実行し、アラートや kill.flag の作成を行います

5) Paper Trading 検証レポート生成
   - ツール:
     python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）

AI 関連
-------
- ニュース NLP（kabusys.ai.score_news）:
  - DuckDB の raw_news / news_symbols / ai_scores テーブルを参照／更新します
  - OPENAI_API_KEY が必須
  - バッチ処理、リトライ、レスポンス検証、スコアの ±1.0 クリップなどの保護機構あり

- レジーム判定（kabusys.ai.regime_detector.score_regime）:
  - ETF（1321）200 日移動平均乖離とマクロニュースセンチメントを合成して regime を算出
  - OPENAI_API_KEY が必須（マクロニュースがない場合は安全に 0.0 を使用）

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一的に行われます
- 出力:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト・30日保持）
- ログレベルは LOG_LEVEL または引数で制御可能

データベース / スキーマ
----------------------
- DuckDB: 分析・リサーチ用（デフォルト: data/kabusys.duckdb）
- SQLite:
  - 監視用: data/monitoring.db（monitoring_db.init_monitoring_db が必要テーブルを作成）
  - ペーパートレード用: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき Execution はこの DB を使用）
- monitoring_db が system_status, trade_logs, positions, risk_logs, dashboard 等のテーブルを作成・管理します

停止フラグ / キルスイッチ
------------------------
- data/stop_requested.flag:
  - run_execution/run_monitoring のループ中で存在が確認されると穏やかに終了します
- data/kill.flag:
  - KillSwitch が書き込みを行い ExecutionEngine 側で停止を要求するために用います
  - KillSwitch は冪等に動作し、既存ファイルがあれば上書きしません
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に自動的に clear します（本番では注意）

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 設定読み込み・Settings クラス（.env 自動ロード）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

modules / サブパッケージ
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI を用いたセンチメント）
  - regime_detector.py     — マーケットレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — （取引監視）※実装参照
  - risk_monitor.py        — ドローダウン・ポジション監視
  - kill_switch.py         — kill.flag の作成・操作
  - monitoring_engine.py   — 各 Monitor を束ねる
  - alert_manager.py       — （通知管理）※実装参照
- execution/
  - execution_engine.py    — ExecutionEngine（発注セッション管理）
  - broker_factory.py      — ブローカークライアント生成
  - order_manager.py       — 注文管理ロジック
  - order_repository.py    — 注文永続化層
  - reconciler.py          — 注文整合性確認
  - risk_manager.py        — 発注前リスクチェック
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・ラウンド処理
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / ベストプラクティス
------------------------------
- .env は決して Git にコミットしないでください
- 本番環境では KABUSYS_ENV=live を十分に確認してから使用してください。validate_config は本番設定に対する警告を出します
- OpenAI を利用する機能は API 使用量とレスポンスの妥当性に注意して運用してください（リトライや検証ロジックは組み込まれていますが、完全ではありません）
- monitoring は本番の監視 DB を参照するため、誤った設定で本番 DB を壊さないように注意してください
- Paper Trading は本番 DB と独立するよう設計されていますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH）

よくあるコマンドまとめ
---------------------
- .env ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  python -m kabusys.run_execution

- Monitoring 起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

サポート / 拡張
----------------
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）は外部 ETL / データパイプラインで準備してください
- ブローカー実装（kabu ステーション等）の詳細は execution/broker_factory.py を参照して拡張可能
- 監視アラート送信（LINE 等）は alert_manager で集中管理しており、ここにプラグイン追加できます

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照しています（現行: 0.1.0）

以上。開発・運用で必要な情報がほかにもあれば README に追記しますので、欲しい項目を教えてください。