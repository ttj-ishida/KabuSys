# KabuSys

日本株自動売買システムのライブラリ・起動スクリプト群です。  
本リポジトリは戦略設計（ファクター計算・ポートフォリオ構築）から、発注実行（ExecutionEngine）、監視（Monitoring）、AIを用いたニュース評価までを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- 「KabuSys」は日本株向けの自動売買システムを想定したコードベースです。
- 主な責務:
  - 市場データ（DuckDB の prices_daily 等）を用いたファクター計算・特徴量探索（research）
  - ポートフォリオ構築、リスク調整、ポジションサイズ算出（portfolio）
  - 発注ロジックと ExecutionEngine（execution） — paper_trading モードでは MockBrokerClient を利用
  - 監視・アラート・Kill Switch（monitoring）
  - ニュース NLP による銘柄別センチメント評価・レジーム判定（ai）
  - 各種ユーティリティ（logging / process priority など）
- 設定は .env（および .env.local）から読み込みます。自動読み込みはプロジェクトルート検出（.git / pyproject.toml）を基に行われます。

---

## 機能一覧

- 環境設定ウィザード（対話式）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: python -m kabusys.validate_config
- Execution エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db 等）に分離して記録
- Monitoring ポーリング起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - ニュースのセンチメント評価（OpenAI 使用）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 + マクロニュース）: kabusys.ai.regime_detector.score_regime
- Research モジュール: ファクター計算（momentum / volatility / value 等）・IC/相関解析
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ算出、セクターキャップ、レジーム乗数
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
- プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（コードで | 型アノテーション等を使用）
- システムに sqlite3 が利用可能（標準ライブラリ）
- 必要に応じて DuckDB バイナリがある環境

1. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の推奨パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt は本リポジトリに含まれていないため、環境に応じて上記をインストールしてください）

3. 環境変数設定（.env）
   - 対話式で .env を生成:
     - python -m kabusys.config_setup
   - 生成後、設定検証:
     - python -m kabusys.validate_config
     - --strict オプションで警告も失敗扱いにできます

4. ログ/データ用ディレクトリの確認
   - デフォルトで `data/` と `logs/` を使用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。
   - 実行スクリプトは必要なら自動的にディレクトリを作成しますが、権限等に注意してください。

5. OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時にキーを渡してください。

---

## 使い方

主要スクリプト（トップレベル実行モード）

- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（自動発注）
  - python -m kabusys.run_execution
  - 起動時に KABUSYS_ENV に応じて DB を選択:
    - live / development: settings.sqlite_path（デフォルト data/monitoring.db）
    - paper_trading: settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - 停止指示は data/stop_requested.flag を作成することで可能。PID ファイルは data/execution.pid（設定で変更可）。

- Monitoring を起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング秒数を上書き（例: MONITOR_POLL_INTERVAL=30）
  - Monitoring は設定にかかわらず本番 sqlite_path を使用して監視ログを残します
  - 停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL を出力します

- AI 関連（ライブラリ関数）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect）を受け取ります。api_key が None の場合は環境変数 OPENAI_API_KEY を参照するので事前に設定してください。

停止 / Kill Switch
- KillSwitch（監視側）は drawdown やポジション上限を検出した際に `data/kill.flag` を書いて ExecutionEngine に停止シグナルを送ります。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが、本番では 0 を推奨します。

ログ
- ログは stdout と日次ローテート（logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/`。

注意
- OpenAI を使う処理は API 失敗時にフェイルセーフとしてスキップ/デフォルト値を採る設計ですが、キーの漏洩に注意し `.env` を Git にコミットしないでください。
- .env の自動ロードはプロジェクトルートが検出できない場合スキップされます。CI 等では環境変数を明示的に渡してください。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（モニタリング/停止関連）

参照: src/kabusys/config.py（Settings クラス）

---

## ディレクトリ構成（簡易）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/                    — ExecutionEngine, ブローカーファクトリ等（詳細はリポジトリに依存）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (runtime)
    - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid
  - logs/ (runtime)
    - <app_name>.log 日次ローテーション

（上記はソースベースの主要ファイルを抜粋しています。詳細はソースを参照してください。）

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）での設定ミスは重大な影響を及ぼします。validate_config での検証・LINE 通知設定などを必ず確認してください。
- .env は絶対にリポジトリへコミットしないでください。
- OpenAI を利用する処理は外部 API に依存するため、レート制限・コスト管理を忘れずに行ってください。API エラーはリトライ・フェイルセーフ処理が組まれていますが、運用方針に応じて監視を強化してください。
- DuckDB / SQLite のファイルパスは .env で調整してください。paper_trading と本番 DB は分離する仕組みです。

---

必要であれば、README にサンプル .env テンプレート（.env.example）や起動/デバッグ手順、ExecutionEngine の詳細な起動フロー・API ドキュメントを追加します。どの情報を優先して追記しますか？