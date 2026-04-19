KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な機能として、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント／レジーム判定）などを備え、ローカルやペーパートレード、本番環境で運用できるよう設計されています。

バージョン: 0.1.0

主な機能
--------
- ExecutionEngine
  - 実際のブローカー（kabuステーション）またはペーパートレード用の MockBroker を使った発注
  - リスク管理（ポジション上限、ドローダウン等）
  - 注文／約定ログの永続化（SQLite）
- Monitoring
  - システム稼働監視（CPU/メモリ/ディスク、プロセス生存）
  - 注文滞留・約定異常・リスク監視
  - Kill Switch（一定条件で停止フラグを書き込み、Execution を停止）
  - 監視ログ永続化（SQLite）
- Portfolio construction
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップ、レジーム補正
- Research
  - DuckDB を用いたファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターンの計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（OpenAI）
  - ニュース記事のセンチメント解析（gpt-4o-mini を想定）
  - マクロニュースを用いた市場レジーム判定
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト

セットアップ手順（ローカル開発向け）
--------------------------------
1. リポジトリをクローン
   - git clone ...（省略）

2. Python 環境を用意
   - Python 3.10+ を推奨。仮想環境を作成して有効化してください。

3. 依存ライブラリをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存例:
     - duckdb, psutil, openai, PyYAML（設定検証で必要）など

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後に設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も FAIL 扱いになります

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使うなら必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（例: INFO）

   注: .env 自動ロードはデフォルトで有効です（パッケージルートの .env / .env.local を読みます）。
   無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方
------
- 実行（ExecutionEngine）
  - 通常起動:
    - python -m kabusys.run_execution
  - 挙動補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、発注履歴は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動補足:
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（監視ロガーは環境に依存せず本番 DB を参照）。
    - 監視中にプロセス停止や異常が検出されると kill.flag を書き、ExecutionEngine 側で検知して停止できます。
    - ループを外部から終了させたい場合はプロジェクトルートの data/stop_requested.flag を作成してください（run_monitoring と run_execution の両方がこのフラグを監視します）。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります。

- .env ウィザード
  - python -m kabusys.config_setup

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

ログ
----
- ログはデフォルトで logs/ 下に日次ローテーションで出力されます（logs/<app_name>.log）。
- setup_logging(app_name="execution" 等) により root ロガーが設定されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

停止・KillSwitch
----------------
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件を満たすと data/kill.flag を作成します。ExecutionEngine 起動時に kill.flag が存在すると起動後に停止処理が行われます。
- 管理者が明示的に停止したい場合は data/stop_requested.flag を作成してください。run_execution/run_monitoring はこのファイルを検出して安全に終了します。
- kill.flag を手動でクリアする場合はファイルを削除してください（実行環境の安全運用上は注意して行ってください）。

設定（主な環境変数）
-------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定の読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py            — ニュースの LLM センチメントスコアリング
  - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — 監視ログの SQLite 永続化層
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — 注文・約定の監視（ファイル内未表示の想定コンポーネント）
  - risk_monitor.py        — ドローダウン／ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor の統合ループ
  - alert_manager.py       — アラート送信（ファイル内未表示の想定コンポーネント）
- execution/
  - execution_engine.py    — ExecutionEngine 本体（発注セッション管理）
  - broker_factory.py      — Broker クライアント生成（実ブローカ or Mock）
  - order_manager.py       — 注文管理
  - order_repository.py    — 注文永続化（SQLite 等）
  - reconciler.py          — ブローカー状態との整合処理
  - risk_manager.py        — 発注前リスクチェック
- portfolio/
  - portfolio_builder.py   — 候補選定／重み計算
  - position_sizing.py     — 株数決定ロジック
  - risk_adjustment.py     — セクターキャップ／レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — IC/統計サマリー等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定

運用上の注意
------------
- 本番運用（KABUSYS_ENV=live）の場合は .env の内容、LINE 通知設定などを慎重に確認してください。validate_config の live 向け追加チェックを活用してください。
- OpenAI を使う AI 機能は API 費用・レート制限の影響を受けます。API キーやリトライ設定に注意してください。
- DB（SQLite / DuckDB）ファイルは適切なバックアップ／アクセス管理を行ってください。
- ログディレクトリの書き込み権限やデーモン化（systemd など）での運用設定は各環境に合わせて行ってください。

開発者向けメモ
---------------
- Settings クラスは環境変数アクセスをラップしています。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- .env の自動ロードはプロジェクトルート（.git or pyproject.toml を探索して特定）から行われます。配布後も動作するように設計されています。
- AI 呼び出し部分（news_nlp, regime_detector）は外部 API 呼び出しであり、テスト時は内部の _call_openai_api をモックすることを想定しています。

問い合わせ / 貢献
----------------
- バグ報告や機能要望は issue を作成してください。プルリクエスト歓迎です。README の補足やドキュメントの改善も助かります。

以上。運用・開発ともに安全性を優先して導入と設定を進めてください。