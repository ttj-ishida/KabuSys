README — KabuSys（日本株自動売買システム）
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
本リポジトリは注文実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ファクター／ポートフォリオ構築、研究用ユーティリティ、AI ベースのニュース NLP（OpenAI）などを含む構成になっています。  
設計方針の一部：ローカルで動作する SQLite / DuckDB を利用し、実運用（live）／ペーパートレード（paper_trading）／開発（development）を環境変数で切り替え可能。環境設定は .env に保存します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）で分離。
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）に対応。

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視。
  - Kill Switch（data/kill.flag）を発動して ExecutionEngine に停止シグナルを送る監視ロジック。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分／スコア配分、リスク制約（セクター上限、レジーム乗数）、株数決定（ロット丸め、利用可能現金に基づくスケーリング）を純粋関数で提供。

- リサーチ（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 上の prices_daily / raw_financials を使用）。
  - 将来リターン計算、IC 計算、統計サマリ機能。

- AI（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメント（銘柄ごとの ai_score）算出と ai_scores テーブルへの永続化（バッチ化・リトライ・レスポンス検証）。
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースに基づく市場レジーム判定（bull/neutral/bear）。

- ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を生成/更新。
  - validate_config.py: .env と config/*.yaml の存在・基本チェックを行う CLI。
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）。

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（ typing | match 等の機能と互換性を考慮）。
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（validate_config の YAML チェック用だが任意）
  - その他プロジェクトが追加で必要とするパッケージ（requirements.txt がある場合はそれを使用）

例（pip 使用）:
  pip install duckdb psutil openai pyyaml

初期設定
1. リポジトリをクローンしてプロジェクトルートに移動。
2. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup
   - J-Quants トークン、kabuAPI パスワード、KABUSYS_ENV（development/paper_trading/live）等を入力。
   - .env を絶対に Git にコミットしないでください。

3. 設定検証（任意）:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗と見なして exit(1)。

4. data ディレクトリや logs ディレクトリが自動で作られますが、権限の問題がある場合は手動で作成してください:
   mkdir -p data logs

5. 必要な DB 初期化は起動スクリプトが実行時に行います（monitoring テーブル等は init_monitoring_db による作成／マイグレーションを実施）。

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR など
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを抑制可能（テスト等で使用）

使い方（起動・各コマンド例）
--------------------------

- 実行エンジンを起動（通常）
  python -m kabusys.run_execution
  - 起動時にプロセス優先度を上げ、PID ファイル（data/execution.pid）を書きます。
  - data/stop_requested.flag が存在すると起動せず終了します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録して本番 DB と分離されます。

- 監視ループを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番用 sqlite_path を使用します（env にかかわらず）。

- 設定ウィザード（.env 作成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（CLI）
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH より優先。

- AI / 研究系関数はライブラリとして呼び出して利用
  例: Python REPL や別スクリプト内で
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を準備して score_news(conn, target_date, api_key=...)

停止・Kill Switch
- 監視モジュールは条件（ドローダウン超過、ポジション上限等）で data/kill.flag を書き込みます。ExecutionEngine は起動時 / ループ内でこのフラグを確認し、存在すれば停止します。
- 管理者が手動で停止したい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring は検出して終了します。

ログ
---
- デフォルトは logs/ ディレクトリに日次ローテーション付きログを出力（logs/<app_name>.log）。
- setup_logging() が各起動スクリプトで呼ばれます。LOG_DIR 環境変数で変更可能。

ディレクトリ構成（主要ファイル）
-----------------------------
（抜粋／要約。実際のファイル数は多いです）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理（自動 .env ロード、Settings クラス）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコア算出（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成 / 永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文滞留 / 約定異常検出（※実装ファイルあり）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - monitoring_engine.py  — 各 monitor を束ねる実行ループ
    - kill_switch.py        — kill.flag 制御
    - alert_manager.py      — LINE 等への通知（※実装ファイルあり）
  - execution/
    - execution_engine.py   — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py     — ブローカークライアント生成（Mock/実装切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py           — データ取得・更新ユーティリティ（get_last_price_date 等）
    - stats.py              — zscore_normalize 等（research に依存）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 運用メモ
------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live を使う場合は特に設定（LINE 通知、kill flag 設定、ログ）を慎重に確認してください。validate_config の live モード警告を参照してください。
- run_monitoring は監視用 DB（SQLITE_PATH）を常に参照します。監視と実行で DB を分離したい場合は PAPER_TRADING_SQLITE_PATH 等の設定を活用してください（paper_trading モード）。
- OpenAI API を使用する機能はネットワーク・料金が発生します。API キー管理と呼び出し頻度に注意してください（バッチ化・リトライロジックあり）。

ライセンス / 貢献
-----------------
- ライセンス情報がプロジェクトルートにある場合はそちらを参照してください。  
- バグ報告や機能リクエストは Issue を作成してください。

以上が主要な使用法・構成の概要です。必要であればセットアップ手順の詳細（例: systemd サービス定義、Docker 化、必要な Python バージョン・requirements.txt の作成例）や各モジュールの API ドキュメントを追記します。どの情報を優先して詳述しますか？