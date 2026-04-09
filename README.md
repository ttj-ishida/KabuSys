# KabuSys

軽量な日本株自動売買フレームワーク（ライブラリ）。ポートフォリオ構築、ポジションサイズ計算、ファクター研究、ニュース NLP（OpenAI 経由）によるセンチメント、監視（Monitoring）、および発注エンジン／リコンシリエーション等のコンポーネントを含みます。

主に DuckDB / SQLite をデータ層に使い、ブローカーへの接続は抽象化された Protocol（BrokerAPIProtocol）を通して行います。設計方針の多くは「ルックアヘッドバイアス回避」「DB 書き込みの冪等性」「フェイルセーフ挙動（API失敗時は継続）」が反映されています。

---

## 主な機能一覧

- 環境変数 / .env の自動読み込みと Settings ラッパー
  - 自動ロード順: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化
- ポートフォリオ構築（純粋関数）
  - 候補選定 (select_candidates)
  - 等配分 / スコア加重配分 (calc_equal_weights, calc_score_weights)
  - セクター集中防止 (apply_sector_cap)
  - レジーム乗数 (calc_regime_multiplier)
  - 株数決定（リスクベース / weight ベース）(calc_position_sizes)
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ（ATR・出来高）、バリュー（PER/ROE）等の計算
  - 将来リターン、IC（Spearman）や統計サマリ
- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメントスコア生成（gpt-4o-mini を想定）
  - マクロニュースを使った市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライやバックオフ、レスポンス検証あり
- 発注 / 実行
  - OrderManager（状態遷移・二相永続化の考慮）
  - ExecutionEngine（Signal Pull + WebSocket Push drain）
  - Reconciler（起動時の自動同期・ポジション差分検出）
  - Broker クライアントは Protocol ベースで差し替え可能
- 監視（Monitoring）
  - MonitoringDB（SQLite）での永続化レイヤ
  - SystemMonitor / TradeMonitor / RiskMonitor
  - KillSwitch（ファイルベースの停止シグナル）
  - AlertManager（LINE Push での通知）
  - Streamlit ダッシュボード（監視用 UI）

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10+ を推奨（X | Y の型表記などを使用）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がない場合は主要な依存を手動で入れてください:
     ```
     pip install duckdb openai requests psutil streamlit
     ```
   - 実運用ではさらにテスト系や開発ツールを追加してください。

4. 環境変数設定
   - プロジェクトルート（リポジトリ直下）に `.env`（および必要なら `.env.local`）を作成してください。
   - 例（.env.example を参考に作成する想定）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みはデフォルトで有効。テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

5. データディレクトリ等を作成
   ```
   mkdir -p data
   # duckdb や sqlite の DB は初回実行時に作成されます
   ```

---

## 使い方（代表的な利用例）

- Settings（環境設定）を使う
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path  # Path オブジェクト
  ```

- DuckDB 接続を渡してファクター計算（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP（OpenAI）でスコアを付けて ai_scores テーブルに書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # API キーは引数で渡すか、環境変数 OPENAI_API_KEY を設定
  n = score_news(conn, date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {n}")
  ```

- レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20))
  ```

- 監視 DB 初期化（MonitoringDB のテーブル作成）
  ```python
  import sqlite3
  from kabusys.monitoring import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()
  ```

- Streamlit ダッシュボード起動（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine の基本的な流れ（擬似コード）
  - 実際には BrokerAPIProtocol に準拠した broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを注入して開始します。
  - 簡易イメージ:
    ```python
    engine = ExecutionEngine(
        broker=my_broker,
        repo=my_order_repo,
        risk_manager=my_risk_manager,
        order_manager=my_order_manager,
        duckdb_conn=duckdb.connect("data/kabusys.duckdb"),
        config=EngineConfig(target_date=date.today())
    )
    engine.run_session()
    ```
  - 実運用では PID ファイルや kill.flag、リコンシリエーションなどの扱いに注意してください（コード内に詳細ロジックあり）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（既定: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE Push）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring SQLite（既定: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill_mode（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite DB
- PID_FILE_PATH / KILL_FLAG_PATH — 実行制御用ファイルパス
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment ('development'|'paper_trading'|'live')
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定は .env / .env.local から自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
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
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - order_manager.py
    - execution_engine.py
    - reconciler.py
    - (その他: order_record, order_repository, risk_manager 等は別ファイルで想定)
  - ai、portfolio、research、monitoring、execution の各モジュールは
    独立性を保ちながら相互に組み合わせ可能です。

その他、data/ に DB ファイル（duckdb / sqlite）や kill.flag、pid ファイルを置く運用を想定しています。

---

## 注意点 / 実運用上のポイント

- ルックアヘッドバイアス回避: 日付・データ取得は target_date ベースで設計されています。内部で datetime.today() を直接参照する箇所は避ける方針です。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から決定します。配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI API 呼び出しは外部 API なので、失敗時のフォールバック（ゼロスコア等）やリトライロジックが組み込まれています。API キーの保護に注意してください。
- OrderManager / ExecutionEngine 周りはクラッシュ安全性（2相永続化、リコンシリエーション）を考慮した実装です。ブローカーの挙動によって再現性の確認が必要です。
- Monitoring 系は監視・アラート発報を担います。LINE 通知のクールダウンや重複抑止が実装されています。

---

この README はコードの主要な使い方と構成をまとめたものです。より詳細な設計やパラメータチューニングは各モジュールの docstring を参照してください。必要であれば、導入手順のスクリプト化（docker / systemd ユニット例）、CI 設定、ユニットテストの追加手順も別途作成できます。