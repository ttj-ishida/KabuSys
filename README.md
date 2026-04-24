README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたライブラリ群です。本リポジトリには発注エンジン（ExecutionEngine）、監視モジュール（MonitoringEngine / SystemMonitor / RiskMonitor 等）、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ機能、OpenAI を用いたニュース NLP/レジーム検出、ペーパートレード検証用ツールなどが含まれます。

設計方針のポイント
- 本番／ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
- DB は DuckDB（分析用）と SQLite（監視・履歴用）を併用
- モジュールは可能な限り副作用を避けた純粋関数群と、DB 操作などの永続化レイヤに分離
- OpenAI 絡みの処理はフェイルセーフ設計（API 失敗時は安全側で継続）

主な機能
----------
- ExecutionEngine（発注エンジン）
  - 本番・ペーパーの切替（paper_trading では MockBrokerClient を使用し paper_trading.db に記録）
  - リスク管理（RiskManager）、オーダー管理、Reconciler などを統合して運用する
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・Execution プロセス生存監視
  - TradeMonitor: 注文の滞留・約定異常検知（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、kill switch 発動（data/kill.flag）
  - MonitoringEngine: 各 Monitor のポーリング統括、AlertManager 経由で通知
- Portfolio construction
  - 候補選定、等金額／スコア加重、セクター上限適用、ポジションサイジング（lot 単位丸め等）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI 統合）
  - news_nlp: raw_news を LLM でスコアリングし ai_scores に保存
  - regime_detector: ma200 とマクロニュースを組み合わせてレジーム判定
- ツール
  - config_setup: .env の対話式ウィザード生成
  - validate_config: .env + config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から検証レポート生成

前提条件
--------
- Python 3.10 以上（型アノテーションの union | 等を使用）
- 以下の外部パッケージ（用途に応じて）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config/*.yaml の中身を検証したい場合）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（kabuステーション API、OpenAI を使う場合）

インストール（例）
-----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

環境設定 (.env)
---------------
1. 対話式ウィザードで .env を作成・更新:
   - python -m kabusys.config_setup
   - デフォルトや既存値を確認しながら入力できます（シークレット項目はマスク表示）

2. よく使う環境変数（主要なものとデフォルト）
   - KABUSYS_ENV: 実行環境
     - development | paper_trading | live
     - default: development
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - LOG_LEVEL: INFO（DEBUG, INFO, ...）
   - OPENAI_API_KEY: OpenAI を利用する場合に必要
   - PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定振る舞い）

設定検証
--------
.env および config/*.yaml を起動前に検証する:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit 1）になります

データベース初期化
-----------------
monitoring 用の SQLite テーブルは起動スクリプト側で冪等に初期化されます（init_monitoring_db を実行）。
特に手動で操作する必要はありません。

実行方法
--------
各種サブコマンド／エントリポイントはモジュールとして起動できます。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading.db を使い、MockBrokerClient により発注をシミュレーション
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
    - 実行中は data/execution.pid ファイルを使用してプロセス管理
    - 停止は data/stop_requested.flag を作成することで行えます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番用の sqlite_path を使用して監視ログを書き込みます
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示的に指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能（OpenAI）
----------------
- news_nlp.score_news や regime_detector.score_regime を利用する場合は OPENAI_API_KEY を設定してください。
- API 呼び出しはフェイルセーフ設計で、失敗時は安全側のデフォルトを採ります（例: マクロセンチメント=0.0 等）。

Kill Switch / 停止フロー
-----------------------
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は実行エンジン停止のためのフラグです。監視側で条件成立時に書き込まれます。
- stop_requested.flag（data/stop_requested.flag）は運用者がループを停止させるためのフラグとして run_execution / run_monitoring が監視します。

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日分保持）。
- setup_logging を共通化しており、全スクリプトで同じログ設定を利用します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py        — SQLite 監視ログ永続化層
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py
  - regime_detector.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py

補足 / 運用上の注意
------------------
- 本リポジトリには実際の発注を行う処理が含まれるため、本番（KABUSYS_ENV=live）での稼働は十分なテスト・設定確認の上で行ってください。
- .env は決して Git にコミットしないでください（config_setup のヘッダーに注意喚起あり）。
- OpenAI API を利用する機能はコストやレイテンシに注意してください。呼出しはバッチ化・リトライ等の制御を行っていますが、運用ポリシーを設定してください。

寄与 / テスト
--------------
- まずは config_setup → validate_config を実行して設定を整えてください。
- 単体関数群（portfolio、research 等）は副作用が少ないためユニットテストを書きやすく設計されています。
- API 呼び出し部分はテストで差し替え可能（例: news_nlp の _call_openai_api をモック）。

ライセンス
---------
（必要に応じてここにライセンス情報を記載してください）

以上。README に改善したい項目（例: 追加の実行例、環境変数一覧の拡張、requirements.txt の作成など）があれば教えてください。