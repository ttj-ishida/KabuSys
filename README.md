# KabuSys

日本株自動売買システムの軽量ライブラリ／実装サンプル。  
ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、ニュースのAIスコアリングなどを含むモジュール群で構成されています。

主な設計方針:
- DuckDB / SQLite を用いたオンプレ型データ処理
- 本番と Paper Trading の明確な分離
- 自動監視（監視DBへのログ、アラート、kill フラグ）による安全運用
- LLM を用いたニュースセンチメント / レジーム判定（OpenAI）
- 純粋関数ベースでテストしやすいポートフォリオ構成ロジック

---

## 機能一覧
- 環境設定読み込み（`.env`, `.env.local`）と Settings ラッパー（`kabusys.config.Settings`）
- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - `paper_trading` 環境では MockBroker を使用して paper DB に記録
  - PID / stop フラグによる起動制御
- Monitoring（`run_monitoring.py`, `monitoring` モジュール）
  - システム状態・データ鮮度監視（CPU/Mem/Disk、PIDチェック、データ最終日）
  - 注文滞留・約定異常検出
  - ドローダウン／ポジション上限監視と kill flag 発行
  - LINE Push によるアラート送信（`AlertManager`）
  - Streamlit ベースの監視ダッシュボード
- Portfolio 構築ユーティリティ
  - 候補選定、等重・スコア重み付け、セクターキャップ、ポジションサイズ計算
- Research（DuckDB を使ったファクター計算）
  - Momentum / Volatility / Value 等のファクター
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
- AI モジュール
  - ニュース NLP（OpenAI）により銘柄ごとのセンチメントを算出して `ai_scores` に書き込み
  - 市場レジーム判定（ma200 + マクロニュースセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 必要条件（主要な依存）
- Python 3.9+（型ヒントで | を利用）
- pip パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（Python 標準ライブラリで使用）
- ネットワーク接続（LINE API、OpenAI を使う場合）

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 必要な Python パッケージをインストール（上記参照）
3. プロジェクトルートに `.env` を作成（自動ロードされます）
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. 主要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（使用する場合）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（Execution 実行時）
   - OPENAI_API_KEY: OpenAI を使う機能（news/regime）を使う場合
   - KABUSYS_ENV: 環境。`development`（デフォルト） / `paper_trading` / `live`
   - 任意（DBパス等）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE（paper_trading 用の約定モード: instant|partial|never|reject）
     - LOG_LEVEL（DEBUG/INFO/...）

サンプル `.env`（プロジェクトルート）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注: `.env.local` は `.env` より優先して上書きされます。OS 環境変数は保護され上書きされません。

---

## 使い方（主要なスクリプト）

- 監視ループを起動（Monitoring）
  - デフォルトでは production の sqlite_path を使って監視 DB にログを記録します（KABUSYS_ENV に依らず本番 DB を参照する設計）。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト: 60秒）。
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 停止:
    - Ctrl+C（KeyboardInterrupt）
    - またはプロジェクトルートの `data/stop_requested.flag` が存在するとループが終了します（スクリプト内でチェック）。

- ExecutionEngine を起動（発注エンジン）
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離されます。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止は `data/stop_requested.flag` により検知して安全に停止します。
  - 実行時に PID ファイル（デフォルト `data/execution.pid`）を作成し、Process 存在チェックを行います。

- Streamlit ダッシュボード（監視）
  - 起動:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視DB を読み取り専用で開き、ダッシュボード表示を行います。

- Paper Trading 検証レポート
  - CLI 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（`PAPER_TRADING_SQLITE_PATH` 環境変数が優先）

- AI 機能（ニューススコアリング・レジーム判定）
  - ライブラリとして呼び出して使います（OpenAI キーが必要）。
  - 例（Python REPL）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, datetime.date(2026,4,10), api_key="sk-...")
    ```

---

## 運用ノート / 実装上の注意点
- 監視は本番の monitoring DB（`SQLITE_PATH`）に記録されます。監視が常に本番 DB を見に行く設計であるため、開発環境で動かす場合はパスの設定に注意してください。
- ExecutionEngine は paper_trading で DB を分離する仕組みを備えています。Paper 環境では `PAPER_TRADING_SQLITE_PATH` を使用してください。
- kill switch:
  - `KillSwitch` はリスク条件（ドローダウン超過、ポジション上限超過等）を満たした場合に `data/kill.flag` を書き込みます。Execution 側は `KILL_FLAG_PATH` をチェックして安全停止します。
- プロセス優先度設定:
  - 起動時に `set_process_priority("high")` が呼ばれます。OS によって管理者権限が必要な場合があります。失敗しても警告ログに留まり動作は継続します。
- .env 自動ロード:
  - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索されます。環境によって自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイルと役割の抜粋です。

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / Settings)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading レポート生成)
  - ai/
    - news_nlp.py (ニュースセンチメント取得・ai_scores 書き込み)
    - regime_detector.py (レジーム判定、market_regime 書き込み)
  - monitoring/
    - monitoring_db.py (監視 DB スキーマ + 永続化 API)
    - system_monitor.py (システム / データ鮮度監視)
    - trade_monitor.py (注文滞留 / 約定異常監視)
    - risk_monitor.py (ドローダウン・ポジション制限監視)
    - kill_switch.py (kill.flag 管理)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (複数監視を束ねるオーケストレータ)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py (発注ステートマシン API)
    - reconciler.py (起動時リコンシリエーション)
    - ...（broker 用 factory / execution engine 等）
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数決定・スケールダウンロジック)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (IC・統計等)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring / コメントを参照してください。）

---

## 開発・テストに関するヒント
- 多くの関数は外部副作用を持たない純粋関数として実装されているため、ユニットテストが容易です（portfolio / research モジュールなど）。
- DB や OpenAI の呼び出しはモック可能な設計になっています（例: `_call_openai_api` をパッチすることでテスト可能）。
- `.env.local` にテスト固有の設定を置くと便利です。OS 環境変数は自動ロード時に保護されます。

---

必要があれば以下を追加作成します:
- サンプル .env.example
- 初期 DB 作成手順（DuckDB / SQLite のスキーマ初期化スクリプト）
- より詳細な運用手順（systemd ユニットファイル例、ログローテーション、監視運用フロー）

ご希望があれば用途に合わせて README を拡張します。