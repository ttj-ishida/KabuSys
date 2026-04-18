README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ペーパートレード用の分離された DB と Mock ブローカー
- ポートフォリオ構築、ポジションサイズ計算、リスク調整の純関数群
- ファクター計算・特徴量探索（DuckDB を使用）
- ニュースの LLM による NLP スコアリングと市場レジーム判定（OpenAI 使用）
- 監視ログ保管用の SQLite 層、Kill Switch による安全停止機構
- 環境設定ウィザード・設定検証ツール・ペーパートレード検証レポート生成

バージョン
---------
0.1.0

主な機能一覧
-------------
- Execution
  - 実発注（live）／ペーパートレード（paper_trading）を切り替え可能
  - ブローカークライアントは環境に応じて実装を切り替え（MockBroker）
  - 発注・オーダー管理、リスク管理、リコンシリエーションを含む実行エンジン

- Monitoring
  - システムリソース（CPU / メモリ / ディスク）や Execution プロセスの監視
  - 注文ログ、リスクログ、ダッシュボード情報の永続化（SQLite）
  - リスクモニタ（ドローダウン・保有銘柄数の監視）と Kill Switch
  - アラート送信フック（LINE 等を想定）

- Portfolio / Risk
  - 候補選定（スコア順）、等金額・スコア重み配分
  - セクター上限適用、レジームに基づく乗数
  - ポジションサイズ計算（単元丸め、コストバッファ、aggregate cap）

- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - ニュース記事の銘柄別センチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（OpenAI）

- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト

セットアップ手順
----------------

1. Python と仮想環境
   - Python 3.10 以上を推奨（Union 型表記や型ヒントに依存）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要なライブラリ（最低限）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml の検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. リポジトリルートに移動
   - プロジェクトルートは .git または pyproject.toml があるディレクトリとして自動検出されます。

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 主な任意／推奨環境変数（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — (development)
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
     - OPENAI_API_KEY（AI 機能を使用する場合）
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする（CI 等の厳格チェック）:
     - python -m kabusys.validate_config --strict

6. データ／ログディレクトリ
   - デフォルトで以下ディレクトリ／ファイルを使用します:
     - data/monitoring.db（監視用 SQLite）
     - data/paper_trading.db（ペーパートレード用 SQLite）
     - data/execution.pid（Execution の PID ファイル）
     - data/kill.flag（Kill Switch）
     - logs/（ログファイル。kabusys.utils.logging_setup が作成）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で exit(1)

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は .env の KABUSYS_ENV に関係なく本番 sqlite_path を使用します
  - 停止方法: data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を利用（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します
  - 実行中に停止するには data/stop_requested.flag を作成することで安全停止を試みます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH or data/paper_trading.db

重要な挙動・運用メモ
-------------------
- KABUSYS_ENV:
  - development / paper_trading / live のいずれか。live 時は注意喚起の警告が出ます。
  - paper_trading では発注が仮想化され、ペーパートレード用 DB が使われます。

- Kill Switch:
  - RiskMonitor や他判定で条件を満たすと data/kill.flag が生成され、Execution を停止させる仕組みがあります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。

- PID / stop フラグ:
  - 実行・監視プロセスは data/execution.pid や data/stop_requested.flag を使って外部から操作できます。

- ログ:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。ログは stdout と logs/<app_name>.log に日次ローテートで出力されます。

ディレクトリ構成
-----------------
以下は src/kabusys 配下の主要ファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py     — 市場レジーム判定（ETF + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・ラッパー
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装を想定）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信の抽象化）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/
    - pipeline.py            — prices_daily などを扱う DuckDB 関連ユーティリティ
    - stats.py               — 正規化等のユーティリティ
  - utils/
    - logging_setup.py
    - process_priority.py
    - (その他ユーティリティ)

補足・依存関係
--------------
- 必須パッケージ: duckdb, psutil, openai
- 追加（任意）: PyYAML（config/*.yaml の検証）
- OpenAI API を使う機能を動かすには OPENAI_API_KEY が必要です。
- .env は絶対に Git にコミットしないでください（config_setup の冒頭にも注意書きあり）。

開発・テスト
-------------
- 設定検証 CLI（validate_config）は CI に組み込みやすく、--strict モードで警告を失敗と扱えます。
- AI 呼び出し部分は API 呼び出しをラップした関数をモック化しやすく設計されています（ユニットテストでの差替えを想定）。

ライセンス
---------
（ここにライセンス情報を記載してください）

問い合わせ
----------
- 開発者 / 保守者向けの連絡先・ドキュメントはプロジェクト管理者に確認してください。

以上。README に不足している部分や、より詳しい運用手順（デプロイ手順、systemd ユニット例、CLI 引数詳細など）が必要であれば知らせてください。