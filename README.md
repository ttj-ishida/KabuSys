README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ用ライブラリ兼実行フレームワークです。本コードベースは以下の主要機能を提供します。

- 発注エンジン（ExecutionEngine）と発注管理（OrderManager / RiskManager / Reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ポートフォリオ構築（候補選定 / 重み付け / ポジションサイズ計算 / セクター制限）
- リサーチ用ファクター計算と特徴量解析（DuckDB ベース）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）および市場レジーム判定
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）
- 開発支援ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート）

主な特徴
--------
- 環境変数 / .env を用いた設定管理（自動ロード機能あり）
- paper_trading モードでは本番 DB と分離された専用 SQLite（data/paper_trading.db）を使用
- DuckDB をデータ分析用に組み込み、prices_daily / raw_financials 等のテーブルを前提にファクター計算を行う
- 監視は SQLite に永続化（system_status / trade_logs / risk_logs / dashboard / positions）
- OpenAI（gpt-4o-mini など）を使ったニュース NLP とレジーム判定（API キー必須）
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力

前提条件 / 必要パッケージ
-----------------------
以下は代表的な依存パッケージです（実行環境に応じて pip install してください）。

- Python 3.9+
- duckdb
- psutil
- openai (news_nlp / regime_detector を使う場合)
- PyYAML（config/*.yaml のパース検証を行う validate_config で任意）

例:
    pip install duckdb psutil openai PyYAML

設定（.env）
-----------
プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
対話式ウィザードで .env を作成するには:

    python -m kabusys.config_setup

主な環境変数（代表）:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabusapi のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視（monitoring）SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定の検証
---------
作成した設定や config/*.yaml の存在・妥当性を検証する CLI:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

使い方（起動スクリプト）
----------------------
本リポジトリには起動用スクリプトがあり、モジュールとして実行できます。

1) ExecutionEngine（発注エンジン）起動

    python -m kabusys.run_execution

- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。
- 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
- エンジンは data/execution.pid を PID ファイルとして使用します（Settings.pid_file_path で変更可能）。

2) Monitoring（監視）起動

    python -m kabusys.run_monitoring

- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して system_status 等を記録します。
- 停止はプロジェクトルート/data/stop_requested.flag を作成することで行います（ファイルの検出でループを抜けます）。
- 監視側で KillSwitch を評価すると data/kill.flag を書き込んで ExecutionEngine に停止を促す仕組みがあります。

3) Paper Trading 検証レポート出力

    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB パス指定
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定できます（デフォルト data/paper_trading.db）。
- 稼働率、注文成功率、レイテンシなどの指標を出力し PASS/FAIL 判定を行います。

API 的利用
-----------
ライブラリとして関数を直接呼び出すこともできます。例:

- ニューススコアリング（ai/news_nlp.py）:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_count = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

- レジーム判定（ai/regime_detector.py）:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")

注意: 上記は DuckDB 接続とテーブル（prices_daily, raw_news, ai_scores 等）が適切に用意されていることが前提です。

監視 DB スキーマ（概要）
----------------------
監視用 SQLite（init_monitoring_db で作成）には主に以下のテーブルがあります:

- system_status: CPU/メモリ/Disk などのポーリングログ
- trade_logs: 発注イベントログ（Created / Sent / Filled など）
- positions: 現在の保有ポジション
- risk_logs: リスク関連の警告・イベント
- dashboard: ダッシュボード集計（portfolio_value / cash / drawdown 等）

停止・Kill 機構
--------------
- 実行停止：プロジェクトルートに data/stop_requested.flag を置くと run_execution/run_monitoring は検出して停止します。
- Kill Switch：監視側が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。KillSwitch.clear() でクリアできます。Settings.kill_flag_clear_on_start が 1 の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

主なコマンドまとめ
-----------------
- .env 作成ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ExecutionEngine 起動
    python -m kabusys.run_execution

- Monitoring 起動
    python -m kabusys.run_monitoring

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

ディレクトリ構成
----------------
(リポジトリの src/kabusys を基準に抜粋)

- kabusys/
  - __init__.py
  - config.py                  # 環境変数/.env 読み込みと Settings クラス
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py              # ニュースの NLP スコアリング
    - regime_detector.py       # 市場レジーム判定
  - monitoring/
    - monitoring_db.py         # SQLite レイヤ
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         # （アラート送信管理：LINE など、実装がある想定）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                       # データファイル（data/kabusys.duckdb, data/monitoring.db 等）
  - logs/                       # デフォルトログ出力先
  - config/                     # YAML 設定テンプレート類（system_config.yaml 等）

補足 / 運用上の注意
------------------
- 本番 (KABUSYS_ENV=live) では必ず設定を慎重に確認してください（validate_config の警告を参照）。
- .env は機密情報（API キー等）を含むため Git 等にコミットしないでください。
- OpenAI を使う機能は API キーが必須であり、API コストとレイテンシ・利用条件に注意してください。
- プロセス優先度設定と CPU affinity は psutil の権限制約により実行環境で失敗することがあります（警告ログが出力されます）。
- DuckDB / SQLite に依存するので、DB ファイルのバックアップ / ローテーションを運用で検討してください。

貢献 / 拡張
------------
- config/*.yaml の生成スクリプト（scripts/generate_config.py）や実運用向けのデプロイ設定を追加可能です。
- broker クライアントの追加や order lifecycle のロギング拡張、アラート送信チャネルの追加（Slack 等）が想定されます。
- テストカバレッジ強化と CI ワークフローの追加を推奨します。

ライセンス
----------
ソースコードのヘッダや別途 LICENSE ファイルの記載に従ってください（本 README にはライセンス情報を含みません）。

以上。README に不足している情報や、特定コンポーネント（例: ExecutionEngine の詳細な起動パラメータや AI モジュールのカスタム利用例）について追記が必要であれば指示ください。