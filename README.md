# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）

この README はリポジトリ内のコード（src/kabusys 以下）を基に作成しています。  
主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群と実行スクリプトを提供します。主な関心領域は以下です。

- Execution Engine：ブローカーへの発注管理、リスク管理、オーダーの調整（paper_trading モードあり）
- Monitoring：システム状態・注文状態・リスク監視、Kill Switch による停止信号
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：ニュースの自然言語処理（OpenAI）を用いたセンチメント評価 / レジーム判定
- Portfolio construction：銘柄選定、重み付け、ポジションサイズ計算
- ユーティリティ：設定管理、ログ設定、プロセス優先度制御、設定ウィザード／検証ツール
- 各種ツール：ペーパートレードの検証レポート生成など

設計方針として、データベースは DuckDB（分析用）と SQLite（監視・履歴）を使い分け、AI 呼び出しは外部 OpenAI API へ接続する実装になっています。多くの処理は「外部通信なしでも検証できる」設計を意識しています（research や portfolio モジュールは DB /メモリ演算のみ）。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env/.env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モード（MockBrokerClient を使用、専用 DB に分離）
  - リスク管理（RiskManager, Reconciler, OrderManager 等）

- Monitoring
  - System / Trade / Risk モニタ（periodic ポーリング）
  - Kill Switch（条件に応じて data/kill.flag を作成し Execution を停止）
  - monitoring DB（SQLite）への永続化（system_status, trade_logs, risk_logs, positions, dashboard）

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC（Information Coefficient）計算
  - 候補選択・重み付け・ポジションサイズ計算・セクター制約・レジーム乗数

- AI
  - ニュース NLP スコアリング（OpenAI を用いて ai_scores に書込）
  - 市場レジーム判定（ma200 とマクロニュース＋LLMを合成して market_regime に書込）

- ツール
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## 必要な依存パッケージ（代表）

環境によって追加で必要なパッケージがあります。最小限として次を推奨します：

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の内容検証に使用）
- sqlite3 は標準ライブラリで利用可能

インストール例（仮想環境推奨）：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。

2. .env を作成・設定
   - 推奨フロー:
     - 対話式ウィザードを使う: `python -m kabusys.config_setup`
     - 生成後、`python -m kabusys.validate_config` で検証
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード）
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知、任意）

3. データディレクトリ作成
   - デフォルトでは `data/` と `logs/` を使用します。
   - 実行スクリプトは必要に応じて自動作成しますが、権限等に注意してください。

4. DB の初期化
   - 起動スクリプト（run_monitoring/run_execution）が起動時に監視テーブルの初期化を行います（init_monitoring_db）。

---

## 使い方（主なコマンド）

- 設定ウィザード（.env を作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # --strict を付けると警告も失敗扱い
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV によって切り替え
  - ペーパートレード時は MockBrokerClient を使用し専用 DB（PAPER_TRADING_SQLITE_PATH）に記録
  ```
  python -m kabusys.run_execution
  ```

  実行時の挙動:
  - 起動時にプロセス優先度を "high" にセット
  - `data/stop_requested.flag` が存在すると起動をやめる／実行中は検出すると停止
  - エンジンは別スレッドで実行され、stop フラグを検知すると安全に停止します
  - 実行中は `data/execution.pid` に PID を書き込みます

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず `SQLITE_PATH`（本番 sqlite_path）を使用します（監視テーブルは共通）
  - 停止は `data/stop_requested.flag` を作成するか KeyboardInterrupt（Ctrl+C）

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連関数（プログラム内から呼び出す）
  - ニューススコア (ai_scores へ書き込む)
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定（market_regime に書き込み）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - いずれも OPENAI_API_KEY 環境変数にキーを設定すれば api_key 引数は不要です。

---

## 重要な動作上の注意点

- Monitoring は監視用の SQLite（SQLITE_PATH）を常に使用します。実行（Execution）側の DB と混同しないように注意してください（paper_trading 時のみ Execution は PAPER_TRADING_SQLITE_PATH を使う）。
- Kill Switch: リスク条件を満たすと monitoring 側が `data/kill.flag` を書き込み、Execution 側がそれを検出して停止する仕組みです。`KILL_FLAG_CLEAR_ON_START=1` を使用すると起動時に自動で kill.flag を削除します（本番では 0 を推奨）。
- 停止フラグ: `data/stop_requested.flag` を作ると run_execution/run_monitoring のループを正常終了させます。
- ログ: デフォルトで `logs/` に日次ローテートのログが保存されます。ディレクトリ作成に失敗するとコンソール出力のみになります。
- OpenAI API 呼び出しはネットワークエラーや 429 レート制限に対してリトライ実装がありますが、API キーの漏洩やコストに注意して下さい。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なパッケージとファイル配置の抜粋です（src/kabusys を基準）。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - config_setup.py          # .env 対話ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring 起動スクリプト
    - utils/
      - logging_setup.py       # ログ設定ユーティリティ
      - process_priority.py    # プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       # SQLite 永続化層
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
      - ...
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
      - __init__.py
    - data/                     # （リポジトリ直下）データファイル（.env でパス指定可）
    - tools/
      - paper_verification_report.py

ルートに `config/` ディレクトリ（system_config.yaml 等）があり、`validate_config.py` はこれらの YAML ファイルの存在とパース（PyYAML があれば）も検証します。

---

## よくある運用フロー（例）

1. 環境構築（仮想環境 + 依存インストール）
2. `python -m kabusys.config_setup` で .env を作成
3. `python -m kabusys.validate_config` で設定を確認
4. duckdb / sqlite のデータ準備（prices_daily などのテーブルは別途ロード）
5. Execution を起動（本番は適切な KABUSYS_ENV を設定）
   - `python -m kabusys.run_execution`
6. Monitoring を起動（別プロセス / サーバで）
   - `MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring`
7. AI スコアやレジーム判定はスケジュール実行（cron / Airflow 等）で定期的に呼ぶ

---

## 追加情報 / 開発者向けメモ

- ロギングはアプリ名単位（例: execution, monitoring）で logs/<app_name>.log に出力されます。
- `set_process_priority("high")` を起動直後に呼んでいるため、実行環境の権限により優先度設定が失敗する場合があります（警告が出ますが処理は継続します）。
- DuckDB 接続は分析用途に使われます。research モジュールは DuckDB 内の `prices_daily`, `raw_financials` 等のテーブルを参照します。
- テストを書く際のハックポイント:
  - AI 呼び出し周りは `_call_openai_api` の差し替え（mock）が可能な設計。
  - MonitoringEngine には `run_once()` があり単体テストで個別監視ロジックを呼べます。

---

もし README へ追加したい具体的な情報（コマンド例、環境変数の完全一覧、CI 用のセットアップ手順、データの初期ロード手順など）があれば教えてください。必要に応じて追記・整形します。