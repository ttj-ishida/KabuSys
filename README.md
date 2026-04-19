README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤ライブラリです。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象化（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限）
- 研究（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュースのセンチメント評価、マーケットレジーム判定（OpenAI 使用））
- 運用ツール（.env ウィザード、設定バリデータ、Paper Trading 検証レポート生成）
- ロギング・プロセス優先度設定・DB 初期化ユーティリティ

主要機能一覧
-------------
- 実行:
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor をポーリングし、システム状態を永続化。MONITOR_POLL_INTERVAL により周期変更可能（デフォルト 60 秒）。
- 監視:
  - system_monitor, trade_monitor, risk_monitor による監視ログ記録・アラート判定
  - KillSwitch によるフラグファイル書き込みでエンジン停止
- ポートフォリオ構築:
  - 候補選定（スコア順）、等金額 / スコア加重、リスクベースの株数計算、セクターキャップ、レジーム乗数
- 研究:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB で prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI:
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、銘柄ごとに -1.0〜1.0 のスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して market_regime テーブルへ書込
- 運用ツール:
  - config_setup.py: 対話式に .env を作成/更新するウィザード
  - validate_config.py: 必須環境変数や config/*.yaml、DB パスなどの事前チェック CLI
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを出力

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（validate_config の YAML 検証を有効にするため）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使ってください:
   - pip install -r requirements.txt

4. 環境変数 (.env) 作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考にしてください）。
   - 自動ロード: kabusys.config はプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant, partial, never, reject）
- PAPER_TRADING_SQLITE_PATH: Paper 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（例: INFO）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存の kill.flag を自動クリアするか（"1" でクリア）

使い方
------
基本的な CLI / 実行例:

- .env を作成 / 更新（ウィザード）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）へ記録され、本番 DB と分離されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
      （単位: 秒。1 秒未満や 0 以下は無効 → デフォルト 60 秒にフォールバック）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（ライブラリ関数として使用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を与え、target_date（date オブジェクト）でスコアを生成・ai_scores テーブルへ書込
    - api_key を None にすると環境変数 OPENAI_API_KEY が使用されます
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ冪等書込します

停止 / Kill Switch / フラグファイル
- 手動で監視 / 実行を停止したい場合:
  - data/stop_requested.flag ファイルを作成すると run_monitoring / run_execution のループが検知して終了します（run_execution は起動前にもチェックします）。
- Kill Switch:
  - リスク条件（ドローダウン超過 等）を満たした場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は kill.flag の存在を参照して動作を止めるよう設計されています。
  - 本番で起動時に kill.flag を自動クリアするのは危険なのでデフォルトは無効。KILL_FLAG_CLEAR_ON_START=1 で自動クリアできますが、本番では 0 推奨。

ログ
- ログ出力は kabusys.utils.logging_setup.setup_logging で統一管理されます。
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用。

データベースと永続化
- DuckDB: 分析用（デフォルト data/kabusys.duckdb）
- SQLite (monitoring.db): 監視・注文履歴等（デフォルト data/monitoring.db）
- Paper Trading 用 SQLite は環境変数で分離（PAPER_TRADING_SQLITE_PATH）

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・ディレクトリ）
- kabusys/
  - __init__.py              — パッケージ定義（バージョン等）
  - config.py                — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 実行関連コンポーネント（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 / 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注・約定ログ監視（実装参照）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - monitoring_engine.py   — 複数モニタの統合ポーリング
    - kill_switch.py         — kill.flag 書込ロジック
    - alert_manager.py       —（アラート送信管理）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数・投下額計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュース → OpenAI スコアリング
    - regime_detector.py     — マクロ + MA 合成によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/                    — 実行時に利用するフラグや DB など（リポジトリに含めないこと）
  - logs/                    — ログ出力（実行時に自動作成）

補足 / 注意点
-------------
- .env は決してリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- OpenAI API を利用する機能を使う場合は API キーの管理に注意してください。テスト時はモック可能（コードにて呼び出し関数を差し替えられる設計）。
- run_execution / run_monitoring はプロセス優先度を high に設定しようとしますが、権限不足で失敗することがあります（warning ログに留まる）。
- validate_config は PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップします（警告が出ます）。
- Paper Trading を完全に本番と分離するため、KABUSYS_ENV=paper_trading 時は paper 用 SQLite に書き込みます。

ライセンス / 貢献
----------------
- （ここにプロジェクトのライセンスや貢献ガイドラインを追記してください）

以上が主要な利用方法と構成の概要です。さらに詳細な API ドキュメントやコンポーネント単位の使用方法が必要であれば、どのモジュールについての説明が欲しいかを教えてください。