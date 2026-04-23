# KabuSys

日本株自動売買システムの Python コードベース向け README（日本語）。

この README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

注意: 本リポジトリは実際の発注（kabuステーション等）や外部 API（OpenAI / J-Quants 等）と連携する設計になっています。本番運用前に設定の確認・検証を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ／ツール群です。主な目的は以下です。

- データ取得・集計（DuckDB を用いた時系列・財務データ処理）
- ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- 実行エンジン（ExecutionEngine：ブローカーとのやり取り、発注管理、リスク制御）
- 監視（System/Trade/Risk のポーリング監視、Kill Switch）
- AI 補助（ニュースのセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証）

設計上のポイント:
- DuckDB / SQLite をローカル DB として使用（分析用と監視用を分離）
- 環境変数／.env で設定を管理（自動読み込み機構あり）
- Paper Trading（KABUSYS_ENV=paper_trading）向けに本番 DB とは分離した挙動をサポート
- OpenAI 呼び出しはリトライやバリデーションを組み込んだ堅牢な実装

---

## 機能一覧

- 設定管理
  - .env 対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading 用の切替（専用 SQLite に記録）
  - ブローカーファクトリ・リスク管理・注文管理一式
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - MonitoringEngine / run_monitoring.py による定期実行
  - kill.flag による外部停止（Kill Switch）
  - 監視データの永続化（SQLite）
- 研究・リサーチ
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索 / IC 計算
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベース割当、単元株丸め
  - セクター上限やレジーム乗数適用
- AI（OpenAI）連携
  - ニュースのセンチメント解析（gpt-4o-mini を想定）
  - レジーム判定（ETF MA + マクロニュース）
  - エラーハンドリング・リトライ・レスポンス検証を実装
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（ログの stdout + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

以下はローカル開発／試験的実行の手順（一般的な一例）です。

前提:
- Python 3.8+ を推奨（DuckDB / psutil / openai 等の要件に合わせて調整）
- git リポジトリをクローン済みであること

1. リポジトリをクローン / 移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 必要パッケージをインストール
   - 必要最低限（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（config 検証で YAML の解析を行う場合に任意）
   - pip 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合はそれを使用してください（本コードベースには明示的な requirements ファイルは含まれていません — プロジェクトに合わせて作成してください）。

4. 初期データディレクトリ作成
   - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成。最低限必要な環境変数（validate_config 参照）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - （必要に応じて）DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY 等

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

注意:
- config.py はプロジェクトルート（.git または pyproject.toml を起点）から .env を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行時は .env の値が優先され、環境変数で上書きできます。

---

## 使い方（主なコマンド・エントリポイント）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor をポーリング）
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 動作のポイント:
    - ログは logs/monitoring.log に日次ローテーションで出力
    - 監視は実行環境に関わらず本番の sqlite_path を使用して監視データを永続化
    - 停止フラグ: プロジェクトの data/stop_requested.flag を作成すると監視ループは終了

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて paper_trading 用 DB（デフォルト data/paper_trading.db）へ記録
  - python -m kabusys.run_execution
  - 停止フラグ:
    - data/stop_requested.flag がある場合は起動せず終了
    - run_execution は data/execution.pid に PID を書きます（設定により変更可能）
  - 注意: 実際に本番発注を行う場合は KABUSYS_ENV=live を使い、設定を厳重に確認してください

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）:
    - python -m kabusys.tools.paper_verification_report --db path/to/db

- AI 関連（プログラムから呼び出し）
  - ニュースのセンチメント評価:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - conn は DuckDB 接続オブジェクト
    - api_key を None にすると環境変数 OPENAI_API_KEY を利用
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ロギング・プロセス優先度
  - 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一ログを利用
  - 起動時に kabusys.utils.process_priority.set_process_priority("high") を呼んでいるため psutil による権限の制約で警告が出る場合があります（アクセス権限を確認してください）。

---

## 主要な環境変数（抜粋）

- 必須（validate_config でチェックされる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要な運用変数
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0 推奨）

---

## ディレクトリ構成（要約）

以下は src/kabusys 配下の主なファイル／モジュールと簡単な説明です。

- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL で間隔設定。

- run_execution.py
  - ExecutionEngine を起動するスクリプト。paper_trading モード時は MockBrokerClient を使用。

- config.py
  - Settings クラス：環境変数・.env の読み込み／検証を担当。自動 .env ロード機能あり。

- config_setup.py
  - .env を対話式で生成／更新するウィザード CLI。

- validate_config.py
  - 起動前に .env と config/*.yaml の簡易検証を行う CLI。

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- ai/
  - news_nlp.py: ニュースのセンチメントを OpenAI で判定して ai_scores に書き込む
  - regime_detector.py: 市場レジーム判定（ETF MA + マクロニュース + LLM）

- monitoring/
  - monitoring_db.py: SQLite のスキーマ初期化と永続レイヤ
  - system_monitor.py: システム状態（CPU/MEM/DISK/プロセス/データ鮮度）監視
  - trade_monitor.py: （trade 関連の監視 — ファイルにより詳細）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の生成／管理
  - monitoring_engine.py: 各 Monitor を一括してポーリング・アラート送信

- portfolio/
  - portfolio_builder.py: 候補選定・スコア並べ替え
  - position_sizing.py: 株数決定・aggregate cap ロジック
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- utils/
  - logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority.py: プラットフォーム差を吸収したプロセス優先度・CPU affinity 設定

- __init__.py / version 定義等

※ repository のルート構成は次のようになります（抜粋）:
- src/
  - kabusys/
    - ai/
    - monitoring/
    - portfolio/
    - research/
    - tools/
    - utils/
    - run_monitoring.py
    - run_execution.py
    - config.py
    - config_setup.py
    - validate_config.py
    - ...

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスが重大になり得ます。validate_config での検証を必ず行い、LINE などの通知設定も確認してください。
- kill.flag / stop_requested.flag / data/execution.pid 等のフラグファイルを用いてプロセス間の停止制御を行います。これらのファイルの場所は Settings で変更可能です。
- OpenAI や外部ブローカーのクレデンシャルは .env に秘匿して管理してください。.env は絶対に Git にコミットしないでください。
- psutil によるプロセス優先度変更や CPU affinity 設定は権限に依存します。権限不足時は警告が出て処理は継続しますが、期待する効果が得られない場合があります。
- DuckDB / SQLite のファイルは適切なバックアップ・アクセス制御を行ってください。

---

## 参考：よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視開始
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追記してほしい内容（例: requirements.txt、サンプル .env.example、CI 設定、より詳細なディレクトリツリーなど）があれば教えてください。必要に応じて具体的な .env の雛形や Docker / systemd の起動例も作成できます。