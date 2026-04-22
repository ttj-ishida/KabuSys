KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした軽量なパッケージです。  
主要な責務は以下の通りです。

- ExecutionEngine：発注・リスク管理・注文再接続の実行（実取引 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスク指標の定期監視とアラート（Kill Switch）
- Research：DuckDB 上の価格・財務データを使ったファクター計算・特徴量解析
- Portfolio：候補選定、ウェイト算出、ポジションサイズ計算、セクター制限
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ツール群：設定ウィザード、設定検証、ペーパートレード検証レポート等

主な設計方針：
- 本番データとペーパートレード用 DB を分離（ペーパートレードは data/paper_trading.db を使用）
- DuckDB を分析用 DB として利用、SQLite を監視・ログ保存に利用
- LLM 呼び出しはフェイルセーフ（API エラー時はスキップやフォールバック）で運用を想定

機能一覧
--------
- run_execution.py：ExecutionEngine を起動（KABUSYS_ENV によりペーパー/本番を切替）
  - PID ファイル管理（data/execution.pid）
  - stop フラグ（data/stop_requested.flag）による停止
  - RiskManager / OrderManager / Reconciler の組立て
- run_monitoring.py：SystemMonitor ポーリングループを起動
  - MONITOR_POLL_INTERVAL 環境変数で間隔を設定（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）でループ終了
- config_setup.py：対話式 .env 作成ウィザード
- validate_config.py：.env と config/*.yaml の起動前検証 CLI
- tools/paper_verification_report.py：ペーパートレードログからの検証レポート生成
- monitoring パッケージ：
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / monitoring_db
- research パッケージ：calc_momentum / calc_volatility / calc_value / calc_forward_returns / IC 等
- portfolio パッケージ：候補選定・配分・ポジションサイズ計算・セクターキャップ
- ai パッケージ：news_nlp（ニューススコアリング）、regime_detector（市場レジーム判定）
- utils：logging_setup（統一ログ）、process_priority（優先度設定） 等

セットアップ手順
----------------
前提：
- Python 3.9+（コードは型ヒント・モダン構文を使用）
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証時に必要）
これらは requirements.txt を用意している場合はそれに従ってください。無ければ pip でインストールしてください（例）:
pip install duckdb psutil openai PyYAML

1. リポジトリをクローンしてプロジェクトルートへ移動
2. .env の準備
   - 対話式で作る場合:
     python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して .env を作成
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルトが使える）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使う場合）
3. 設定検証（推奨）
   python -m kabusys.validate_config
   --strict をつけると警告もエラー扱いにできます
4. データディレクトリ作成（自動で作られるが明示的に作る場合）
   mkdir -p data logs

使い方（運用 / 開発）
--------------------

基本的な起動例
- ExecutionEngine を起動（現地の KABUSYS_ENV に依存してペーパー/本番を切替）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込む
  - PID ファイルは data/execution.pid に書かれる
  - data/stop_requested.flag が存在すると起動せず終了、起動中に検知すると停止処理を実行

- Monitoring を起動
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 監視ループの間隔は MONITOR_POLL_INTERVAL で秒指定（デフォルト 60）
  - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用（環境にかかわらず本番 sqlite_path を参照する実装上の注意）

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプションで --db を指定して別 DB を参照可能（デフォルト: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI / 研究系 API（プログラムから利用）
  例: DuckDB 接続を渡してファクター計算やニューススコアリングを呼ぶ
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    from kabusys.ai import score_news
  Note: AI 機能は OPENAI_API_KEY が必要

ログ・監視・停止手段
- ログ
  - setup_logging により stdout と logs/<app_name>.log（日次ローテート）へ出力
  - LOG_DIR 環境変数でログ保存先を上書き可能（デフォルト logs/）
- 停止フラグ
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全に停止する
- Kill Switch
  - RiskMonitor / KillSwitch により重大リスク（ドローダウン超過など）で data/kill.flag が作成され、ExecutionEngine 停止のトリガーとなる
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用監視 DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — AI 機能を利用する場合に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）

ディレクトリ構成
----------------
リポジトリの主要ファイル・ディレクトリ構成（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py         — .env 作成ウィザード CLI
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — レジーム判定（OpenAI + MA）
    - __init__.py
  - research/
    - factor_research.py    — momentum/value/volatility 等
    - feature_exploration.py— forward returns / IC / summary
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - execution/               — Execution エンジン関連（OrderManager 等、実装ファイル群）
  - data/                    — 実行時生成される DB / フラグ（data/*.db, data/*.flag）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

補足 / 運用上の注意
------------------
- DB の分離:
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離されます。これによりペーパートレードでの試験が本番データに影響しません。
- ログとハンドラ:
  - setup_logging は既存ハンドラをクリアして再設定します。複数回呼ぶときは二重出力にならないよう設計済みです。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を試みます（権限が足りないと警告でスキップされます）。
- LLM（OpenAI）:
  - news_nlp / regime_detector は OpenAI API を利用します。API キー管理には十分注意してください。API 呼び出しはリトライ・フォールバック実装が組み込まれていますが、コスト・レイテンシの期待値は運用側で管理してください。
- データ鮮度:
  - SystemMonitor 等は prices_daily の最新日を参照してデータ鮮度チェックを行います。DuckDB のテーブルが正しく更新されていることが前提です。

開発者向けメモ
----------------
- 研究用関数（research）やポートフォリオ構築ロジック（portfolio）は純粋関数として実装されており、ユニットテストがしやすい設計です。
- monitoring/monitoring_db.py はスキーマを冪等に初期化する init_monitoring_db() を提供します。既存 DB に対するマイグレーション（カラム追加）も含まれます。
- テストの容易さを考慮して、AI 呼び出し部分は _call_openai_api のパッチ差し替え（unittest.mock.patch）を想定しています。

ライセンス・貢献
----------------
- 本リポジトリにはライセンス表記は含まれていません。実運用・公開前にライセンスを追加してください。
- バグ修正や機能追加の際はユニットテストと設定検証の追加をお願いします。

最後に
------
まずは .env を作成し、python -m kabusys.validate_config で設定を確認してください。  
ペーパートレードでの挙動確認には python -m kabusys.run_execution を KABUSYS_ENV=paper_trading で起動し、tools/paper_verification_report.py で結果を評価する運用がスムーズです。必要があれば README を拡張して仕様や運用手順を追記します。