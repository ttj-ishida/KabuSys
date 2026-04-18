README
======

概要
----
KabuSys は日本株の自動売買・リサーチ用ライブラリ群です。  
このリポジトリには以下の機能群が含まれます:

- 発注実行エンジン (ExecutionEngine) とペーパートレード切替
- システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス生存確認）
- リスク監視（ドローダウン・ポジション上限）
- Kill Switch（条件に応じた停止フラグの書き込み）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP / 市場レジーム判定（OpenAI を利用する LLM 統合）
- ユーティリティ（設定ウィザード・設定検証・ログ設定等）
- ツール（Paper Trading 検証レポート生成）

主な特徴
--------
- 明確に分離された environment: development / paper_trading / live
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
  - monitoring は環境に関わらず本番 sqlite_path を使用する設計
- .env ウィザード（対話式）と起動前検証 CLI を提供
- DuckDB を用いた時系列ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / レジーム判定（API キー必須）
- ログは stdout と日次ローテートファイルで出力（logs/<app>.log、デフォルト）

セットアップ
----------
前提
- Python 3.9+（コードは typing / dataclasses / pathlib 等を利用）
- システム依存のライブラリ: duckdb, psutil, openai（AI 機能使用時）
- 開発環境では PyYAML があると config の YAML 検証が有効化される

手順（例）
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements ファイルがある前提）
   - pip install duckdb psutil openai
   - （テスト・追加ツール）pip install pyyaml
4. .env を準備
   - python -m kabusys.config_setup を実行して対話式に生成するか、
   - あるいは .env を手動で作成（下記参照）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

主要な環境変数（抜粋とデフォルト）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db  （Monitoring DB）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 環境時）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: デフォルト INFO
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）
- PAPER_FILL_MODE: ペーパートレードのフィルモード: instant / partial / never / reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） デフォルト: 60

使い方
------
起動系スクリプト（パッケージモジュール経由で実行）

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 停止は data/stop_requested.flag の作成で行う（kill/stop スクリプトから制御）
    - PID ファイル: data/execution.pid（設定: Settings.pid_file_path）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によりポーリング秒数を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は sqlite_path（monitoring DB）を利用し、DuckDB も接続してデータ鮮度等を確認
  - 停止フラグ: data/stop_requested.flag を置くとループ終了

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）

AI 関連の利用上注意
- OpenAI API の呼び出しには OPENAI_API_KEY が必要
- news_nlp.score_news / regime_detector.score_regime は API キー未設定時に ValueError を送出
- API エラー時はリトライやフォールバックロジックが実装されているが、レート制限や料金に注意する

停止 / Kill Switch / Flag の仕組み
- data/kill.flag : Kill Switch により ExecutionEngine を停止させるために作成されるファイル
  - KillSwitch はリスク条件（ドローダウン超過・ポジション上限超過）で flag を書き込む
  - ExecutionEngine は起動時に kill.flag をチェックし、存在すれば起動しない/停止する運用
- data/stop_requested.flag : run_monitoring / run_execution の外部停止用のシンプルなフラグ
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアする（本番では非推奨）

ログ
---
- デフォルトは logs/<app_name>.log を日次ローテーション（30 日分保持）して出力
- stdout への出力も同時に行われる（cron などの出力統合に配慮）

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージ宣言・バージョン
- config.py — Settings クラス: 環境変数の解決・自動 .env ロードロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（本番 / ペーパー切替）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト

サブパッケージ・モジュール
- ai/
  - news_nlp.py — raw_news を LLM でセンチメント解析し ai_scores に書き込む
  - regime_detector.py — ma200 とマクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（テーブル定義・読み書き）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID ファイル監視
  - risk_monitor.py — ドローダウン・ポジション上限のチェック
  - trade_monitor.py — （注文関連の監視。コードベースに実装あり）
  - kill_switch.py — kill.flag の発行ロジック
  - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
  - alert_manager.py — （LINE 等への通知管理。実装に依存）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注ロジック・リスク管理・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・等重/スコア重み
  - position_sizing.py — 株数計算・利用現金スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ／レジーム乗数
- research/
  - factor_research.py — モメンタム／バリュー／ボラティリティ計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定
  - その他ユーティリティ群
- data/  （実行時に使用することが多い）
  - monitoring.db （デフォルト SQLITE_PATH）
  - kabusys.duckdb （デフォルト DUCKDB_PATH）
  - paper_trading.db （ペーパートレード用）
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

注意点・トラブルシューティング
------------------------------
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で検出して行います。プロジェクトルートが検出できない場合は自動読み込みをスキップします。
- 自動読み込みを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップされ stdout のみで動作します。権限やディスク空き領域を確認してください。
- OpenAI 絡みの機能をテストする場合は、API 呼び出し部をモック化（unittest.mock.patch）するか、API キー/ネット接続に注意してください。
- monitoring は「監視」用途のため、常に本番用 sqlite_path を参照する実装になっています。テスト環境では DB パスの設定に注意してください。
- PAPER_FILL_MODE の値が不正な場合は Settings で ValueError が出ます。許容値: instant / partial / never / reject
- MONITOR_POLL_INTERVAL が 1 未満の値や不正な文字列の場合、デフォルト（60 秒）にフォールバックします。

開発
----
- 新しい設定項目を追加した場合は config_setup.py と .env.example（存在する場合）を更新してください。
- DuckDB のスキーマ（prices_daily, raw_financials 等）に依存する研究モジュールを追加・変更する際はテスト用の DuckDB を用意して単体テストを行ってください。
- AI 関連モジュールは外部 API 依存が強いため、ユニットテストでは外部呼び出しをモックすることを推奨します。

ライセンス
--------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在しない場合は管理者に問い合わせてください）。

付録: よく使うコマンド例
---------------------
- .env を対話式で作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔を 30 秒に変更）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading レポート（2026-04-01 〜 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

この README はコードベースの主要点をまとめたものです。実運用・導入時は必ず python -m kabusys.validate_config で設定を検証し、KABUSYS_ENV の設定（特に live の場合）を慎重に確認してください。