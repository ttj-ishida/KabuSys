README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤コンポーネント群です。  
主な機能は次の通りです。

- 発注エンジン（ExecutionEngine）とそれを監視する Monitoring（監視・アラート・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援機能（ニュースのセンチメント評価、レジーム判定）
- 開発支援ツール（.env 作成ウィザード、設定検証、ペーパートレード検証レポート）

主要な設計方針
- 環境設定は .env / 環境変数で管理。プロジェクトルート（.git / pyproject.toml）を基準に自動ロード。
- DuckDB を分析用 DB、SQLite を監視／履歴用 DB に使用（デフォルトは data/*.db）。
- Paper Trading は本番 DB と分離して動作（MockBrokerClient + data/paper_trading.db）。
- OpenAI API（gpt-4o-mini など）を使う機能は API キーが必要。失敗時は安全側フォールバック。

機能一覧
--------
- 実行エンジン起動: src/kabusys/run_execution.py
  - KABUSYS_ENV に応じて本番／ペーパートレードを切替
  - プロセス優先度設定・PIDファイル管理・停止フラグ対応
- 監視ループ起動: src/kabusys/run_monitoring.py
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs を記録
  - MONITOR_POLL_INTERVAL で間隔を上書き可能（デフォルト: 60 秒）
  - 停止フラグ data/stop_requested.flag を検知して終了
- 設定ウィザード: src/kabusys/config_setup.py
  - .env の生成・更新を対話式に支援
- 設定検証 CLI: src/kabusys/validate_config.py
  - 必須環境変数・ファイル存在・YAML パース等の事前チェック
- Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
  - ペーパートレード用 SQLite から稼働率・約定率・レイテンシ等を集計して PASS/FAIL 判定
- ポートフォリオ関連:
  - 選定・重み付け: kabusys.portfolio.portfolio_builder
  - 単位株丸め・ポジションサイズ: kabusys.portfolio.position_sizing
  - セクター制限・レジーム乗数: kabusys.portfolio.risk_adjustment
- リサーチ:
  - ファクター計算（momentum / value / volatility）: kabusys.research.factor_research
  - 将来リターン・IC・統計サマリー: kabusys.research.feature_exploration
- AI:
  - ニュース NLP（銘柄別センチメント）: kabusys.ai.news_nlp
  - レジーム判定（MA + マクロセンチメント）: kabusys.ai.regime_detector
- ユーティリティ:
  - ログ設定: kabusys.utils.logging_setup (stdout + 日次ローテートファイル)
  - プロセス優先度 / CPU affinity: kabusys.utils.process_priority

セットアップ手順
----------------
1. Python 環境
   - Python 3.10 以上を推奨（型アノテーションに | を使用）。
2. 依存ライブラリ（例）
   - duckdb, psutil, openai, PyYAML（validate_config の YAML 検証に必要）など。
   - 例: pip install duckdb psutil openai pyyaml
   - 実際のプロジェクトでは requirements.txt があればそれを使用してください。
3. ディレクトリ作成
   - デフォルト DB / フラグ用ディレクトリ: data/
   - ログ用ディレクトリは logs/（logging_setup が自動作成を試みます）
4. 環境変数 / .env
   - プロジェクトルートの .env（または .env.local）に設定を記載します。
   - 自動ロード順: OS 環境 > .env.local > .env（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0
   - .env の生成を対話的に行うには: python -m kabusys.config_setup
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

使い方
------
基本的な起動例（プロジェクトルートで実行）:

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 実行中に data/stop_requested.flag を作成すると安全に停止します。
    - エンジンは data/execution.pid を使用して PID 管理を行います。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は Settings に依らず本番 sqlite_path を使用して監視 DB を初期化します（init_monitoring_db）。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パスを指定可能。

- ログ
  - デフォルト: logs/<app_name>.log（app_name は "execution" / "monitoring" ...）
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定

- AI 機能
  - news_nlp.score_news, regime_detector.score_regime などは OpenAI API キー（OPENAI_API_KEY）が必要
  - API 継続失敗時はフェイルセーフで処理を続行し、重大な例外は上位に伝播させない設計です（ただし DB 書込失敗時は例外が発生する場合あり）

運用上のポイント
-----------------
- Kill Switch:
  - RiskMonitor の判定に基づき kabusys.monitoring.kill_switch が data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます（Settings.kill_flag_path でパス変更可）。
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（自動クリアは危険）。
- データ分離:
  - Paper Trading 用 DB は本番 DB と別ファイル（PAPER_TRADING_SQLITE_PATH）で管理されます。
- 権限/優先度:
  - 起動時に set_process_priority("high") を実行し優先度を上げます。権限不足で失敗する場合は警告のみ出ます。
- ログディレクトリ作成失敗時はファイル出力が無効化され stdout のみになります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / .env 自動ロード・Settings クラス
- config_setup.py                   — .env 対話式ウィザード
- validate_config.py                — 設定検証 CLI
- run_execution.py                  — ExecutionEngine 起動スクリプト
- run_monitoring.py                 — Monitoring ポーリング起動スクリプト

パッケージ別主要ファイル
- kabusys/ai/
  - news_nlp.py                      — ニュースを OpenAI でスコアリング
  - regime_detector.py               — レジーム判定（MA + マクロセンチメント）
- kabusys/monitoring/
  - monitoring_db.py                 — SQLite テーブル初期化・CRUD ラッパー
  - system_monitor.py                — CPU / メモリ / データ鮮度監視
  - trade_monitor.py                 — （trade ログ監視）※実装ファイルあり
  - risk_monitor.py                  — ドローダウン・ポジション監視
  - kill_switch.py                   — kill.flag 管理
  - monitoring_engine.py             — 各 Monitor を束ねる実行ループ
  - alert_manager.py                 — （アラート送信ラッパー）※実装ファイルあり
- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- kabusys/research/
  - factor_research.py
  - feature_exploration.py
- kabusys/utils/
  - logging_setup.py                 — 統一ログ設定
  - process_priority.py              — 優先度 / CPU affinity
- kabusys/tools/
  - paper_verification_report.py

注意事項・補足
--------------
- .env ファイルは絶対にリポジトリにコミットしないでください（機密情報保護）。
- validate_config の YAML 検証には PyYAML が必要です。未インストール時は YAML 検証がスキップされ、警告になります。
- OpenAI 呼び出し関連は外部 API に依存するため、API 利用制限やレイテンシを考慮した運用が必要です（コード内でリトライ/バックオフを実装）。
- スクリプトはすべてモジュール実行可能です（python -m kabusys.<module>）。バックグラウンドで動かす場合はプロセス管理 (systemd / supervisord / Docker) を推奨します。

問い合わせ / 開発メモ
--------------------
- 追加のユーティリティや設定ファイル（config/*.yaml）の雛形が必要な場合、scripts などに自動生成スクリプトを用意してください。
- データベーススキーマの変更は monitoring_db.init_monitoring_db のマイグレーションロジックに追記してください。

以上。必要であれば、README の英語版、systemd ユニット例、または .env.example の雛形を作成します。どれを優先しますか？