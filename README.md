# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）。  
このリポジトリは、取引実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ／AI 補助モジュールを含みます。

以下はこのコードベースの README（日本語）です。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成された自動売買システムです。

- ExecutionEngine：ブローカーとやりとりして発注・状態管理を行う実行層
- Monitoring：システム稼働状態、注文の滞留や約定異常、リスク（ドローダウン／保持銘柄数）を監視し、ログおよびアラートを行う
- Portfolio：候補選定、配分重み、ポジションサイジング、セクター制約・レジーム調整等の純粋関数群
- Research：DuckDB を用いたファクター計算・特徴量探索
- AI：OpenAI を用いたニュースセンチメント（銘柄別）およびマクロセンチメント→市場レジーム判定
- Tools：Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード等

設計方針の一部：
- DB（SQLite / DuckDB）を用いてデータ永続化・分析を行う
- 本番と Paper Trading は DB を分離して運用可能
- OpenAI 呼び出し部分は失敗してもフェイルセーフ（スコア 0 にフォールバック）を基本とする
- 自動的に .env / .env.local を読み込む仕組み（必要なら無効化可能）

---

## 主な機能一覧

- 実行関連
  - 注文の作成 / 送信 / 同期 / リコンシリエーション（再起動後の自動復旧）
  - RiskManager による利用率・ポジション上限・サーキットブレーカー等の制御
- 監視関連
  - SystemMonitor：CPU / メモリ / ディスク / 実行プロセス生存確認 / データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - KillSwitch：重大リスク検出時に flag ファイルを書き ExecutionEngine に停止を通知
  - AlertManager：LINE Push を利用した通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- ポートフォリオ構築
  - 候補選定（スコア/ランク基準）
  - 等分配・スコア重み配分・リスクベースのポジションサイジング
  - セクターキャップ、レジーム乗数
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（OpenAI）
  - ニュースを集約して銘柄別センチメントを取得し ai_scores に格納（score_news）
  - マクロ記事 + ETF（1321）MA200乖離で日次の市場レジーム判定（score_regime）
- ツール
  - Paper Trading 検証レポート生成（period 指定可）
  - Monitoring DB 初期化関数（init_monitoring_db）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール（requirements.txt が無い場合は最低限以下をインストール）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   （実行環境に合わせて追加パッケージを追加してください）
4. 環境変数を設定
   - プロジェクトルートに `.env`／`.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）
   - 主要な環境変数（例）
     ```
     KABUSYS_ENV=development           # development | paper_trading | live
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
   - `Settings` クラスで他のデフォルト値や検証ロジックを参照できます（`kabusys/config.py`）
5. DB（data ディレクトリ）を作成
   ```
   mkdir -p data
   ```
   Monitoring スクリプトは起動時に `init_monitoring_db()` を呼び DB スキーマを作成します。

---

## 使い方（主要スクリプト / モジュール）

※ package として実行できるように `python -m kabusys.<module>` での実行を想定しています。

- ExecutionEngine（取引実行）
  - 本番 / 開発 / Paper Trading を環境変数 `KABUSYS_ENV` で切り替え
  - Paper Trading の場合は Mock ブローカーを使用し `PAPER_TRADING_SQLITE_PATH` に書き込みます
  - 起動：
    ```
    python -m kabusys.run_execution
    ```
  - 起動時にプロセス優先度を "high" に設定し、DB 接続→ブローカー生成→Engine.run_session() を呼びます。

- Monitoring（ポーリング監視ループ）
  - 起動：
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数
    - `MONITOR_POLL_INTERVAL`：ポーリング間隔（秒、デフォルト 60）
      - 不正な値や 0 以下が指定された場合はデフォルトにフォールバック
    - 監視は常に本番 `SQLITE_PATH` を使用（環境に依存しない）
  - 監視ループは SystemMonitor.check_once() を定期実行し、monitoring DB に永続化します。

- Streamlit ダッシュボード（監視用）
  - 実行コマンド例：
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - read-only モードで SQLite を開くため、DB が存在しない場合は MonitoringEngine を起動してデータを作成してください。

- Paper Trading 検証レポート生成ツール
  - 実行：
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション
    - `--from YYYY-MM-DD`：開始日
    - `--to YYYY-MM-DD`：終了日
    - `--db PATH`：SQLite DB パス（環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）

- AI モジュール
  - 銘柄ニュースセンチメント（ai_scores への書き込み）
    - 関数： `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `api_key` が未指定のときは環境変数 `OPENAI_API_KEY` を参照
  - 市場レジーム判定
    - 関数： `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
    - DuckDB 接続と日付を渡して実行し `market_regime` テーブルに書き込む
  - 注意：OpenAI API を利用するため `OPENAI_API_KEY` の設定が必須（未設定時は例外・または処理内でフォールバック）

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の成行約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス PID ファイル / kill.flag のパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

設定の読み込みロジックは `src/kabusys/config.py` を参照してください。プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動で読み込みます。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なファイル・ディレクトリ構成の抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定読み込み
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine 関連モジュール — 一部は上位参照)
    - order_manager.py
    - reconciler.py
    - ...（他の execution 関連ファイル）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py                     — OpenAI を使ったニュースセンチメント
    - regime_detector.py              — マクロ + MA200 によるレジーム判定

（上記はコードベースの主要部を抜粋したものです。詳細は各モジュールの docstring を参照してください。）

---

## 実行上の注意点 / 運用メモ

- DB マイグレーション：
  - monitoring_db.init_monitoring_db(conn) は冪等でスキーマを作成します。既存 DB にカラムが足りない場合は簡単な ALTER を行う処理も含まれます。
- Paper Trading：
  - `KABUSYS_ENV=paper_trading` の場合、Execution は本番 DB と完全分離された `PAPER_TRADING_SQLITE_PATH` に書き込みます。
  - `PAPER_FILL_MODE` により MockBroker の約定挙動を制御できます（instant / partial / never / reject）。
- プロセス管理：
  - 起動スクリプトはプロセス優先度を上げようとします（psutil が必要）。権限や OS により設定に失敗する場合がありますが、ログで警告されスキップされます。
- Kill Switch：
  - KillSwitch は `KILL_FLAG_PATH` に reason を書き込み ExecutionEngine に停止を促します。flag の存在チェックや自動クリアは設定に依存します。
- OpenAI 呼び出し：
  - レート制限や一時エラーに対して指数バックオフでリトライを行いますが、API キーの漏洩やコスト管理に注意してください。

---

## 開発・拡張のヒント

- DuckDB クエリはモジュール内で直接 SQL を組み立てています。性能上の改善は SQL チューニングやインデックス・パーティショニングで対応できます。
- AI モジュール（news_nlp / regime_detector）はテスト可能な設計（API 呼び出し箇所を差し替えられる）になっています。ユニットテストでは _call_openai_api をモックすることで安定化できます。
- ポートフォリオロジックは純粋関数群で DB 非依存なので単体テストが容易です（calc_position_sizes など）。

---

もし README に含めてほしい追加情報（例：運用手順、推奨監視閾値、実際の起動サービス定義 systemd ユニット例、requirements.txt の内容など）があれば教えてください。必要に応じてサンプル .env.example や systemd ユニットテンプレートも作成できます。