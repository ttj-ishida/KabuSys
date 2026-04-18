KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。
戦略・ポートフォリオ構築、発注実行、監視、研究用ユーティリティ、LLMベースのニュース評価などを含みます。

主な特徴
--------
- ExecutionEngine（発注実行）と Monitoring（監視）を分離して起動・運用可能
- Paper Trading（ペーパートレード）モードをサポート（本番DBと完全分離）
- DuckDB を使った研究向けファクター計算（momentum / value / volatility など）
- OpenAI を利用したニュースセンチメント評価（AI モジュール）
- 監視用 SQLite（monitoring.db）で稼働ログ・注文ログ・リスクログを永続化
- 簡易的な CLI ツール群：
  - 環境設定ウィザード（.env 作成）: kabusys.config_setup
  - 設定検証: kabusys.validate_config
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

機能一覧
--------
- 環境設定管理（.env 読み込み/対話式生成）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定（high）・PID ファイル管理・停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムリソース、データ鮮度、発注ログ、リスク指標を定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視用 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを自動作成・マイグレーション
- Kill Switch（kill_switch.py）
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送出
- RiskMonitor（ドローダウン・ポジション上限監視）・TradeMonitor（滞留注文等検出）・AlertManager（通知発行）
- Portfolio モジュール（候補選定・重み付け・株数算出・セクター上限・レジーム乗数）
- Research モジュール（ファクター計算・将来リターン・IC 計算・統計サマリ）
- AI モジュール
  - news_nlp: OpenAI を使ってニュースを銘柄ごとにセンチメント評価し ai_scores に格納
  - regime_detector: ETF（1321）MA200 乖離 + マクロ記事センチメントで日次レジーム判定
- ユーティリティ
  - logging_setup: 統一されたログ設定（stdout + 日次ローテーション）
  - process_priority: プラットフォーム差分を吸収してプロセス優先度 / CPU affinity を設定

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作成してアクティベートしてください。

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使用してください（本リポジトリでは省略）。
   - 必要な主なライブラリ:
     - duckdb, psutil, openai, sqlite3（標準ライブラリ）, PyYAML（設定検証で任意）
   - 例:
     pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話式ウィザードで作成可能:
     python -m kabusys.config_setup
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 運用に応じて KABUSYS_ENV を設定:
     - development / paper_trading / live
   - デフォルトの DB / ログ パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

4. 設定検証（推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. ディレクトリ作成（自動で作られることもありますが明示的に作ると安心）
   mkdir -p data logs

使い方（起動 / ツール）
----------------------

- 実行エンジンを起動（本番/ペーパーどちらも同じスクリプト。KABUSYS_ENV で挙動変化）:
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了。
  - 実行中に stop フラグ（data/stop_requested.flag）を作成すると安全に終了を試みます。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- 監視ループを起動:
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を使用します。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db で DB パスを指定できます（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）。

- AI モジュール（プログラムから呼び出し）
  - ニュース評価（ai_scores に書き込む）:
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) の接続オブジェクト
    score_news(duckdb_conn, target_date, api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")

  ※ OpenAI API を使う場合は OPENAI_API_KEY 環境変数を設定するか、関数に api_key を渡してください。

- ログ設定
  - 各起動スクリプト内で kabusys.utils.logging_setup.setup_logging(app_name="...") を呼び出しているため、デフォルトで:
    - stdout にログ出力
    - logs/<app_name>.log に日次ローテーションでファイル出力（logs ディレクトリを作成できない場合はコンソールのみ）
  - LOG_LEVEL 環境変数でログレベルを調整可能。

運用上の注意
------------
- KABUSYS_ENV の値:
  - development: 開発用（発注なし）
  - paper_trading: ペーパートレード（本番 DB と分離）
  - live: 本番（実際に発注が行われます）
- Kill Switch:
  - KillSwitch はリスク条件（大きなドローダウン等）で data/kill.flag を書き込みます。ExecutionEngine は起動時にこれを確認し、flag があれば起動しません。
  - 設定で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（カラム追加等）を行います。
- 環境変数自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）から .env, .env.local を自動読み込みします。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。権限不足で設定できない場合は警告ログになります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB; デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|...)
- MONITOR_POLL_INTERVAL (監視ポーリング秒; デフォルト 60)
- PID_FILE_PATH, KILL_FLAG_PATH
- KILL_FLAG_CLEAR_ON_START (0|1)

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定読み込み・ Settings クラス
- config_setup.py           — .env 対話ウィザード（python -m kabusys.config_setup）
- validate_config.py        — 設定検証 CLI（python -m kabusys.validate_config）
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

ai/
- news_nlp.py               — ニュースを LLM でスコアリングして ai_scores に書き込み
- regime_detector.py        — レジーム判定（MA200 + マクロ LLN）

monitoring/
- monitoring_db.py          — SQLite 永続化層（テーブル作成・CRUD）
- system_monitor.py         — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- risk_monitor.py           — ドローダウン・ポジション上限監視
- kill_switch.py            — kill.flag 操作
- monitoring_engine.py      — 各 Monitor を束ねるループ
- (trade_monitor.py 等は同フォルダに存在する想定)

portfolio/
- portfolio_builder.py      — 候補選定・重み計算
- position_sizing.py        — 株数決定・スケーリング・lot 単元丸め
- risk_adjustment.py        — セクター上限・レジーム乗数

research/
- factor_research.py        — momentum/value/volatility 等の計算（DuckDB）
- feature_exploration.py    — 将来リターン・IC・統計サマリ

utils/
- logging_setup.py          — 統一ログ設定
- process_priority.py       — プロセス優先度 / CPU affinity 設定

tools/
- paper_verification_report.py — Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

その他
------
- データ格納ディレクトリ: data/
  - stop_requested.flag      — 手動停止用フラグ（run_execution/run_monitoring が参照）
  - kill.flag                — Kill Switch が書き込む停止フラグ
  - execution.pid            — 実行エンジンの PID（起動時に記録）
  - monitoring.db / paper_trading.db / kabusys.duckdb など

貢献 / 拡張のヒント
-------------------
- Research 用クエリは DuckDB を利用しているため、テーブルスキーマ（prices_daily / raw_financials / raw_news 等）に合わせて拡張してください。
- AI モジュールは API 呼び出し部分を抽象化しているので、テスト時は _call_openai_api をモックしてください（実装内にその注記あり）。
- position_sizing 等の純粋関数群はユニットテストが書きやすい設計になっています。境界条件や lot 単元処理のテストを推奨します。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

補足
----
この README はリポジトリ内の主要なスクリプト・モジュールから抜粋して要約しています。実装の詳細や追加の CLI、設定ファイルはプロジェクトルートの README や config ディレクトリを参照してください。必要であれば、各モジュールの使用例や起動シーケンスの詳細ドキュメントも追加できます。