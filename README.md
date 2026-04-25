# KabuSys

日本株向け自動売買システムの一部（ライブラリ＋起動スクリプト群）。  
このリポジトリは戦略構築、ポートフォリオ組成、実行エンジン、監視、研究用ツール、AI（ニュース／レジーム判定）などのモジュールを含みます。

> 注意: 本 README はリポジトリ内のソースコード（src/kabusys/**）をもとにまとめた使用案内です。実行には各種外部ライブラリ（duckdb、psutil、openai など）と環境変数の設定が必要です。

## プロジェクト概要
- モジュール群は主に次の責務を持ちます:
  - execution: 発注エンジン、オーダー管理、リスク管理、ブローカークライアント抽象化（ペーパートレード用の Mock をサポート）
  - monitoring: システム稼働状況／注文ログ／リスク監視、Kill Switch（フラグファイルによる ExecutionEngine 停止）
  - portfolio: 候補選定・重み計算・ポジションサイズ決定・セクター制限などの純粋関数群
  - research: DuckDB を使ったファクター計算や特徴量解析
  - ai: OpenAI を使用したニュースセンチメント / レジーム判定（OpenAI API キーが必要）
  - tools: Paper Trading 検証レポート生成など補助ツール
  - utils: ロギング設定、プロセス優先度設定、設定読み込みなど共通ユーティリティ

## 主な機能一覧
- ExecutionEngine 起動（本番 / ペーパートレード切替）
  - KABUSYS_ENV により paper_trading モードでは MockBrokerClient を使用し DB を分離
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）のループ実行
  - システム負荷、データ鮮度、ポジション／ドローダウン監視、アラート連携（LINE 等の設定あり）
  - Kill Switch による安全停止（data/kill.flag）
- Portfolio コンストラクション（等金額・スコア加重・リスクベース等）
- Research: ファクター計算（モメンタム／ボラティリティ／バリュー等）、IC・統計サマリー
- AI:
  - ニュース記事の銘柄別センチメント付与（OpenAI を利用）
  - マクロニュース + ETF MA による市場レジーム判定
- ユーティリティ:
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール

## システム要件（推奨）
- Python 3.10+
- 必須（または利用する機能に応じて）パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config/*.yaml の構文チェックを行う場合）

インストールはプロジェクトの要件ファイルに従ってください（本リポジトリに requirements.txt は含まれていないため、利用する機能に応じて個別に pip install してください）。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順（初めての導入）
1. リポジトリをクローン・作業ディレクトリへ移動
2. 仮想環境を作成し、必要ライブラリをインストール（上記参照）
3. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - セキュリティ上、.env は決して Git にコミットしないでください
4. 設定検証を実行
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit 1）
5. データディレクトリ（data/）やログディレクトリ（logs/）は起動時に自動作成されることがありますが、必要に応じて手動で作成してください。

## 主要な環境変数（代表）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行モード:
  - KABUSYS_ENV — execution の実行環境: "development" | "paper_trading" | "live"
- データベース:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）
- ロギング:
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…。デフォルト: INFO）
  - LOG_DIR — ログ出力先（デフォルト: logs/）
- AI:
  - OPENAI_API_KEY — OpenAI を利用する場合に必要
- その他:
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。デフォルト 60（run_monitoring で使用）
  - PAPER_FILL_MODE — ペーパートレードの約定動作（instant|partial|never|reject。デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト: 0。本番では 0 推奨）

Settings モジュールはプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

## 使い方（起動・ツール）
- 環境変数をセットし、.env を用意した上で下記を実行します。

1. 実行エンジン（ExecutionEngine）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
   - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
   - 実行中、同フラグファイルが作成されるとエンジンは停止します。
   - 実行時に data/execution.pid に PID を書く挙動があります。

2. 監視ループ（Monitoring）を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
   - 監視は Settings.sqlite_path（監視用 DB）を使用。duckdb は Settings.duckdb_path。
   - 停止は data/stop_requested.flag を作成してください（存在検知でループを抜けます）。

3. 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6. AI 関連（ニューススコア・レジーム判定）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行するには OPENAI_API_KEY（引数・環境変数いずれか）を設定してください。

ログ設定:
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出しています。
- ログは stdout に出ると同時に logs/<app_name>.log に日次ローテーション（30日分保持）で保存されます。
- LOG_DIR / LOG_LEVEL の環境変数で上書き可能。

停止フラグ / Kill Switch:
- data/stop_requested.flag: run_execution/run_monitoring が存在を検知して終了するために使われます（管理者が作成・削除）。
- data/kill.flag: monitoring の KillSwitch が条件を満たしたときに書き込むフラグ。ExecutionEngine は起動時や実行中にこれを検出して安全停止します（KILL_FLAG_CLEAR_ON_START による自動クリア設定あり）。

## ディレクトリ構成（主要ファイル）
リポジトリ内の src/kabusys 配下を抜粋。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                — 発注エンジン関連（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite を用いた監視 DB 層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のディレクトリにはさらに細分されたモジュール群があります。ここでは主要なファイルを列挙しています。）

## 開発上の注意 / 備考
- Settings はプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込みます。テストで自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live は DB を明確に分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出しには外部 API（OpenAI）が必要です。API 呼び出しはリトライ・フェイルセーフ（失敗時はスコアをゼロにする等）の設計になっていますが、API キーの管理・コストに注意してください。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、実行はコンソール出力のみで継続します（重大な失敗はログに警告が出ます）。
- Python の型ヒントやファイル冒頭の docstring に動作上の重要な仕様が記載されています。実運用前に validate_config や unit test を必ず行ってください。

---

以上がこのコードベースの概要と基本的な利用方法です。運用・本番導入時は config/*.yaml や .env の内容を慎重に確認し、KABUSYS_ENV=live の場合は特に kill flag の自動クリア設定や LINE 通知設定などを確認してください。必要であれば README をプロジェクト固有の手順（systemd ユニット、コンテナ化、CI/CD）に合わせて拡張してください。