# KabuSys

日本株向け自動売買システムのモジュール群。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、実行エンジン、監視（Monitoring）やニュースNLP / レジーム判定などを含む軽量なフレームワークです。

---

## 概要

KabuSys は以下の主要機能を持つ Python パッケージ群です。

- DuckDB / SQLite を用いたデータ処理・永続化
- ファクター計算（Momentum / Volatility / Value など）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 実行エンジン（Broker 抽象化・Order 管理・再起動時のリコンシリエーション）
- 監視（システム状態・注文滞留・リスク監視）、LINE 通知、Streamlit ダッシュボード
- Paper Trading 支援（mock broker、専用 DB）
- AI 模組（OpenAI を使ったニュースセンチメント、レジーム判定）
- 検証ツール（Paper Trading 検証レポート等）

設計方針として、ルックアヘッドバイアスを避ける、部分失敗時にデータ破壊を最小化する、外部 API 呼び出しはフェイルセーフにする（失敗時はフォールバック）といった運用を意識しています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local から環境変数を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - Settings クラス経由で安全にアクセス
- 実行（Execution）
  - ExecutionEngine（broker 抽象化）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期処理）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）：MockBrokerClient を使い data/paper_trading.db に記録
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/DISK／プロセス PID／データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイル data/kill.flag による停止シグナル）
  - AlertManager（LINE Push API 経由で通知）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め・利用可能資金に応じたスケーリング等）
- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC 計算、統計サマリー
- AI 関連
  - ニュース NLU（OpenAI を利用して銘柄別センチメントを ai_scores に登録）
  - レジーム判定（ETF MA とマクロニュースのセンチメントを合成）
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力

---

## セットアップ手順（簡易）

※ 実行環境や追加の依存がある場合は適宜調整してください。

1. リポジトリをクローン

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化（推奨: Python 3.9+）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   （プロジェクトに requirements.txt がある想定での例。なければ下記の主要パッケージを個別にインストールしてください）
   ```
   pip install -r requirements.txt
   ```

   主要な依存例:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例（requirements.txt が無い場合）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. データディレクトリを作成（必要に応じて）

   ```
   mkdir -p data
   ```

5. 環境変数を設定（.env / .env.local をプロジェクトルートに置くことが可能。自動ロードはデフォルトで有効）
   - 必須（実行する機能による）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - よく使う設定:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB path, default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper trading の約定振る舞い
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60 秒）

   例 (.env):
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   ```

---

## 使い方（主要な実行コマンド）

- ExecutionEngine を起動（実際のブローカー or mock。環境 KABUSYS_ENV により動作が切り替わります）:

  - 本番 / 開発モード（デフォルト）:
    ```
    python -m kabusys.run_execution
    ```

  - Paper Trading（Mock Broker、専用 DB に記録）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

  - 注意: ExecutionEngine 起動時は Settings.kill_flag_clear_on_start が 1 の場合に kill.flag をクリアします。PID ファイル（Settings.pid_file_path）を利用してプロセスの存在確認を行います。

- Monitoring（ポーリングループ）を起動:

  ```
  python -m kabusys.run_monitoring
  ```

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- Streamlit ダッシュボードを起動（監視 DB の可視化）:

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（コマンドライン）:

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - オプション `--db PATH` で SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も利用可能）。

- AI / レジーム関連（ライブラリ API）:
  - ニュースセンチメントスコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect）を引数に取ります。API キーは引数か OPENAI_API_KEY 環境変数で指定します。

- ライブラリ利用（リサーチ等）:
  - 例: calc_momentum を使う
    ```
    from kabusys.research import calc_momentum
    res = calc_momentum(duckdb_conn, date(2026, 4, 1))
    ```

---

## 重要な環境変数一覧（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の fill 挙動（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視の閾値）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）

設定は .env / .env.local に記述可能。OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上の注意

- Monitoring はデフォルトで本番の sqlite_path を使用します。paper_trading モードで分離したい場合は PAPER_TRADING_SQLITE_PATH を使用してください。
- 実行エンジンは PID ファイル（Settings.pid_file_path）でプロセスの存在を管理します。古い PID ファイルが残っていると stale PID 扱いとなり削除されます。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。kill.flag の存在は ExecutionEngine 側でチェックする運用を想定しています。
- OpenAI 呼び出しはネットワークエラーや 429 等に対して指数バックオフリトライを行いますが、リトライ上限を超えた場合はフェイルセーフ（スコアを 0 やスキップ）して処理を継続します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリングスクリプト
  - ai/
    - news_nlp.py                       — ニュースセンチメント（OpenAI）
    - regime_detector.py                — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py                  — SQLite 永続化層（monitoring DB）
    - system_monitor.py                 — システム / データ鮮度監視
    - trade_monitor.py                  — 注文滞留・約定異常検出
    - risk_monitor.py                   — ドローダウン / ポジション上限監視
    - kill_switch.py                     — kill.flag 管理
    - alert_manager.py                  — LINE 通知ラッパー
    - monitoring_engine.py              — 各 Monitor を束ねる
    - streamlit_dashboard.py            — Streamlit ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - ... (Broker 抽象など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py                — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - tools/
    - paper_verification_report.py       — Paper Trading 検証レポート CLI
    - __init__.py

（上記はコードベース内の主要モジュール構造の抜粋です）

---

## 開発・拡張のヒント

- DuckDB/SQLite テーブルスキーマは各モジュールに従い作成されます。monitoring 用のテーブルは init_monitoring_db() で作成・マイグレーションされます。
- AI 周りの関数は API キーを引数で渡せるよう設計されており、ユニットテスト時は呼び出し関数をモックして外部依存を切ることを推奨します。
- process_priority と CPU affinity はプラットフォーム差分を吸収するユーティリティが用意されています（psutil を利用）。
- Paper Trading 用 DB は実運用 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

---

必要であれば以下を追加で作成します:
- requirements.txt の推奨依存リスト
- .env.example テンプレート
- 起動 / systemd ユニットのサンプル
- より詳細な API ドキュメント（各モジュールの例・関数シグネチャ）