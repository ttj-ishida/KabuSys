README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
リサーチ（ファクター計算）、ポートフォリオ構築、ポジションサイズ計算、発注実行（ExecutionEngine）、監視（Monitoring）、AI（ニュースセンチメント／レジーム判定）といった主要コンポーネントを備えています。  
本リポジトリは本番運用とペーパートレードを明確に分離する設計になっており、設定は .env ファイル（または環境変数）で制御します。

主な機能
---------
- 発注エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定、PID 管理、停止フラグ（data/stop_requested.flag）に対応
- 監視ループ（run_monitoring）
  - システム資源（CPU/メモリ/ディスク）、データ鮮度、発注状態、リスク（ドローダウン・ポジション数）等を定期ポーリングしてログに保存
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視永続化（MonitoringDB）
  - SQLite を用いたテーブル群（system_status、trade_logs、positions、risk_logs、dashboard）
  - マイグレーション（カラム追加）のための冪等 init 関数を持つ
- Kill Switch（監視による自動停止）
  - しきい値超過時に data/kill.flag を書き込んでエンジンを停止させる仕組み
- Paper Trading 検証レポート生成ツール
  - data/paper_trading.db を解析して稼働率、注文成功率、送信率、レイテンシ等を集計・判定
- 研究モジュール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア加重、セクターキャップ適用、ポジションサイズ計算（単元株丸め・集約キャップ処理）
- AI モジュール（ai）
  - OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
  - API 失敗時はフォールバック動作を行い、フェイルセーフに配慮
- 設定ウィザード（config_setup）と検証 CLI（validate_config）
  - .env の対話的作成 / 更新、起動前の設定チェック（--strict で警告も FAIL 扱い）

セットアップ手順
----------------
以下は開発マシンでの一般的な手順です。

1. Python 環境準備
   - 推奨: Python 3.10+（実際の要件は環境に合わせて調整）
   - 仮想環境例:
     - python -m venv .venv
     - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - 本コードで使用している主な外部パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. .env の作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照してください）
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - logs/
   - data/
   - 上記は自動生成される場合がありますが、アクセス権等は確認してください。

使い方
------
基本的な起動方法と CLI の例を示します。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 実行中に停止させるには data/stop_requested.flag を作成する（または Kill Switch による停止）。

- 監視プロセスを起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）へログを書き込みます。

- 設定ウィザード:
  - python -m kabusys.config_setup
    - .env を対話的に作成・更新します。

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで終了コード 1 を返します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- OpenAI を使うスクリプト（ニューススコアリング / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。
  - API による失敗はフォールバックして継続する設計ですが、キーは必須です（呼び出し時にチェックあり）。

運用上の注意
- Paper Trading は本番 DB と完全分離:
  - KABUSYS_ENV=paper_trading のとき、sqlite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
- Kill Switch / Stop Flag:
  - 監視側は条件検出時に data/kill.flag を書き込みます（Settings.kill_flag_path で制御可）
  - 実行停止のために data/stop_requested.flag を用いてプロセスに停止指示を出す実装（run_execution/run_monitoring が参照）
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（defaults: logs/、30 日保持）
  - setup_logging を各スクリプトで呼び出して統一的に設定

主要環境変数一覧
----------------
（主要なものを抜粋）

- 必須（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番で 1 は危険）

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
  - PID_FILE_PATH（実行エンジンの PID ファイル、デフォルト data/execution.pid）
  - KILL_FLAG_PATH（kill.flag のパス、デフォルト data/kill.flag）

- OpenAI 関連
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）

- その他
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数、デフォルト 60）
  - PAPER_FILL_MODE（instant | partial | never | reject）（ペーパートレードの約定モード）

ディレクトリ構成（抜粋）
-----------------------
以下はソースツリーの主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数と Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         — （実装ファイルが存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （実装ファイルが存在）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/                 — ExecutionEngine 関連コンポーネント（broker_factory 等）
  - data/                      — データ読み書き / pipeline / stats（存在するサブモジュール）

（上記は抜粋です。細かいモジュールはソースツリーを参照してください）

開発・運用上の補足
------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動で読み込みます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で、既存 DB にカラムが足りない場合は ALTER TABLE で追加します。
- テスト / モック:
  - KABUSYS_ENV=paper_trading による MockBroker の使用で実運用 DB と完全分離できます。テスト時は各モジュールの関数をスタブ化して利用できます。
- セキュリティ:
  - .env は機密情報を含むため Git へコミットしないでください（config_setup でも注意書きを出力します）。

ライセンス・貢献
----------------
- 本 README に記載のライセンス情報は含まれていません。実際のプロジェクトの LICENSE ファイルを参照してください。  
- コントリビューションは通常の GitHub Flow に従ってください（Fork → PR）。

最後に
------
初期セットアップ時はまず python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で設定を検証してください。  
ペーパートレードに切り替えて動作確認することで、本番 DB を汚すことなく挙動確認が可能です。必要があればさらにドキュメントや例（.env.example, scripts）を追加してください。