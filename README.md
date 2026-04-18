# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはローカル起動・設定、主要機能、使い方、ディレクトリ構成の概要を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / リサーチ基盤です。主な機能は次の通りです。

- 戦略（ファクター計算・特徴量探索）を行う Research コンポーネント（DuckDB を利用）
- ポートフォリオ構築（候補選定、重み付け、サイズ計算、セクター制限）
- ExecutionEngine：ブローカークライアント経由で発注（paper_trading をサポート）
- Monitoring：システム状態・注文状態・リスク監視、kill switch による停止
- AI モジュール：OpenAI を利用したニュースセンチメント（news_nlp）／レジーム判定（regime_detector）
- ユーティリティ：環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定、ツール類（検証レポート等）

設計方針の一部：
- DuckDB を分析用 DB、SQLite を監視・注文ログ用に使用
- 本番/ペーパートレードは環境変数 `KABUSYS_ENV` で分離
- .env を用いた設定管理（自動ロード機能あり）
- 外部 API 呼び出し（OpenAI など）は明示的にキーを与えて実行

---

## 機能一覧（抜粋）

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
- 設定検証 CLI（python -m kabusys.validate_config）で .env / config/*.yaml の事前チェック
- Execution 起動スクリプト（python -m kabusys.run_execution）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して paper DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリングで SystemMonitor 等を実行、停止フラグに応じて終了
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）
- Portfolio モジュール（選定、重み付け、サイズ計算、セクター制限、レジーム乗数）
- Research モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: ma200 とマクロ記事の LLM センチメントを組み合わせて日次レジームを判定
- tools.paper_verification_report: Paper Trading の検証レポート生成 CLI

---

## セットアップ手順

想定環境: Python 3.10+（DuckDB / psutil / openai 等の依存あり）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   ※requirements.txt は本リポジトリに含まれていない想定のため、代表的パッケージを例示します。
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - PyYAML は config/*.yaml のパース検証時に使用（任意）
   - openai は AI モジュール実行時に必要

4. .env の作成（推奨: ウィザード使用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants / kabuAPI のトークンなどを設定してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合（--strict）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認/作成  
   デフォルトで次のファイル/ディレクトリが想定されます:
   - data/kabusys.duckdb（DuckDB）
   - data/monitoring.db（監視用 SQLite）
   - data/paper_trading.db（paper_trading 用 SQLite、KABUSYS_ENV=paper_trading 時）
   - logs/（ログ出力）

   起動時に自動作成される場合が多いですが、権限等に注意してください。

備考:
- .env の自動読み込み: プロジェクトルートに .env / .env.local があれば Settings モジュールが起動時に読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。
- OpenAI を使う場合は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に明示的に API キーを渡してください。

---

## 使い方

ここでは代表的なコマンドと実行例を示します。

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 DB（デフォルト data/paper_trading.db）に記録
  - 実行中に data/stop_requested.flag が作成されると安全に停止します
  - 実行中の PID 管理は data/execution.pid を使用

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作:
  - Settings の sqlite_path（監視 DB）を使って接続・初期化
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可
  - data/stop_requested.flag が存在するとループを終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（例: ニューススコアリング）
  - コード経由で呼び出す:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026,4,11), api_key="sk-...")
    ```
  - 注意: OpenAI API キーが必須（引数または環境変数 OPENAI_API_KEY）

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  ```

停止・Kill Switch 等:
- 管理者が強制的に Execution を停止させたい場合は `data/kill.flag` を書き込む（KillSwitch が監視している場合、ExecutionEngine に停止シグナルを送ります）。
- 自動停止フラグ（run_execution/run_monitoring の終了用）: `data/stop_requested.flag`（存在するとループを終了）

ログ:
- ログはデフォルト `logs/` 配下に日次ローテーションで出力されます（例: logs/execution.log, logs/monitoring.log）。`LOG_DIR` 環境変数で変更可。
- ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で制御。

注意点:
- process_priority.set_process_priority を呼んでプロセス優先度を高く設定しますが、OS と権限により設定に失敗する場合があります（警告が出ます）。
- Paper trading と Live は DB が分離されるように設定されているため、本番環境では設定を厳重に確認してください（validate_config の live チェックなど参照）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR（ログディレクトリ）
- OPENAI_API_KEY（AI モジュール使用時）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔：秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の発注約定モード: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（start 時に kill.flag を自動クリアするか 1/0）

設定は .env / .env.local に保存し、config_setup ウィザードで簡単に作成可能です。

---

## ディレクトリ構成

リポジトリの主要な構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
    - __init__.py
  - ai/
    - news_nlp.py
      - raw_news を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py
      - マーケットレジーム判定と market_regime への書き込み
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル初期化と永続化 API
    - system_monitor.py
      - CPU/メモリ/ディスク／データ鮮度チェック
    - trade_monitor.py (ファイルはこの一覧に示されていませんが監視ロジックを想定)
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag 管理
    - monitoring_engine.py
      - モニタを束ねる実行ループ
  - execution/
    - execution_engine.py (実行エンジン本体; run_execution がこれを起動)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
      - 候補選定、等配分・スコア配分
    - position_sizing.py
      - 株数計算、ロット丸め、上限調整
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value などのファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン、IC、統計
  - utils/
    - logging_setup.py
      - 標準化されたログ出力設定（stdout + 日次ファイルローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

その他:
- data/（実行時に DB・フラグファイルが置かれる想定）
  - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid
- logs/（ログファイル）

---

## 開発・運用上の注意

- 本番（live）環境に切り替える場合は validate_config の警告に注意してください。LINE 通知や kill flag の扱いなど本番向けのガードが入っています。
- AI モジュールを使う際は OpenAI の利用制限や費用に注意。エラー・タイムアウトは内部でリトライ・フェイルセーフ処理がありますが、過負荷な連続実行は避けてください。
- process priority や CPU affinity の設定は OS 権限が必要な場合があります。設定失敗は警告を出して継続します。
- DB スキーマの簡単なマイグレーションロジック（monitoring_db.init_monitoring_db）を持ちますが、大規模なマイグレーションは注意が必要です。

---

README は以上です。必要であれば次を追加できます：
- 依存パッケージの正確な requirements.txt の候補
- 実行時のログ出力例
- 各モジュール（ExecutionEngine、OrderManager 等）の詳細 API ドキュメント

どの追加情報が必要か教えてください。