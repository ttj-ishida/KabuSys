KabuSys — 日本株自動売買システム
================================

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買／研究プラットフォームの一部です。  
ここに含まれるコード群は、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究（factor 計算）、AI（ニュース NLP / レジーム判定）などのコンポーネントを提供します。

主な特徴
--------
- ExecutionEngine：実際の発注（またはペーパートレード）を実行するエンジン（run_execution.py）。
- Monitoring：システム状態・取引ログ・リスク監視のポーリング処理（run_monitoring.py、monitoring_engine）。
- Kill Switch：リスク条件（ドローダウン、ポジション上限）で Execution を停止する機能（kill.flag に書き込み）。
- Portfolio construction：銘柄選定・重み付け・ポジションサイズ計算（portfolio パッケージ）。
- Research：DuckDB 上で動くファクター計算・特徴量探索（research パッケージ）。
- AI モジュール：ニュースのセンチメントスコア付与（OpenAI）や市場レジーム判定（ai パッケージ）。
- ツール：ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）。
- 環境設定ウィザードと設定検証 CLI（config_setup.py / validate_config.py）。
- 統一されたログ設定（utils/logging_setup.py）とプロセス優先度ユーティリティ（utils/process_priority.py）。

必要条件（主な依存）
------------------
（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）
- Python 3.9 以上（型注釈によりそれ以前は未検証）
- duckdb
- openai (AI 機能利用時)
- psutil
- PyYAML（config/*.yaml の検証を行う場合のみ）

セットアップ手順
----------------
1. リポジトリをクローン、ワークディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール:
   - pip install duckdb openai psutil PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     - ウィザードは .env を生成します。（.env を絶対に Git にコミットしないでください）
   - 手動で設定する場合は .env.example を参照して必要な変数を設定してください。

5. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

主な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）：J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）：kabuステーション API パスワード
- KABUSYS_ENV（任意、デフォルト: development）：実行環境
  - 有効値: development / paper_trading / live
- DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）：DuckDB ファイルパス
- SQLITE_PATH（任意、デフォルト: data/monitoring.db）：監視用 SQLite ファイル（Monitoring が使用）
- PAPER_TRADING_SQLITE_PATH（任意、paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY：OpenAI API を利用する AI 機能で必要
- LOG_LEVEL（任意、デフォルト: INFO）：ログレベル
- LOG_DIR（任意、デフォルト: logs/）：ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL（任意、監視用、デフォルト: 60）：監視ポーリング間隔（秒）
- PAPER_FILL_MODE（任意、paper_trading 用、デフォルト: "instant"）
  - 有効値: "instant" | "partial" | "never" | "reject"

重要な挙動メモ
----------------
- run_monitoring.py は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックします。
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番パス）を使用して監視情報を記録します。
- run_execution.py は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ書き込み、本番 DB と分離します。
- 起動時にプロセス優先度を "high" に設定しようとします（utils/process_priority.py）。権限不足等で失敗した場合は警告を出して継続します。
- 停止フラグ / Kill Switch:
  - 監視ループはプロジェクトの data/stop_requested.flag の存在をチェックして終了します（run_* スクリプト）。
  - KillSwitch は data/kill.flag に書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時に kill.flag の自動クリア挙動を設定可能（KILL_FLAG_CLEAR_ON_START）。

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン（注文実行）起動:
  - python -m kabusys.run_execution
  - ペーパートレードの場合: KABUSYS_ENV=paper_trading を .env に設定して起動

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を必要に応じて設定（秒）

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（例）:
  - ニューススコア付与（programmatic 呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
  - コンソール出力（stdout）と日次ローテーションされたファイル出力（logs/<app_name>.log）を行います。
  - LOG_LEVEL / LOG_DIR 環境変数で調整可能。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 設定読み込み・Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前の設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py          — ログ共通設定
- process_priority.py       — プロセス優先度 / CPU affinity

src/kabusys/monitoring/
- monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py         — システム状態・データ鮮度監視
- risk_monitor.py           — ドローダウン・ポジション上限監視
- trade_monitor.py          — （取引関連監視）※コード内に参照あり
- kill_switch.py            — kill.flag 管理
- monitoring_engine.py      — 各 Monitor を束ねるエンジン
- alert_manager.py          — （アラート送信管理）※コード内に参照あり

src/kabusys/execution/
- execution_engine.py       — 発注エンジン本体（参照あり）
- order_manager.py, ...     — 注文管理、リポジトリ、リスク管理等（参照あり）
- broker_factory.py         — ブローカークライアント生成（paper/live の分岐）

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py        — momentum/value/volatility 等の計算（DuckDB）
- feature_exploration.py    — 将来リターン、IC、統計サマリー 等
- __init__.py

src/kabusys/ai/
- news_nlp.py               — ニュース NLP スコアリング（OpenAI）
- regime_detector.py        — マーケットレジーム判定（OpenAI）

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

データ / ログ / フラグ
---------------------
- data/monitoring.db         — デフォルトの監視用 SQLite（SQLITE_PATH で変更可）
- data/paper_trading.db      — ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        — デフォルト DuckDB（DUCKDB_PATH）
- data/kill.flag             — Kill Switch 発動で Execution を停止させるためのファイル
- data/stop_requested.flag   — run_* スクリプトが監視している停止フラグ（存在でプロセス終了）
- logs/                      — デフォルトのログ出力先（LOG_DIR で変更可）

補足 / 運用上の注意
-------------------
- .env にシークレット（API キーやパスワード）を保存する場合、誤って Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知設定を確実に確認してください（validate_config にチェックあり）。
- OpenAI を利用するモジュールは API のレート制限やエラーに対してリトライ処理を行いますが、運用時はコスト・レートを考慮してください。
- DuckDB / SQLite への書き込み権限・ディスク容量には注意してください。
- process priority / CPU affinity の設定は OS 権限やプラットフォーム差により失敗する場合があります（ログで警告）。

貢献・拡張
---------
- 新しい戦略やブローカー実装を追加する際は execution パッケージの拡張を検討してください。
- research モジュールは DuckDB ベースでファクター計算を行うため、データテーブル（prices_daily / raw_financials）を整備することで即座に活用できます。
- monitor / kill switch のルールは monitoring/*.py を拡張して柔軟に変更できます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（現状 "0.1.0"）。  
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

最後に
------
この README はコードベースの現状（主要ファイル群）に基づいて作成しています。実際の導入・運用前に python -m kabusys.validate_config やログ／DB の動作を確認してください。問題や改善案があれば issue を作成してください。