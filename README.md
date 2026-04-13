# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模フレームワークです。DuckDB / SQLite をデータ層に持ち、ExecutionEngine（発注実行）、Monitoring（監視・アラート）、Research（ファクター計算）、AI モジュール（ニュースセンチメント・レジーム判定）などを含みます。

---

## 特徴（機能一覧）

- Execution
  - 発注管理（OrderManager / OrderRepository）
  - ブローカ抽象化（BrokerClientFactory）により本番・ペーパートレード切替
  - 起動時のリコンシリエーション（Reconciler）で自動復旧
  - リスク管理（RiskManager）による注文抑制
- Monitoring
  - システム状態（CPU / メモリ / ディスク）、プロセス検出、データ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - kill.flag による ExecutionEngine 停止シグナル生成（KillSwitch）
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - SQLite による監視ログ永続化（monitoring_db）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分/スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - ニュースを OpenAI に送り銘柄別センチメントを作成し ai_scores テーブルへ保存（news_nlp）
  - マクロと ETF を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 用の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必須環境・依存パッケージ（例）

- Python 3.9+（ソースは typing の | 記法などを使用）
- パッケージ（最低限の例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- DB: SQLite（標準ライブラリで利用）、DuckDB（duckdb）

※ 実際の requirements.txt は本リポジトリに含まれていないため、プロジェクトで使うバージョンに合わせて requirements を作成してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限の例）
   ```
   pip install duckdb psutil openai requests streamlit
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（OS 環境変数が優先、`.env.local` は上書き）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 重要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: 起動環境（development / paper_trading / live） デフォルト: development
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
   - PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag パス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要エントリポイント）

- ExecutionEngine を起動（本番または paper_trading に応じて動作）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に記録されます。
  - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。

- SystemMonitor をポーリング起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（ローカル閲覧）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先して利用します。
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの集計と PASS/FAIL 判定。

- AI モジュール（プログラムから呼び出し）
  - ニュースセンチメントを生成して書き込む例（Python REPL またはスクリプト内）:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # score_news は target_date（datetime.date）と OpenAI API キーを受け取る
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 運用上のポイント / 注意事項

- Paper Trading は本番 DB と完全分離されるよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- .env 読み込み:
  - OS 環境変数 > .env.local > .env の順で適用されます。
  - 自動ロードはプロジェクトルートを .git または pyproject.toml を基準に検出して行います。
- OpenAI の呼び出しはリトライ（指数バックオフ）やパース失敗時のフェイルセーフを備えていますが、API キーは必須です（AI 機能使用時）。
- kill.flag による停止は冪等で、既に存在する場合は書き込まれません。ExecutionEngine 側で起動時にフラグのクリアを制御できます（Settings.kill_flag_clear_on_start）。
- Process priority / CPU affinity はプラットフォーム差分を抽象化して設定しますが、権限不足などで失敗する可能性があります（警告を出して継続）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - ai/
      - news_nlp.py             — ニュースセンチメント
      - regime_detector.py      — 市場レジーム判定
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層（監視ログ）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (broker_factory / execution_engine 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - utils/
      - process_priority.py

各モジュールは可能な限り純粋関数／DB 依存の分離（DuckDB / SQLite）を意識して実装されています。AI まわりは OpenAI SDK に依存し、外部 API の呼び出しに失敗してもフェイルセーフで継続するよう設計されています。

---

## 開発者向け補足

- コードは DuckDB を分析用に、SQLite を軽量なログ・オーダー永続化に使い分けています。
- 設計方針として「ルックアヘッドバイアス防止（datetime.today()/date.today() を使わない）」が多くの処理で守られています（target_date などを明示的に渡す）。
- テスト時は環境変数による自動 .env ロードを無効化するか、各 API 呼び出し（OpenAI など）をモックしてください。

---

README に含めてほしい追加情報（依存関係の正確なバージョンや実運用時の注意点など）があれば教えてください。必要に応じてインストール用の requirements.txt や systemd / supervisor の起動例も作成します。