# KabuSys

日本株向け自動売買システム（軽量ディレクトリ構成・モジュール化）。  
このリポジトリは以下の主要機能を提供します：戦略用のファクター計算・研究モジュール、ポートフォリオ構築（選定・配分・株数計算）、実行（ExecutionEngine／ブローカー連携）、監視（MonitoringEngine・アラート・Kill Switch）および AI 補助（ニュース NLP、レジーム判定）など。

---

## プロジェクト概要

- 目的：日本株の自動売買を安全に運用するための基本コンポーネント群を提供する（シグナル処理・発注・リスク管理・監視・レポーティング）。
- 設計方針：
  - 各機能は責務を分離（pure functions / DB 層 / 外部 API 呼び出しは分離）。
  - Paper Trading と Live を環境で切り替え可能（DB とブローカーは分離）。
  - ルックアヘッドバイアスを防ぐ設計。LLM 呼び出し時も日付参照に注意。
  - フェイルセーフ（API失敗や例外時にシステム全体を停止させない設計）。

---

## 機能一覧

- Execution（発注）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカーファクトリ（MockBroker による paper_trading 対応）
  - OrderManager / OrderRepository / Reconciler（起動時の自動復旧）
  - RiskManager（ポジション・利用率などの制限）
- Monitoring（監視）
  - SystemMonitor：プロセス生存、CPU/メモリ/Disk、データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - MonitoringEngine：複数モニタをまとめてポーリング
  - AlertManager：LINE による一方向プッシュ通知
  - KillSwitch：flag ファイルで ExecutionEngine 停止を指示
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア加重、リスクベースの株数計算、セクターキャップ、レジーム乗数
- Research（研究・因子）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計要約
- AI（OpenAI を用いた機能）
  - news_nlp.score_news：ニュース記事の銘柄別センチメントを LLM で算出して ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースセンチメントを合成してレジーム判定・DB 書込
- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
- 設定・ユーティリティ
  - Settings（.env ファイル自動読み込み・環境変数管理）
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - Monitoring DB 初期化（init_monitoring_db）

---

## 前提 / 必要環境

- Python 3.9+（typing の記述スタイルなどから推奨）
- 必要な主な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
- SQLite（標準ライブラリで利用可能）
- ネットワークアクセス（ブローカー API / OpenAI / LINE API 利用時）

（実際の依存関係はプロジェクトの requirements.txt または pyproject.toml を参照してください。）

推奨インストール例:
```
pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt   # 存在する場合
   # または最低限
   pip install duckdb psutil requests streamlit openai
   ```

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` があれば自動で読み込まれます（ただし OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 代表的な環境変数（必須または重要）:
     - JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV : environment（development / paper_trading / live） — デフォルト development
     - PAPER_FILL_MODE : paper_trading の注文充足モード（instant / partial / never / reject）
     - PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH : DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用
     - PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL など

   サンプル .env（最小例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方

以下は代表的な起動方法・コマンド例です。

- ExecutionEngine を起動（通常 / Paper Trading 切替）
  - 本番モード:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - Paper Trading（MockBroker を使い、DB を data/paper_trading.db に記録）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

- Monitoring を起動（ポーリング）
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード (監視 DB の可視化)
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポートの生成ツール
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（コードから呼び出す）
  - ニューススコアリング:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

注:
- run_execution/run_monitoring では起動時にプロセス優先度を high に設定しようとします（set_process_priority）。権限がない場合は警告が出てスキップされます。
- Paper Trading の場合、発注は MockBrokerClient を使い、本番 DB と分離して data/paper_trading.db に記録されます。

---

## 監視（Monitoring）に関する注意点

- monitoring は Settings にかかわらず「本番 sqlite_path（data/monitoring.db）」を使用します（監視ログは一元で管理）。
- init_monitoring_db(conn) は冪等で DB スキーマを作成し、必要に応じて簡易マイグレーション（列追加）を行います。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側が kill.flag の存在を検出して停止する設計が前提です。
- AlertManager は LINE の channel access token / user id が未設定の場合は送信をスキップします。クールダウン機構付き。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — Settings（.env 自動読み込み / 環境変数取得）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースから銘柄別センチメントを算出（OpenAI）
    - regime_detector.py — マクロ + MA に基づく市場レジーム判定（OpenAI optional）
  - monitoring/
    - monitoring_db.py — SQLite による監視テーブル / MonitoringDB
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — フラグファイルで Execution 停止
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・等重・スコア加重
    - position_sizing.py — 株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - execution/
    - order_manager.py, reconciler.py, ... — 発注関連コンポーネント
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/ (外部データファイル格納想定)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (監視 logs)
    - paper_trading.db (paper trading 用)

（上記は主要モジュールのみ抜粋。詳細は各ファイルの docstring を参照してください。）

---

## よく使う環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- SQLITE_PATH: data/monitoring.db（監視ログ）
- DUCKDB_PATH: data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（default 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

---

## 開発・拡張メモ

- DuckDB はファクト計算 / 研究用途で使用。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- ファクター計算・研究関数は副作用を持たない（pure）ことを意図しているため、テストしやすく設計されています。
- AI 呼び出し部は失敗時フォールバック（0.0 等）を行うなどフェイルセーフを採用。API 呼び出しの中核関数はテストで差し替え可能（patch を利用）。
- Execution と Monitoring はプロセス優先度や PID ファイルで連携する設計です。運用時は PID・kill flag の扱いに注意してください。

---

README の内容はプロジェクトの概要と運用に必要な最低限の手順をまとめたものです。詳細は各モジュールの docstring / ソースコードを参照してください。必要であれば、サンプル .env.example、requirements.txt、運用手順（デプロイ / systemd サービス定義 など）のテンプレートを追加できます。希望があれば作成します。