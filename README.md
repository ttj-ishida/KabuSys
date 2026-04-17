# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト群）。

このリポジトリはトレーディングエンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）などの主要機能を持つモジュール群で構成されています。

---

## プロジェクト概要

- 設計は「本番 DB と paper_trading を分離」「DB による永続化」「監視と自動停止（Kill Switch）」などの安全策を重視しています。
- DuckDB を用いた市場データ（prices_daily / raw_financials 等）の解析機能（ファクター計算、将来リターン、IC 計算 等）を提供します（研究用途）。
- OpenAI API（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定モジュールを含みます（API キー必須）。
- 監視機能は SQLite にログを残し、Streamlit ダッシュボードで可視化できます。

---

## 機能一覧

- Execution（発注エンジン）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの抽象化（本番・モック切替）
  - リコンシリエーション（再起動時の整合処理）
  - RiskManager / OrderManager / OrderRepository 等

- Monitoring（監視）
  - SystemMonitor, TradeMonitor, RiskMonitor（CPU・メモリ・ディスク・データ鮮度、滞留注文、ドローダウン等を監視）
  - KillSwitch（データ/kill.flag を書くことで ExecutionEngine を停止）
  - AlertManager（LINE Push 通知）
  - MonitoringEngine（ポーリングループ）
  - Streamlit ダッシュボード（監視結果表示）

- Portfolio（銘柄選定・配分）
  - 候補選定、等比率・スコア重み計算、ポジションサイズ計算、セクター上限・レジーム調整

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン / IC 計算 / 統計サマリー

- AI
  - ニュース NLP（raw_news を LLM へ送って銘柄ごとのスコアを ai_scores に保存）
  - レジーム判定（ETF MA200 とマクロニュースの LLM センチメントを合成）
  - いずれも OpenAI API キーが必要（OPENAI_API_KEY）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - その他ユーティリティ群

---

## セットアップ手順（概要）

1. Python 環境
   - 推奨: Python 3.10+（実装は型ヒントに 3.10 の構文を使う個所あり）
   - 仮想環境を作成して有効化することを推奨します。

2. 依存ライブラリのインストール（例）
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 主要パッケージ（最低限）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 実行環境に応じて追加パッケージが必要な場合があります。

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須（代表例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - 任意（代表例）:
     - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時必須）
     - KABUSYS_ENV — 実行モード（development / paper_trading / live） デフォルト: development
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant/partial/never/reject）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

4. データディレクトリの作成
   - `data/` ディレクトリを作成しておくと便利（DB・PID・フラグファイル格納）。

5. DB 初期化
   - 監視用 DB テーブルは起動時に `init_monitoring_db()` で自動作成・マイグレーションされます。特別な初期化は不要です。

---

## 使い方（代表的コマンド例）

- ExecutionEngine を起動
  - 本番相当:
    ```
    python -m kabusys.run_execution
    ```
    - 起動前に `KABUSYS_ENV` を `live`（または `.env` に記載）に設定してください。
  - Paper Trading（モックブローカー、別 DB）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading の場合、デフォルトで `data/paper_trading.db` に記録され、本番 DB と分離されます。

- Monitoring を起動
  - 監視ポーリングループを起動します:
    ```
    python -m kabusys.run_monitoring
    ```
    - ポーリング間隔を変更する場合:
      ```
      export MONITOR_POLL_INTERVAL=30
      python -m kabusys.run_monitoring
      ```
    - 監視は常に Settings.sqlite_path（本番設定）を使用します（環境に依らず監視 DB は本番用パスが使われる設計）。

- Streamlit ダッシュボード（監視ビュー）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `-- --db` の後に監視 DB パスを指定できます（デフォルト: data/monitoring.db）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- AI 機能（ニュース NLP / レジーム判定）の実行（例）
  - OpenAI API キーを環境変数にセット:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - Python スクリプト / インタラクティブで呼び出し:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10))  # raw_news があることが前提
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10))
    ```

- 停止・強制停止
  - 実行中の監視/実行エンジンはフラグファイルで制御できます:
    - data/stop_requested.flag — run_monitoring.py / run_execution.py が確認する「停止要求」フラグ（存在するとループを終了）
    - data/kill.flag — KillSwitch が書き込むファイル（ExecutionEngine に停止を指示するトリガー）
  - KillSwitch はリスク条件（ドローダウン / ポジション上限）で flag を書きます。

---

## 重要な設計点 / 注意事項

- .env 読み込み
  - プロジェクトルート（.git または pyproject.toml がある場所）を自動検出して `.env` / `.env.local` をロードします。
  - OS の環境変数は保護され、.env.local の override は OS 環境変数を上書きしません（ただし override=True の場合は OS 環境変数以外を上書きします）。
- 環境切り替え（KABUSYS_ENV）
  - 有効値: development / paper_trading / live
  - paper_trading はモックブローカーと専用 SQLite DB を使い、本番 DB と完全分離します。
- 監視 DB の初期化とマイグレーションは init_monitoring_db で行われます。既存テーブルにカラムがない場合は ALTER TABLE で追加します。
- AI モジュールは OpenAI API 呼び出しを含みます。API 利用に伴うコストやレート制限に注意してください。失敗時のフェイルセーフ実装（スコアを 0 にする等）がありますが、API キー未設定では例外が発生します。
- process priority / CPU affinity は psutil を使って設定します。権限不足や未対応 OS の場合は警告でスキップします。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ローダー、Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py (参照実装あり)
    - order_record.py (参照実装あり)
    - broker_factory.py, broker_api.py (抽象化)
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB データベース)
    - execution.pid, stop_requested.flag, kill.flag
  - utils/
    - process_priority.py

（上はコードベースからの抜粋です。実際は他モジュール・補助ファイルが存在する可能性があります）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API
- OPENAI_API_KEY — OpenAI API キー（AI 機能用）
- KABUSYS_ENV — execution モード（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading の SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル

---

## 開発者向けメモ

- 各モジュールは副作用を抑え、明示的な接続・依存注入（duckdb_conn, sqlite_conn, broker 等）を採っています。ユニットテストが容易な構造です。
- OpenAI 呼び出し部分にはリトライ・バックオフ・レスポンス検証ロジックがあります。テスト時は該当関数をモックしてください（例: news_nlp._call_openai_api）。
- Monitoring の停止/強制停止はファイルベースのフラグ（stop_requested.flag, kill.flag）で容易に行えます。CI やステージングでの自動停止テストがしやすい設計です。

---

何か特定の機能（例: ExecutionEngine の起動オプション、OrderRepository のスキーマ、DuckDB のテーブル構造等）についてさらに詳細な README を作成したい場合は、追加で対象ファイルや出力フォーマットの要望を教えてください。