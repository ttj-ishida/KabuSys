KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のミニマルな実装です。本リポジトリには以下の主要機能が含まれます。

- 発注エンジン（ExecutionEngine）起動スクリプト
- システム／注文／リスク監視（Monitoring）
- ポートフォリオ構築・サイズ決定ロジック（純粋関数群）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用）
- ペーパートレード検証レポート出力ツール
- .env 対話式設定ウィザード・設定検証ツール

主な機能一覧
--------------
- 環境設定ウィザード (.env を対話式で作成): python -m kabusys.config_setup
- 設定検証 CLI（必須環境変数や config/*.yaml の検査）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパー混在に対応）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全分離）
- Monitoring 起動スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番用 sqlite_path を使用（監視は本番 DB を参照）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI）による銘柄別センチメント集計: kabusys.ai.score_news
- 市場レジーム判定（価格＋マクロニュースの組合せ）: kabusys.ai.regime_detector.score_regime
- ポートフォリオ構築（候補選定・重み付け・位置サイズ算出・セクター制限）: kabusys.portfolio

セットアップ手順
-----------------
前提:
- Python 3.9+ を推奨（ソースは型注釈や標準ライブラリを多用）
- DuckDB（python duckdb モジュール）、psutil、openai 等のパッケージが必要

推奨手順（例）
1. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール  
   （requirements.txt は本リポジトリに含まれていない想定のため最低限のパッケージ例）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の検証を行いたい場合）: pip install pyyaml

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example やスクリプト内のキーを参考にする（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も Fail として扱う場合: python -m kabusys.validate_config --strict

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動 ("instant"|"partial"|"never"|"reject")

使い方（主要コマンド）
--------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動（実際の発注／ペーパー）
  - python -m kabusys.run_execution
  - 停止方法: data/stop_requested.flag を作成すると起動中のループが終了します
  - ペーパートレード実行時は KABUSYS_ENV=paper_trading を設定（.env か環境変数で）

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で秒単位の間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 同様に data/stop_requested.flag を作成すると監視ループが終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

Kill Switch / フラグ類
---------------------
- Kill Switch: data/kill.flag を書き込むことで ExecutionEngine に停止を指示できます（KillSwitch クラス）。
  - 監視系が条件を満たすと kill.flag を書き込み、ExecutionEngine 側で検出して安全停止を試みます。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。
- stop_requested.flag: run_execution / run_monitoring のループを終了させるためのローカル停止フラグ（data/stop_requested.flag）。

ログ
----
- ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（kabusys.utils.logging_setup）。
  - 例: logs/execution.log, logs/monitoring.log
- 環境変数 LOG_DIR で変更可能。LOG_LEVEL で出力レベルを制御。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数自動ロード（.env / .env.local）と Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（ペーパー分離対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（OpenAI 必須）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite ベースの監視永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py —（アラート送信ロジック）
- execution/
  - execution_engine.py, order_manager.py, broker_factory.py, order_repository.py, reconciler.py, risk_manager.py
  - （実際の発注・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・資金配分
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC 計算など
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ群

注意点・運用上のポイント
------------------------
- Monitoring は監視対象の SQLite（デフォルト data/monitoring.db）を使用します。監視は本番 DB を参照する設計のため環境にかかわらず sqlite_path を使用します。
- ExecutionEngine は KABUSYS_ENV が paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB とデータを分離します。
- OpenAI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 呼び出し時のエラーはフェイルセーフで取り扱われる設計ですが、API キー未設定時は明示的に例外を投げる箇所があります。
- process_priority / cpu_affinity は psutil を使用します。権限不足や非対応 OS の場合は警告を出してスキップします。
- .env は絶対に Git にコミットしないでください（config_setup.py にも注意書きあり）。
- DuckDB / SQLite のスキーママイグレーションは一部自動化（列追加など）されていますが、運用前にバックアップを推奨します。

開発・テスト
-------------
- モジュールはユニットテストしやすいよう純粋関数や依存注入を意識して設計されています（例: OpenAI 呼び出しをラップしモックで差し替え可能）。
- settings は Settings クラス経由で参照するか、モジュール top-level で settings = Settings() を利用しています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効にできます。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。プロジェクトの LICENSE ファイルを参照してください。
- バグ報告・機能追加の提案は Issue にて受け付けてください。

お問い合わせ
------------
実装に関する質問や運用上の確認はリポジトリの Issue を利用してください。README にない運用ルールや config の追加項目がある場合は、config/*.yaml またはプロジェクト内ドキュメントを参照してください。

以上。必要であれば README の英語版、または各コマンドの実行例・.env のサンプルテンプレートを追加で作成します。