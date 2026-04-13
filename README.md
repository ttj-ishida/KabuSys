# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）。

このリポジトリは主に以下を提供します：
- 注文実行エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch、LINE通知）
- ポートフォリオ構築ユーティリティ（候補選定・配分・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

---

## 主な機能

- Execution
  - 注文生成・送信・同期のための OrderManager / OrderRepository / Reconciler。
  - ブローカープラグイン機構（実運用 or Paper Trading の切替）。
  - リスク管理（RiskManager）を組み込んだ ExecutionEngine。

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk/プロセス状態・データ鮮度監視。
  - TradeMonitor：滞留注文・約定価格異常検出。
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ記録。
  - KillSwitch：フラグファイル（data/kill.flag）で ExecutionEngine 停止をトリガ。
  - AlertManager：LINE プッシュ通知（クールダウン管理）による通知。

- Portfolio Construction（純関数群）
  - 候補選定、均等配分 / スコア配分、リスク調整（セクターキャップ・レジーム乗数）、発注株数算出（単元丸め、aggregate cap）。

- Research
  - ファクター（Momentum / Volatility / Value）計算（DuckDB 上の prices_daily/raw_financials を参照）。
  - 将来リターン計算、IC（Information Coefficient）・統計サマリ。

- AI / NLP
  - news_nlp.score_news(): raw_news を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に書き込み。
  - regime_detector.score_regime(): ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成し market_regime に書き込み。

- 運用ツール
  - Streamlit ダッシュボード（監視情報の可視化）
  - Paper Trading 検証レポート生成スクリプト

---

## 動作要件（概略）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3 等

インストール例：
```
python -m pip install duckdb psutil requests openai streamlit
```

（実運用では仮想環境 / requirements.txt を用意してください）

---

## 環境変数（代表例）

- 必須/重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabu ステーション API パスワード
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector が参照
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading の場合、Execution は MockBrokerClient を使用し paper 用 SQLite（data/paper_trading.db）に記録され、本番 DB と分離される
- データベースパス（デフォルト path は data/ 以下）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — Monitoring 用（monitoring は常に本番 sqlite_path を使う設計に注意）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- 監視 / PID / Kill フラグ
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag を削除)
- 監視ループ間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- Paper Trading 動作モード
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト "instant"）

.env の自動読み込み
- プロジェクトルートに .env / .env.local がある場合、自動的に環境変数として読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順（例）

1. リポジトリをクローンして Python 仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil requests openai streamlit
   ```

2. .env ファイルを作成（.env.example を参照して必要な値を設定）
   例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   OPENAI_API_KEY=zzzz
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

3. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

4. DuckDB / SQLite の初期テーブルは実行時に自動生成されます（init_monitoring_db を利用）。

---

## 使い方（実行例）

- ExecutionEngine を起動（プロセス優先度を High に設定）
  - 実運用（本番 DB を使用）:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（KABUSYS_ENV=paper_trading を設定）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意: run_execution は Settings.is_paper によって paper 用 SQLite を使用します。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は設計上、環境にかかわらず本番 sqlite_path を使用する点に注意。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ローカルで監視 DB を read-only で開いて表示します。MonitoringEngine が先に DB を初期化している必要があります。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI モジュール（スクリプト / 直接呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...) の戻り値）を受け取り、内部で OpenAI API を呼び出します。API キーは引数または環境変数 OPENAI_API_KEY で渡してください。

---

## 運用上の注意点 / 補足

- プロセス優先度
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出します。必要に応じて OS 権限や環境での制約により設定できない場合があります（ログに警告が出ます）。

- kill.flag（KillSwitch）
  - KillSwitch は risk モニタ等の条件でデータ/kill.flag を書き込み、ExecutionEngine 停止の指示を出す仕組みです。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと起動時に既存の kill.flag を自動で削除できます。

- Monitoring DB のマイグレーション
  - init_monitoring_db() は冪等にテーブルとインデックスを作成します。既存 DB に新しいカラムがない場合は ALTER TABLE による簡単なマイグレーションを実行します（例: trade_logs.latency_ms, dashboard.peak_value）。

- Paper Trading 分離
  - paper_trading モードは production DB と完全に分離して記録される設計です。安全に動作確認できます。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — Settings クラス（環境変数読み取り・自動ロード）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI ツール
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - (その他関連モジュール)
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
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
  - data/
    - pipeline.py (prices_daily などを扱うユーティリティ群)
  - utils/
    - process_priority.py

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。）

---

## 開発・拡張ポイント（メモ）

- DuckDB を用いたファクター/リサーチ系は SQL と Python 併用で高速に集計できます。prices_daily/raw_financials の整備が重要です。
- AI 系は OpenAI API の呼び出しを行う設計のため、API レート制御やリトライポリシーに注意しています。レスポンスのバリデーションや部分失敗時のフェイルセーフも実装済みです。
- ポジション決定・発注ロジックは単元株（lot_size）や aggregate cap を考慮したスケーラブルな実装になっています。将来的に銘柄別単元対応やマスタ連携が容易な設計です。

---

README は以上です。実際の導入時は .env の設定・DB 初期データの準備（prices_daily 等）・ブローカークライアントの設定（本番接続情報）を行ってください。追加で README に含めたい実行例や設定のテンプレートがあれば教えてください。