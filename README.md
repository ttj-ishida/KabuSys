# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群。  
このリポジトリは戦略・ポートフォリオ構築、注文実行、監視、研究および AI 補助機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ兼ランタイムです。主要機能は次のとおりです。

- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限等）
- 研究用モジュール（ファクター計算、IC 計算、統計サマリー）
- AI 補助モジュール（ニュースの NLP スコアリング、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 運用ツール（Paper Trading 検証レポート生成など）

設計上の注意点：
- 環境（KABUSYS_ENV）により挙動が変わります（development / paper_trading / live）。
- Paper Trading は本番 DB と分離された専用 SQLite を使用します。
- OpenAI 等の外部 API 呼び出しは環境変数でキーを指定します。API 失敗時はフェイルセーフで継続する設計です。

---

## 機能一覧

主な機能（抜粋）

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッドで実行、停止フラグ監視）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して data/paper_trading.db に記録
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視用 DB は環境に関係なく本番 sqlite_path を使用
- config_setup.py
  - .env を対話的に作成 / 更新するウィザード
- validate_config.py
  - .env と config/*.yaml の基本チェック（--strict オプションで警告をエラー扱い）
- tools/paper_verification_report.py
  - Paper Trading の成果・安定性指標を集計してレポート出力
- portfolio/*
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- research/*
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、IC/統計サマリー
- ai/*
  - news_nlp: ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector: マクロセンチメントと ETF MA を組み合わせて市場レジームを判定
- monitoring/*
  - monitoring_db: 監視用 SQLite スキーマと永続化 API
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch
- utils/*
  - logging_setup, process_priority（優先度 / CPU affinity 設定）など

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（Union 型 `X | Y` を使用しているため）
- Git リポジトリがプロジェクトルートとして認識されます（.env 自動ロード等で使用）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 追加で YAML 検証が必要なら: pip install PyYAML

   （本リポジトリに requirements.txt がない場合は上記を手動でインストールしてください）

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動で作成してください
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV の値: development / paper_trading / live

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データ / ログ ディレクトリ
   - デフォルトで data/ と logs/ を使用します（存在しない場合は自動作成される箇所がありますが、権限を確認してください）。

---

## 使い方

主要な起動 / 実行例：

- ExecutionEngine を起動する（デフォルト: KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定してください（.env または環境変数）。

- Monitoring を起動する（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒（不正値・0 以下はデフォルトにフォールバック）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key 未指定時は OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

運用上の注意:
- Kill Switch: KillSwitch は data/kill.flag を書き込みます。ExecutionEngine 側は data/stop_requested.flag や kill.flag を見て停止します（起動前に clear が必要な場合あり）。
- Paper Trading は data/paper_trading.db に記録され、本番監視 DB（data/monitoring.db）とは分離されます。
- ログ: logs/<app_name>.log に日次ローテーションで出力されます。LOG_LEVEL や LOG_DIR は環境変数で指定可能です。

---

## よく使う環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存先ディレクトリ
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（kill/stop 関連）

※ .env での設定が推奨。.env は絶対に Git 管理に含めないでください。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル / ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み込みロジック（.env 自動ロード機能含む）
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py
      - ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py
      - 市場レジーム判定（ETF MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
    - position_sizing.py
      - 株数決定（単元丸め等）
  - research/
    - factor_research.py
      - モメンタム/ボラティリティ/バリュー ファクター計算（DuckDB 利用）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー
  - monitoring/
    - monitoring_db.py
      - 監視用 SQLite スキーマと読み書き API
    - system_monitor.py
      - システム状態・データ鮮度チェック
    - trade_monitor.py
      - （注文関連の監視、コードベースに存在）
    - risk_monitor.py
      - ドローダウン / ポジション数監視
    - kill_switch.py
      - kill.flag の書き込みロジック
    - monitoring_engine.py
      - 各 Monitor を束ねたポーリングエンジン
  - utils/
    - logging_setup.py
      - 共通ロギング設定
    - process_priority.py
      - プロセス優先度・CPU affinity 設定

ルートに存在が想定される運用ファイル（実行時生成/使用）：
- data/
  - monitoring.db（SQLite, 監視ログ）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kill.flag / stop_requested.flag / execution.pid 等のフラグ・PID ファイル
- logs/
  - execution.log, monitoring.log 等

---

## 運用上の注意 / トラブルシューティング

- .env は機密情報を含むためリポジトリにコミットしないでください。
- KABUSYS_ENV=live は本番です。validate_config の警告をよく確認してから運用してください。
- OpenAI API を使う機能は API 使用量に注意してください。エラー時はフォールバックが入りますが、想定外の停止を防ぐため事前にテストを行ってください。
- run_monitoring は監視 DB に対して永続的に書き込みます。MONITOR_POLL_INTERVAL を短くしすぎると DB / ログが増大します。
- psutil を用いたプロセス優先度設定や CPU affinity は権限や OS に依存します。権限不足時は警告が出てスキップされます。

---

もし README に追加したい項目（例: 具体的な設定例、サンプル .env、API の詳細、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記・整備します。