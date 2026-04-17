# KabuSys

日本株向けの自動売買システム（モジュール群）のリポジトリです。  
この README はリポジトリ内の主要コンポーネントと利用方法（ローカル実行 / ペーパートレード検証 / 監視）をまとめたものです。

概要・機能・セットアップ・使い方・ディレクトリ構成を日本語で記載します。

---

## プロジェクト概要

KabuSys は日本株に対する自動売買システムのコアライブラリ群です。  
主な機能は次のとおりです。

- 注文実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視（Monitoring）: システム状態、注文の滞留や約定異常、ドローダウン監視、Kill Switch
- ポートフォリオ構築（選定・配分・リスク調整・ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量解析、IC算出）
- AI 補助（ニュースセンチメントによるスコアリング・市場レジーム判定: OpenAI を利用）
- ペーパートレード用の分離された DB と Mock ブローカー
- 各種ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

設計方針として、データ処理（DuckDB）と監視ログ（SQLite）は分離されており、本番の発注系とペーパートレードは明確に分離されています。

---

## 主な機能一覧

- Execution（実行）
  - 実際のブローカークライアントまたは MockBrokerClient を用いた発注処理
  - RiskManager によるリスク制御（最大ポジション比率、資金利用率、ドローダウンなど）
  - Reconciler による注文とブローカー状態の突合せ

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウンや保有銘柄数上限の監視、ダッシュボード更新
  - KillSwitch: 危険時に data/kill.flag を作成して ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（設定があれば）

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順）、等金額 / スコア重み / リスクベース配分
  - セクター上限適用、レジーム乗数（bull/neutral/bear）

- Research（研究・分析）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン、IC（Information Coefficient）や統計サマリ
  - DuckDB を利用した SQL ベースの計算

- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースのセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF ma200 による市場レジーム判定（market_regime へ書込）
  - OpenAI API 呼び出しはリトライ・バックオフや結果バリデーションあり

- ツール
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（ローカル）

以下はローカルで動かすための一般的な手順例です。実際の依存は利用する機能により変わります（OpenAI を使う場合は openai、DB 操作は duckdb、システム情報は psutil など）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）
   - 最低限（推奨）:
     ```
     pip install duckdb psutil requests openai
     ```
   - 設定ファイル YAML チェックを使う場合:
     ```
     pip install pyyaml
     ```
   - テストや追加機能に応じて適宜インストールしてください。

   （本リポジトリに requirements.txt があればそれを使ってください。）

4. 環境変数の準備
   - 対話ウィザードで .env を生成するのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション / よく使う変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG|INFO|...）
     - PAPER_FILL_MODE（instant|partial|never|reject）

   サンプル .env（config_setup で自動生成されます）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   ```

5. データディレクトリの準備（必要時）
   ```
   mkdir -p data
   ```

6. 初回起動前の検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

以下は主要な実行・ユーティリティの使い方です。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（実行エンジン）を起動
  - 標準:
    ```
    python -m kabusys.run_execution
    ```
  - 動作環境:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し、DB は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。
    - KABUSYS_ENV=live の場合は本番設定に従ってブローカーへ発注します（十分注意してください）。

  - 起動時処理:
    - プロセス優先度を "high" に設定しようとします（psutil が権限を要求する場合あり、失敗しても継続します）。
    - stop フラグ（data/stop_requested.flag）が存在すると起動しません。
    - 実行中に stop フラグを作るとエンジンを停止します。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定できます（デフォルト 60）。
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH を使用できます。

- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング:
    ```python
    from kabusys.ai import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, datetime.date(2026, 4, 11), api_key="sk-...")
    print("scored:", n)
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, datetime.date(2026, 4, 11), api_key="sk-...")
    ```

- 停止・Kill Switch
  - 監視ループ / 実行エンジンは以下のフラグファイルを参照します:
    - data/stop_requested.flag: run_monitoring.py / run_execution.py はこれをチェックしてループを終了または起動を抑止します。
    - KillSwitch（監視モジュール） は危険時に data/kill.flag を書き込み、ExecutionEngine の停止をトリガーします。
  - 実行中に手動で停止したい場合は `data/stop_requested.flag` を作成してください（ファイル内容は任意）。

---

## 設定（主な環境変数）

- 必須（主に .env で設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- データベース
  - DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）

- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp, regime_detector など）

- その他
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用）
  - PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

注意: .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。

---

## 実装上の注意点 / トラブルシュート

- 設定不足やパラメータ値の不正は `python -m kabusys.validate_config` で検出できます。
- OpenAI API を利用する機能は API キーが未設定だと ValueError を投げます（score_news, score_regime）。
- psutil による優先度変更や CPU affinity 設定は権限不足で失敗することがありますが、ログに警告を出して処理は継続します。
- DuckDB / SQLite のパスに指定したディレクトリが存在しない場合、validate_config は警告を出しますが、起動時に自動作成されるケースがあります。
- monitoring_db.init_monitoring_db は冪等であり、起動時に必要なテーブルとカラム（マイグレーションを含む）を作成します。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールの一覧です（抜粋）。実際のソースは `src/kabusys` 以下にあります。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/              — Execution 系（OrderRepository など）※一部ファイルはここに存在
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

（上記はリポジトリ内の主要ファイルを抜粋したものです。さらに細かい実装は各サブモジュール内をご参照ください。）

---

## 開発・拡張メモ

- ペーパートレードは本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 周りは OpenAI の JSON mode を利用し、レスポンスの堅牢なバリデーションとリトライを実装済みです。
- DuckDB を用い SQL と Python を組み合わせてファクター計算を行う設計のため、大規模データの分析に適しています。
- 監視機能は監査・アラート・Kill Switch の 3 つを柱に実装されており、本番運用時の安全弁を提供します。

---

必要に応じて README を追記します（例: 実行エンジンの設定詳細、OrderRepository/OrderManager の API 仕様、テストの実行方法など）。追加で欲しいセクションがあれば指定してください。