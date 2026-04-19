README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な機能は下記のとおりで、監視（Monitoring）・実行（Execution）・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント）などを含みます。  
コードはモジュール化されており、ユニットテストしやすい純粋関数（ポートフォリオ計算等）と、SQLite / DuckDB を使った永続化・分析基盤を組み合わせる設計です。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV 環境変数）。
  - paper_trading モードでは MockBrokerClient を使用し、data/paper_trading.db に完全分離して記録。
  - リスク管理（RiskManager）や注文管理（OrderManager）を含む。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視。
  - kill.flag（Kill Switch）による ExecutionEngine の停止制御。
  - 監視ログは SQLite（monitoring.db）へ永続化。
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、重み計算（等金額・スコア重み）、ポジションサイズ計算、セクターキャップ・レジーム補正など。
  - 純粋関数として実装され、DB参照なしで容易にテスト可能。
- リサーチ（research モジュール）
  - DuckDB 上でファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン、IC計算、統計要約などを提供。
- AI（ai モジュール）
  - OpenAI を用いたニュースセンチメント集計（news_nlp）、市場レジーム判定（regime_detector）。
  - OpenAI API 呼び出しはリトライ・バリデーション・フェイルセーフを備える。
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントで | を使用しているため）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai 等のパッケージが必要

1) 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2) 必要パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の YAML 検出機能を使う場合: pip install pyyaml
   （requirements.txt がプロジェクトにあれば pip install -r requirements.txt を使ってください）

3) 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 対話式ウィザードで作成する:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要な任意 / 設定例:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - LOG_LEVEL, LOG_DIR など

4) 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------
- 実行エンジン（ExecutionEngine）起動
  - 本番モード例:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード例（MockBrokerClient を使用、記録先は data/paper_trading.db）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid に PID が書かれます。停止は kill.flag により監視側から行うか、stop フラグを作成します。

- 監視ループ（Monitoring）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（monitoring DB）を使用し、KABUSYS_ENV にかかわらず本番 sqlite_path を参照します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いに

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

環境変数（主なもの）
--------------------
- KABUSYS_ENV: development | paper_trading | live（実行環境）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR: ログ設定
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_PATH, PID_FILE_PATH: kill.flag / pid ファイルのパス（必要に応じて上書き）

停止 / Kill Switch の運用
------------------------
- 監視モジュールは一定条件で kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- KillSwitch は data/kill.flag を書き、ExecutionEngine は起動時に kill.flag をチェックします（存在すれば起動しない）。
- kill.flag を明示的にクリアするには KillSwitch.clear() をプログラムで呼ぶか、手動でファイルを削除してください。
- ExecutionEngine の停止制御は stop_requested.flag（data/stop_requested.flag）や kill.flag を監視しています。

ログ
----
- 共通のログ設定ユーティリティ (kabusys.utils.logging_setup.setup_logging) を使用します。
- デフォルトでは stdout 出力と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- LOG_DIR を設定してログ保存先を変更できます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数自動読み込み・Settings クラス（.env/.env.local の自動読み込み機能あり）
- config_setup.py
  - .env の対話式作成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py : ログ設定ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py : SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py : システム状態・データ鮮度監視
  - trade_monitor.py : （trade 監視ロジック）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag 書込みロジック
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : （LINE 等へ通知するアラート管理; コードベース参照）

- execution/
  - execution_engine.py : ExecutionEngine 本体
  - broker_factory.py : ブローカークライアントの生成（Mock 本番切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数決定・スケーリング
  - risk_adjustment.py : セクターキャップ・レジーム乗数

- research/
  - factor_research.py : ファクター計算（momentum, value, volatility）
  - feature_exploration.py : 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py : ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py : ETF MA とマクロニュースを合成して market_regime を判定

- tools/
  - paper_verification_report.py : Paper Trading の検証レポート生成スクリプト

注意事項・運用上のポイント
--------------------------
- .env は機密情報を含むため決して Git にコミットしないこと（config_setup も注記あり）。
- OpenAI API を利用する機能は API キーが必須。呼び出しはリトライ・サニタイズを行うが、API コストに注意してください。
- monitoring は監視データを一貫して本番 sqlite_path に書きます（KABUSYS_ENV に依らず）。
- paper_trading は本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使う）。
- プロセス優先度設定（set_process_priority）はプラットフォームにより動作しない場合があります（権限や OS に依存）。失敗しても警告を出して継続します。

開発・テスト
-------------
- ポートフォリオやリサーチ等は純粋関数で実装されており、ユニットテストが書きやすい構造です。
- OpenAI 呼び出し部分は内部で分離しているため、ユニットテスト時は該当関数をモックできます（例: unittest.mock.patch）。
- DuckDB / SQLite に対するクエリは外部に依存するため、テスト用にサンプル DB を用意してテストを実行することを推奨します。

問い合わせ / 貢献
-----------------
- 仕様改善やバグ修正は Pull Request を送ってください。README や config/*.yaml のドキュメントを更新する際は、実行時の挙動に齟齬が出ないよう該当モジュールのコメントと合わせて確認してください。

以上がこのリポジトリの概要・導入手順・使い方・ディレクトリ説明です。必要であれば、各モジュールの API 使用例や運用チェックリスト（起動手順、監視確認、STOP/KILL の手順など）を別途ドキュメント化します。