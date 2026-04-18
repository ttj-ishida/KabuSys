README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのサンプル実装です。  
主な目的は次の通りです。

- 売買ロジック（ExecutionEngine）と監視・Kill Switch（Monitoring）を分離した実行アーキテクチャ
- DuckDB / SQLite を用いたデータ分析・監視ログ永続化
- ポートフォリオ構築、ポジションサイジング、リスク制御のユーティリティ群
- ニュース NLP / レジーム判定のための LLM（OpenAI）連携
- ペーパートレード用の分離された DB と検証ツール群

バージョン: 0.1.0

主要機能
--------
- ExecutionEngine
  - 本番 / ペーパートレードを切り替えて発注を実行
  - ブローカークライアントは環境に応じて実装を切り替え（paper_trading では Mock）
  - 発注管理、リスク管理、リコンサイルの統合
- Monitoring
  - システム状態（CPU / メモリ / ディスク / プロセス生存）とデータ鮮度の定期チェック
  - 注文ログ、リスクログ、ダッシュボードの永続化（SQLite）
  - Kill Switch（drawdown やポジション数超過で data/kill.flag を書き込み ExecutionEngine を停止）
  - 停止フラグ（data/stop_requested.flag）を用いた graceful shutdown
- Portfolio モジュール（純粋関数）
  - 候補選定、等比率 / スコア加重配分、ポジション数算出（単元株丸め含む）
  - セクター上限・レジーム乗数適用ロジック
- Research（DuckDB ベース）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI 機能（OpenAI）
  - ニュースを LLM でスコアリングし ai_scores テーブルへ保存
  - マクロニュース + ETF MA 乖離を組み合わせた市場レジーム判定
  - リトライ・バリデーション等の堅牢な API 呼び出し実装
- ツール
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提条件
--------
- Python 3.10+（ファイル内の型注釈・構文を想定）
- SQLite（標準ライブラリに含む）
- 必要な Python パッケージ（下記参照）

主な Python 依存パッケージ
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に必要）
（必要なパッケージはプロジェクト用の requirements.txt を用意してください）

インストール（例）
-----------------
仮想環境を作成して依存関係をインストールする例:

1. 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

環境設定 (.env)
---------------
プロジェクトルートに .env を置くことで環境変数を管理します。自動ロード機能が有効（デフォルト）なため、.env を作成すると起動時に読み込まれます。

推奨ワークフロー（対話式ウィザード）:
  python -m kabusys.config_setup

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境時に使用）
- LOG_LEVEL: ログレベル
- KILL_FLAG_CLEAR_ON_START: 本番環境での Kill Flag 自動クリア制御（0/1）

設定の検証
----------
作成した .env や config/*.yaml の基本チェックを行う:
  python -m kabusys.validate_config
--strict オプションを付けると警告も失敗扱いになります。

使い方（起動/停止など）
-----------------------

1) 監視プロセスを起動
   python -m kabusys.run_monitoring

   - ポーリング間隔を環境変数で上書き:
     export MONITOR_POLL_INTERVAL=30
   - 監視プロセスは常に本番用の sqlite_path を使用して監視データを記録します（KABUSYS_ENV に依存せず）
   - 停止: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが終了します

2) 実行エンジン（Execution）を起動
   python -m kabusys.run_execution

   - KABUSYS_ENV=paper_trading の場合:
     - MockBrokerClient を使用し、data/paper_trading.db にペーパートレードデータを記録（本番 DB と分離）
   - 起動時の Kill Switch / stop flag により起動抑止や停止が行われます
   - エンジンの PID は data/execution.pid に書き込まれます

3) 実行の停止（Kill Switch）
   - KillSwitch は監視結果に応じて data/kill.flag を書き込みます（ExecutionEngine はこれを検知して停止）
   - 手動で停止したい場合は stop_requested.flag（監視・実行ループを止める）や execution.pid を参照してプロセスを停止します

4) Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   オプション:
   - --from YYYY-MM-DD
   - --to YYYY-MM-DD
   - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

ログ
---
- ログは標準出力（stdout）とファイル出力（logs/<app_name>.log、日次ローテーション）に出ます。
- ログ設定は kabusys.utils.logging_setup.setup_logging() を通じて統一的に行われます。

主要ファイル／コマンド一覧
------------------------
- python -m kabusys.config_setup : .env 対話式作成ウィザード
- python -m kabusys.validate_config : 環境・設定チェック
- python -m kabusys.run_monitoring : 監視サービス起動
- python -m kabusys.run_execution : ExecutionEngine 起動
- python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート

注意事項
--------
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API 呼び出し時の課金とレート制限に注意してください。
- .env は絶対にリポジトリにコミットしないでください（秘密情報を含む）。
- 本番環境で KABUSYS_ENV=live を設定する場合は、LINE 通知設定や Kill Switch の設定などを十分に確認してください。
- 自動で .env を読み込む機能を無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時に便利）。

ディレクトリ構成
---------------
プロジェクトルート（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定取得ロジック
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring 起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム監視ロジック
    - trade_monitor.py       — （注文関連監視: ファイル内にて定義）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + ETF MA）
  - data/                    — 実行時に使用する SQLite / PID / flag などを置く想定
  - tools/
    - paper_verification_report.py

（注）実際のリポジトリにはさらに細かな実装ファイルや補助スクリプトが含まれる想定です。

開発者向け補足
---------------
- DuckDB 接続を受け取ってクエリを実行する設計のため、研究系モジュールは本番の発注ロジックに影響を与えません（安全にオフラインで解析可能）。
- 監視・実行プロセスは PID / flag によるシンプルなプロセスマネジメントを採用しています。コンテナ化や systemd での運用時はそれらの仕組みと組み合わせて使用してください。
- テスト時は外部 API 呼び出し関数（_call_openai_api 等）をパッチしてモック化することが容易にできるよう設計されています。

ライセンス / 免責
-----------------
この README はサンプル実装に基づく説明です。実運用に用いる場合は安全性・法令順守・取引所規約・資金管理に関する十分な検証と監査を行ってください。

---
必要に応じて README の一部（例: 環境変数一覧やコマンドの具体例）を拡張できます。どの項目を詳しく追記したいか教えてください。