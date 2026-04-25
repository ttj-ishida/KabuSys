README（日本語）
===============

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は戦略に基づいた銘柄選定・ポジションサイズ計算・発注実行の補助、およびシステム監視／ペーパートレード検証／AI を使ったニュースセンチメント解析などの運用機能を提供することです。

特徴（機能一覧）
---------------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードモードを切り替え可能（KABUSYS_ENV）。
  - Paper Trading モードでは MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録。
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知機構を備える。

- 監視プロセス（run_monitoring.py / monitoring パッケージ）
  - システム負荷、データ鮮度、発注ログなどを定期ポーリングして SQLite に記録。
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch（停止シグナル）を実装。
  - アラート管理（AlertManager 経由）により外部通知を出せる設計。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算（単元丸め・リスク制限）、
    セクター上限、レジーム乗数等の純粋関数群を提供。

- リサーチ（kabusys.research）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）。
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリなど。

- AI（kabusys.ai）
  - OpenAI を利用したニュースセンチメント解析（news_nlp）およびマーケットレジーム判定（regime_detector）。
  - API エラー時のリトライやフェイルセーフ動作を備える。

- ユーティリティ
  - 環境設定ウィザード（kabusys.config_setup）と設定検証 CLI（kabusys.validate_config）。
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）。
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。

セットアップ手順
----------------
前提
- Python 3.9+（型ヒント等に合わせたバージョン）
- システムに sqlite3 が利用可能
- duckdb, psutil, openai 等の Python パッケージが必要

推奨インストール手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install PyYAML

   ※ requirements.txt があればそれを使ってください（このリポジトリには同梱されていません）。

3. プロジェクトルートに移動（.git または pyproject.toml がある場所）
   - このリポジトリの構成では src/ がパッケージフォルダです。PYTHONPATH を調整するか、プロジェクトルートから実行してください。

4. .env を作成
   - python -m kabusys.config_setup を実行すると対話式ウィザードで .env を生成できます。
   - あるいは .env.example を参考に .env を作成してください（.env は絶対に Git にコミットしないでください）。

主な環境変数（概要）
- 必須（実運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要なもの（デフォルトあり）
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
  - OPENAI_API_KEY: AI 機能を使う場合に必要

- 監視専用
  - MONITOR_POLL_INTERVAL: 監視プロセスのポーリング間隔（秒、defaults: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などは Settings で参照

使い方（主要コマンド）
--------------------

1) 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 対話式で環境変数を設定し .env を生成します。

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります。

3) 実行エンジン起動（Execution）
   - 本番（通常）:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパートレード（DB を分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行時の挙動:
     - PID を data/execution.pid（デフォルト）に保存
     - data/stop_requested.flag があると起動しない / ループを停止する
     - Paper Trading の場合は paper_sqlite_path にデータを書き込み本番 DB と分離

4) 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
   - 監視は常に settings.sqlite_path（monitoring DB）を使用（環境にかかわらず）

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間を指定する例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db で指定、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

6) AI 関連（ニューススコア / レジーム判定）
   - kabsys.ai.score_news / kabusys.ai.regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーを受け取り動作します。
   - 簡易的に使うにはスクリプトやジョブから該当関数を呼び出してください。
   - OpenAI を利用するには OPENAI_API_KEY を設定してください。

停止・フラグ管理
- 停止フラグ（外部からプロセスを停止したい場合）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了または起動を防ぎます。
- Kill Switch（自動評価による停止）
  - リスク条件に応じて KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番環境では 0 を推奨します。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- コンソール出力は stdout に出ます。ログディレクトリは環境変数 LOG_DIR で変更できます。

ディレクトリ構成
----------------
以下は主なファイル・パッケージのツリー（src/kabusys 配下）です。重要なモジュールを抜粋しています。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/Settings 管理
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/                 — 発注関連（Engine、OrderManager 等）
    - data/                      — データ処理・パイプライン（DuckDB 用テーブル定義等）
    - research/                  — 研究用コード（DuckDB 結合）
    - その他モジュール...

注意事項 / 運用上のポイント
--------------------------
- .env は機密情報を含むため必ず .gitignore に設定し、リポジトリへコミットしないでください。
- 本番モード（KABUSYS_ENV=live）の場合は設定を慎重に確認してください（validate_config の警告を参照）。
- AI（OpenAI）利用部分は API キーが必要で、コストやレート制限に注意してください。API エラー時はフォールバック挙動がありますが十分な監視を行ってください。
- DuckDB / SQLite のパスや logs ディレクトリの親ディレクトリが存在しない場合、警告が出ます。必要に応じて事前に作成してください（logging_setup は起動時にディレクトリ作成を試みます）。

よくあるコマンドまとめ（例）
----------------------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
----------------
- YAML 設定ファイル（config/*.yaml）や DuckDB テーブル定義を編集して戦略・リスク設定を変更できます。
- AI モジュールは外部 API を呼び出すためテストはモック（unittest.mock.patch）で行う設計が各所に施されています。CI テストでは API 呼び出しをモックすることを推奨します。

以上。必要であれば README にサンプル .env のテンプレートや具体的な systemd / cron 用の起動例（Unit ファイルやサービス定義）を追記できます。どの情報を追加したいか教えてください。