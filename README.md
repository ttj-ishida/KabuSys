# KabuSys

日本株向け自動売買システム（ライブラリ兼実行プログラム）。  
このリポジトリはトレーディング実行エンジン、監視（Monitoring）機能、ファクター研究・ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。

主な設計方針：
- DuckDB / SQLite をデータ層として利用（履歴データは DuckDB、監視ログ等は SQLite）
- 環境変数/.env による設定管理（自動読み込み機構あり）
- Paper trading（検証用）と Live（本番）を分離して運用可能
- OpenAI（gpt-4o-mini）を用いたニュース NLP／レジーム判定機能を備える（オプション）

---

## 機能一覧

- 実行（Execution）
  - 注文作成・送信・状態管理（OrderManager、OrderRepository 等）
  - 再起動・クラッシュ後のリコンシリエーション（Reconciler）
  - Paper trading モード（Mock ブローカー & 別 SQLite DB）

- 監視（Monitoring）
  - システム状態監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件を満たしたら flag ファイルを書き、ExecutionEngine を停止させる）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 研究・データ処理（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分／スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（position sizing）: 単元株丸め、aggregate cap のスケーリング等

- AI（任意）
  - News NLP（OpenAI でニュースを解析して銘柄ごとのスコアを ai_scores テーブルへ）
  - Regime Detector（ETF + マクロニュースを組合せて market_regime を判定）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - DB 初期化ロジック（監視用テーブル自動作成・マイグレーション）

---

## 必要条件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)

例:
```
pip install duckdb psutil requests openai streamlit
```

（プロジェクトによっては requirements.txt を用意している場合があります。それが無ければ上記をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 設定（環境変数 / .env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - PAPER_FILL_MODE: paper_trading 時の約定モード ("instant" | "partial" | "never" | "reject")
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL 等

   - 例 (.env):
     ```
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=yourpassword
     JQUANTS_REFRESH_TOKEN=...
     ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

注: 監視用 DB テーブルはスクリプト起動時に自動で初期化（init_monitoring_db）されます。

---

## 使い方

- ExecutionEngine を起動（デフォルト: Settings に従う）
  - 本番・paper_trading を切り替えるには KABUSYS_ENV を設定
  ```
  # paper_trading 例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - Live 運用:
  ```
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```

- Monitoring（ポーリング）を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  ```
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  （監視 DB を読み取り専用 URI で開くため、`--db` 引数でパスを指定できます）

- Paper Trading 検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  `--db` で DB パスを指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を利用します。

- AI 処理（プログラムから利用）
  - ニューススコア付与:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

- 設定や動作上のポイント
  - Paper trading は本番 DB と完全に分離され、デフォルトで data/paper_trading.db を使用します。
  - run_execution/run_monitoring 実行時にプロセス優先度が "high" に設定されます（プラットフォームの制約により設定できない場合は警告）。
  - Execution 側を停止させたい場合は KillSwitch により data/kill.flag を作成します（Monitoring 側が条件を満たすと書き込む）。
  - MONITOR_POLL_INTERVAL が不正な値（0 以下など）の場合はデフォルトにフォールバックします。

---

## 主要コンポーネント（ファイル／モジュールの説明）

- kabusys/config.py
  - 環境変数/.env の読み込み・検証を行う Settings クラス。自動でプロジェクトルートの .env/.env.local を読み込む（無効化可）。

- kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じてブローカークライアントや DB を分離して起動する。

- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔制御。

- kabusys/monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化（テーブル作成・CRUD ユーティリティ）
  - system_monitor.py: CPU/メモリ/ディスクやデータ鮮度、PID ファイルチェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: flag ファイルの書き込み・評価
  - alert_manager.py: LINE API による通知
  - monitoring_engine.py: これらを束ねてポーリング実行
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- kabusys/execution/
  - order_manager.py, reconciler.py, ... : 注文処理、再同期、リスク管理など（ExecutionEngine 本体は別ファイル／モジュールに存在）

- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定、重み付け、ポジション量の決定、セクターキャップ、レジーム乗数

- kabusys/research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン、IC 計算、ファクター統計

- kabusys/ai/
  - news_nlp.py: raw_news を集約し OpenAI に投げて銘柄別センチメントを ai_scores へ格納
  - regime_detector.py: ETF の MA 乖離 + マクロニュースセンチメントを合成して market_regime を作成

- kabusys/tools/
  - paper_verification_report.py: Paper Trading の検証レポートを標準出力に生成

- kabusys/utils/
  - process_priority.py: プロセス優先度、CPU affinity 設定ユーティリティ

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    run_execution.py
    run_monitoring.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ...（その他実行関連モジュール）
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    tools/
      paper_verification_report.py
      __init__.py
    utils/
      process_priority.py
      __init__.py

（DuckDB / SQLite データファイルは data/ 配下に置くことを想定）

---

## 環境変数の主要一覧（抜粋）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

詳しくは kabusys/config.py の Settings を参照してください（バリデーション・デフォルト値が定義されています）。

---

## 運用上の注意

- Paper trading は本番 DB と完全に分離しているため、本番資金に影響しません。Paper モードでの DB は PAPER_TRADING_SQLITE_PATH で指定できます。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0 で継続）を実装していますが、API コスト・レート制限に注意してください。
- Monitoring は定期的に system_status / risk_logs / trade_logs 等を記録します。ディスク容量や DB のバックアップ運用を検討してください。
- run_* スクリプトはプロセス優先度設定を試みますが、環境（OS、権限）により設定できない場合はログに警告を出します。

---

この README はコードベースの主要なポイントをまとめたものです。各モジュールの詳細な使用方法・パラメータは該当するソース（src/kabusys 以下）内の docstring を参照してください。必要であれば README を英語版やさらに詳しい運用ガイドに拡張できます。