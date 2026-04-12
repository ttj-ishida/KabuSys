# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を行う小規模なシステムです。  
このリポジトリには注文実行ロジック、ポートフォリオ構築、ファクター計算、ニュース NLP を用いたセンチメント評価、稼働監視（Monitoring）や運用補助ツールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 注文作成 → ブローカー送信 → 状態管理 → リコンシリエーション（再起動/クラッシュ復旧）を行う ExecutionEngine。
- ポートフォリオ構築（候補選定・重み計算・株数算出・セクター制限など）の純粋関数群。
- DuckDB を用いたリサーチ用ファクター計算モジュール（モメンタム、ボラティリティ、バリュー等）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント集約（ai.news_nlp）と市場レジーム判定（ai.regime_detector）。
- SQLite を使った監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）と監視エンジン（MonitoringEngine）。
- LINE API によるアラート送信機能と Streamlit ダッシュボード。
- Paper Trading モード（本番 DB と分離）および検証レポート生成ツール。

---

## 主な機能一覧

- Execution
  - 注文生成、送信、状態同期、再起動時のリコンシリエーション
  - リスク管理（ポジション上限、利用率、ドローダウン監視）
  - Paper Trading モード（ブローカーはモック、DB は data/paper_trading.db に分離）
- Monitoring
  - システムリソース監視（CPU/Memory/Disk）とデータ鮮度チェック
  - 注文滞留・約定異常価格の検出
  - Kill Switch（データベース上の条件に応じて ExecutionEngine 停止フラグを書き込む）
  - LINE による一方向アラート
  - Streamlit ダッシュボード（監視状況の可視化）
- Research / Tools
  - ファクター計算（mom, vol, value 等）
  - 特徴量探索・IC 計算
  - ニュース NLP による銘柄センチメント算出（ai_scores テーブルへ書込）
  - Paper Trading 検証レポート生成スクリプト
- ユーティリティ
  - 環境変数ローダ（.env / .env.local 自動読み込み）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 要件

- Python 3.10+（typing の | ユニオン表記等を使用）
- 主な依存（例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード起動時)
  - openai (ai モジュール使用時)
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI / LINE を使う場合）

requirements.txt は本リポジトリに含まれていないため、上記パッケージを適宜インストールしてください。

例:
```bash
python -m venv .env
source .env/bin/activate
pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成してパッケージをインストール（上記参照）

3. 環境変数の準備
   - プロジェクトルートに `.env` や `.env.local` を置けます（自動読み込みされます）。
   - 必須（実行内容に応じて）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API を使用する場合）
     - KABU_API_PASSWORD（kabuステーション API）
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - その他主要な環境変数（任意/デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE アラート）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - MONITOR_POLL_INTERVAL（監視ループ間隔、秒。デフォルト: 60）
   - .env の記述例:
     ```
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=*****
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```

4. データディレクトリの作成
   ```bash
   mkdir -p data
   # duckdb / sqlite は実行時にファイルを作成します
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番は KABUSYS_ENV に応じて動作）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring（SystemMonitor のポーリングループ）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視 DB を書きます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 引数 --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- Streamlit ダッシュボード起動（監視 DB を指定）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

## 環境変数・設定（主なもの）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが重要）
  - paper_trading: ブローカーをモックにして paper_trading 用 DB に書き込む
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH: Execution 停止監視に使用するファイルパス

---

## 動作上の注意・設計上のポイント

- Monitoring の DB（監視ログ）は init_monitoring_db() により必要なテーブルを冪等に生成します。
- Paper Trading は本番 DB とデータを分離する設計になっており、誤って本番に書き込むリスクを低減しています。
- OpenAI を呼ぶ箇所（news_nlp, regime_detector）はリトライや失敗時のフォールバックを実装しており、API 失敗時には安全側（スコア 0 等）で継続します。
- プロセス優先度設定（set_process_priority）は psutil を用いて OS ごとの差分を吸収します。setting 高優先度は起動直後に実行されます。
- Kill Switch は監視で条件が満たされた場合に `data/kill.flag` を作成し ExecutionEngine に停止シグナルを送ります（Execution 側でそのフラグを監視する想定）。
- テストや CI では環境自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使えます。

---

## ディレクトリ構成

ソースは `src/kabusys` に配置されています。主なファイル群:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env ローダ、Settings クラス
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
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
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 order_repository / broker_factory 等は本コードベースに依存)
  - data/ (想定実行時に使用する DB ファイルを置くディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

（上記は抜粋です。実際の実装ファイルはリポジトリ内を参照してください）

ツール / モジュールの責務は各ファイルの docstring に詳細があります。実行時の挙動やリスク制御のロジックはコメントで多く説明されていますので、変更する場合は docstring を確認してください。

---

## 開発・テスト時のヒント

- OpenAI 呼び出しはユニットテストではモック可能です（内部で _call_openai_api を patch する設計）。
- DuckDB はローカルファイルで高速にテーブル操作できるため、研究モジュールの単体実行に便利です。
- MonitoringDB のマイグレーションは起動時に自動で行われ（ALTER TABLE ADD COLUMN など）、互換性が考慮されています。
- process priority / cpu affinity の設定は OS と権限に依存するため、権限不足時は警告を出してスキップします。

---

必要であれば、README に依存パッケージの具体的な requirements.txt、サンプル .env.example、あるいは主要フローのシーケンス図／ユースケース別実行手順（本番、paper_trading、ローカル開発）を追記します。どれを追加しましょうか？