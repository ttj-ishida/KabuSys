KabuSys
======

日本株向け自動売買システムのコアライブラリ群（プロトタイプ / ミニマム実装）。  
このリポジトリには、発注実行エンジン、監視 / KillSwitch、ポートフォリオ構築ロジック、ファクター計算、LLM を使ったニュース NLP などの主要コンポーネントが含まれます。

主な特徴
------

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により本番 / ペーパートレードを切替可能（paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録）
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視を実装
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、監視ログを SQLite に永続化
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）
- 監視用 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - 必要に応じた簡易マイグレーション（列追加）を行う冪等初期化
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、重み計算（等額・スコア重み）、セクター制限、レジームに応じた乗数、株数決定（単元丸め、aggregate cap）
- リサーチ / ファクター計算（research/*）
  - モメンタム / ボラティリティ / バリュー等のファクターを DuckDB のデータを元に計算
  - 将来リターン、IC、統計サマリーなどの解析ユーティリティ
- AI モジュール（ai/*）
  - news_nlp: OpenAI（gpt-4o-mini）を使って銘柄ごとのニュースセンチメントを ai_scores テーブルに書き込む
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定を行う
  - API 呼び出しはリトライやフォールバックを備え、部分失敗でも致命的にならない設計
- ツール
  - config_setup: 対話式 .env 生成ウィザード（python -m kabusys.config_setup）
  - validate_config: .env / config/*.yaml の事前検証（python -m kabusys.validate_config）
  - paper_verification_report: ペーパートレード DB から検証レポートを出力

セットアップ手順
--------

前提
- Python 3.10 以上（typing の "X | Y" 構文を使用）
- 基本的な外部パッケージ（以下を参考）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を行う場合）

例（pip）
- 仮想環境を作成して有効にすることを推奨します:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール（requirements.txt はリポジトリにない場合、手動で）:
  - pip install duckdb psutil openai PyYAML

.env の初期作成
1. 対話式ウィザードで .env を作る:
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワードなどを入力
2. 作成後に設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱い

重要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - paper_trading: Mock ブローカーを使い data/paper_trading.db を利用
  - live: 実際に発注が行われる可能性があるため注意
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (デフォルト instant)
- LOG_LEVEL, LOG_DIR
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動で .env を読み込まない

使い方（起動例）
----------

1) 監視ループ（Monitoring）
- デフォルトで本番 sqlite_path（Settings.sqlite_path）を使用して監視を行います:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - プロジェクトルート data/stop_requested.flag を作成すると監視ループが安全終了します

2) 実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- paper_trading モードで起動する例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合、BrokerClientFactory が MockBrokerClient を選び、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
- 停止:
  - data/stop_requested.flag を作成するとエンジンに停止シグナルを送る（run_execution はフラグを検知して engine.stop() を呼ぶ）
- PID: 実行時に data/execution.pid を利用 / 管理（設定により変わる）

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging により統一的に設定されます。
- デフォルト出力:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト LOG_DIR=logs、30 日保持）
- LOG_LEVEL / LOG_DIR は環境変数で上書き可能

停止 / Kill Switch
-----------------
- KillSwitch は監視処理がリスク条件（例: ドローダウン超過、ポジション上限超過）を検出した場合に data/kill.flag を書き込み、ExecutionEngine の停止を誘発します。
- ExecutionEngine の停止はフラグファイル検出に依存するため、手動で停止する際は data/stop_requested.flag を作成するなどの仕組みが用意されています。

ディレクトリ構成（主要ファイル）
------------------------

概略:
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env の自動ロード）
  - config_setup.py              — 対話式 .env 生成ウィザード
  - validate_config.py           — 起動前設定検証ツール
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py           — 一元的ログ設定
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - execution/                   — 発注 / エンジン関連（実装のエントリ）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化・永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py
  - data/  (ランタイム生成)
    - monitoring.db (既定 SQLITE_PATH)
    - paper_trading.db (ペーパートレード DB)
    - kill.flag / stop_requested.flag / execution.pid など制御フラグ

注意事項 / ベストプラクティス
-----------------------------
- .env は機密情報を含むため絶対にコミットしないこと（config_setup.py のヘッダにも明記）。
- KABUSYS_ENV=live では本番発注を行う恐れがあるため、設定・LINE 通知設定等を慎重に確認してください。
- AI 機能（news_nlp / regime_detector）は OpenAI API キーを必要とし、API 呼び出しに伴うコストとレイテンシを考慮してください。
- DuckDB / SQLite のパスは環境変数で柔軟に変更できます。CI/CD や検証環境では別ファイルを指定して本番 DB と分離してください。
- 自動で .env を読み込む仕組みが働くため（プロジェクトルートに .env がある場合）、テストから isolation したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / 拡張のヒント
-------------------
- BrokerClientFactory を実装・拡張して任意のブローカーへ接続可能
- portfolio/* のロジックは純粋関数で設計されているためユニットテストが容易
- research/* は DuckDB を使った SQL ベースの計算。データモデルの拡張に合わせて SQL を拡張してください
- AI モジュールは応答フォーマットの堅牢性（JSON 抽出やバリデーション）を意識した実装になっています。モデルやプロンプトの調整はここを変更

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリルートに LICENSE（未記載の場合は要追加）

最後に
------
この README はコードベースの主要な機能と起動フローをまとめたものです。詳細な API、内部設計、各クラスの動作仕様は該当モジュールの docstring とソースを参照してください。必要なら運用手順（systemd / cron / コンテナ化）のサンプルも別途作成できます。