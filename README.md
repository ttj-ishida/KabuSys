KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python パッケージです。  
主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）による注文管理・リスク管理（paper_trading / live 切替対応）
- 監視サブシステム（Monitoring）によるシステム状態・注文状況・リスク監視と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）※ DuckDB を使用
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ユーティリティ群（設定ウィザード、設定検証、ログ設定、プロセス優先度制御）
- ペーパートレード検証レポート生成ツール

特徴
----
- 設定は .env（環境変数）で管理。config_setup.py による対話式ウィザードあり
- production / paper_trading / development を環境切替で分離
- DuckDB（分析用）と SQLite（監視／発注ログ）を併用
- OpenAI を使ったニュース NLP / レジーム判定（オプション）
- ログは stdout と日次ローテートファイルに出力（logs/*.log）

動作要件（推奨）
----------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config ファイル検証を行う場合）
- SQLite は標準ライブラリで利用可能

インストール例（仮）
- 任意の仮想環境を作成し、以下をインストールしてください（requirements.txt が無い場合は手動で）:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリのルートに移動
2. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや kabu API パスワード等を入力してください。
   - 生成された .env は絶対に Git にコミットしないでください。
3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) します。
4. 必要に応じて DuckDB / SQLite のディレクトリを作成（デフォルトは data/）
   - データベースパスは .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH で調整できます。

主要な環境変数（代表）
--------------------
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 環境で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照、デフォルト 60）
- KILL_FLAG_... / PID_FILE_PATH 等（Kill Switch / PID 管理に使用）

使い方（主要エントリポイント）
----------------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB に記録します（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします（同ファイルで停止シグナルを受ける運用）。

- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒）。デフォルト 60 秒。
  - 監視は Settings に従って sqlite_path（監視 DB）と duckdb_path を使用します。
  - データ停止は data/stop_requested.flag によって検知されます。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ライブラリ／モジュールの利用例
----------------------------
- ニュース NLP（AI）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=...) — DuckDB 接続と日付を渡して ai_scores に書き込む
- レジーム判定（AI）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=...) — market_regime テーブルに結果を保存
- ファクター計算／リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - 関数は DuckDB 接続と target_date を受け取り、結果リストを返します
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視・停止フラグの運用
--------------------
- data/stop_requested.flag
  - run_monitoring と run_execution が起動ループで参照。存在すると監視・実行を終了します（オフライン停止）。
- data/kill.flag
  - KillSwitch が書き込むフラグ。大きなリスク事象（ドローダウン超過など）で ExecutionEngine に停止シグナルを与えます。
  - Settings.kill_flag_clear_on_start=1 で起動時に自動クリアする設定にできますが、本番では 0 を推奨します。

ログ
---
- setup_logging を各起動スクリプトで呼び出しているため、ログは統一フォーマットで出力されます。
- デフォルトログディレクトリ: logs/
- stdout と日次ローテーションファイル（logs/<app_name>.log）に出力されます。

開発・デバッグのヒント
-------------------
- .env の自動ロードはデフォルトで有効。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は .env 設定、config/*.yaml（存在すれば）の基本チェックを行います。PyYAML が無ければ YAML 内容検証はスキップされます。
- OpenAI 関連機能は API のレート制限や一時エラーを考慮したリトライ実装が含まれています。

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式生成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — レジーム判定（OpenAI + MA200）
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・利用資金スケーリング
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - (trade_monitor.py 等 他モジュール)
  - execution/
    - （ExecutionEngine / OrderManager / BrokerFactory 等、起動エンジン実装）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

よくある質問
--------------
- Q: paper_trading と live の違いは？
  - A: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（デフォルト）に記録します。本番の注文 API にはアクセスしません。live は実際のブローカー API を使用する想定です。
- Q: 監視ループの間隔を変更したい
  - A: MONITOR_POLL_INTERVAL 環境変数（秒）で上書きできます。0 以下や無効な値は無視されデフォルト 60 秒にフォールバックします。
- Q: OpenAI キーの設定場所は？
  - A: 環境変数 OPENAI_API_KEY（または関数呼び出し時の api_key 引数）。未設定時は AI 機能は動作しません（明確に例外を投げる箇所あり）。

ライセンス / 注意
----------------
- このリポジトリはサンプル／参考実装を想定しています。実際の資金を運用する際は十分な検証と法令順守、注文レート制御・例外処理・監査機能の整備を行ってください。
- .env や API キーなどの機密情報は決して公開リポジトリにコミットしないでください。

その他
-----
README に記載して欲しい追加情報（例: 実行例、設定テンプレート、CI 手順など）があれば教えてください。必要に応じて README を拡張します。