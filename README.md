# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）を元にした概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買／バックテスト／リサーチを支援するモジュール群と、実行エンジン・監視エンジン・補助ツールを含むシステムです。主な機能は次のとおりです。

- 実行エンジン (ExecutionEngine)：発注・注文管理・リスク管理・リコンクシリエーション
- 監視エンジン (Monitoring)：システム稼働状況・注文状態・リスク監視、Kill Switch の生成
- ポートフォリオ構築モジュール：銘柄選定、重み付け、株数算出（丸め・上限考慮）
- リサーチ / ファクター計算：モメンタム・バリュー・ボラティリティ等の計算
- AI 補助：ニュース NLP によるセンチメントスコア、レジーム判定（OpenAIを利用）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、レポート生成等

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定管理
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
- 監視
  - monitoring/*: システム状態、トレードログ、リスク監視、Kill Switch、アラート連携など
  - monitoring_db.py: SQLite を用いた監視ログ永続化（マイグレーション対応）
- ポートフォリオ
  - portfolio/*: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- リサーチ
  - research/*: ファクター計算、特徴量探索、IC 計算、Zスコア正規化（data.stats から提供）
- AI
  - ai/news_nlp.py: raw_news から OpenAI 経由で銘柄別センチメントを生成し ai_scores に書き込む
  - ai/regime_detector.py: ETF MA とマクロニュースの LLM 評価を合成して market_regime を決定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB をサマリして PASS/FAIL 判定される検証レポートを生成

---

## セットアップ手順（開発環境）

前提
- Python 3.10+（型注釈に `X | Y` スタイルを使用しているため）
- 仮想環境を推奨（venv / poetry 等）

例（venv + pip）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - optional: pip install PyYAML  （validate_config の YAML 検証を有効にするため）

   注: requirements.txt が無い場合は上記を手動でインストールしてください。

3. ディレクトリ作成
   - data/ と logs/ を作成しておくと安全です（スクリプトが自動作成する箇所もありますが権限により失敗する場合あり）。
     - mkdir -p data logs

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を作成（本リポジトリに .env.example が無い場合は README の「環境変数」参照）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告もエラー扱い）: python -m kabusys.validate_config --strict

6. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定（ai モジュールが必要とする場合）
     - export OPENAI_API_KEY="sk-..."

---

## 主要環境変数（抜粋・デフォルト）

必須（validate_config による検証対象）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主な任意 / デフォルト
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

その他の設定は config_setup のウィザードまたは config/*.yaml（テンプレート）を参照してください。

---

## 使い方（起動・実行例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading に応じ動作分離）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され本番 DB と完全に分離されます。
    - ExecutionEngine は起動時に data/stop_requested.flag の存在をチェックします。flag があると起動を行いません。
    - 実行中に stop を送るには kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）や stop_requested.flag を利用してください。

- Monitoring 起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（有効な正の整数でない場合はデフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データの参照先は固定）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラム内呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="sk-...")
      - conn は duckdb.connect(...) の接続オブジェクト（DuckDBPyConnection）
      - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="sk-...")

- 停止 / Kill Switch
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（存在チェックで停止）。
  - run_* スクリプトはプロジェクト内の data/stop_requested.flag による外部停止要求を監視しています。

---

## ログ

- ログはデフォルトで stdout（コンソール）と日次ローテートされたファイルに出力されます（logs/<app_name>.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。ログディレクトリを変更するには LOG_DIR 環境変数を設定するか、setup_logging に引数を渡してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（詳細なファイル構成はリポジトリを参照してください）

---

## 注意点 / 運用上のノウハウ

- KABUSYS_ENV
  - development / paper_trading / live のいずれかを指定します。live モードは本番発注を行うため十分注意して設定してください。
- ペーパートレードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視コンポーネント（monitoring）は KABUSYS_ENV に関係なく本番の sqlite_path（SQLITE_PATH）を参照する点に注意してください。
- OpenAI など外部 API 呼び出しはネットワーク障害やレート制限に備えリトライ／フェイルセーフ（スコアを 0 にする等）を組み込んでいますが、本番稼働前に十分テストしてください。
- psutil によるプロセス優先度設定や CPU affinity は環境・権限に依存します。アクセス拒否が発生しても警告ログを出して処理継続します。
- データベース初期化は起動スクリプト側で行います（init_monitoring_db）。必要に応じて事前に data ディレクトリと DB ファイルのパーミッションを確認してください。

---

## よく使うコマンドまとめ

- .env 作成： python -m kabusys.config_setup
- 設定検証： python -m kabusys.validate_config
- Execution 起動： python -m kabusys.run_execution
- Monitoring 起動： MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート： python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

もし README に追加してほしい情報（例：各 config/*.yaml のテンプレート、より詳しい起動オプション、CI の設定例、テストの実行方法など）があれば教えてください。必要に応じて追記します。