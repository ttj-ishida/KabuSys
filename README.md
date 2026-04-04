# KabuSys — 日本株自動売買システム（README）

概要
---
KabuSys は日本株のデータ取得・品質管理・特徴量（ファクター）計算、ニュースに基づく AI スコアリング、そして監査ログを備えた研究＆自動売買プラットフォームのコアライブラリ群です。  
主に DuckDB をデータ格納に使い、J-Quants API / RSS / OpenAI（LLM）など外部データソースと連携します。設計上、ルックアヘッドバイアス回避や冪等性・堅牢なリトライ処理を重視しています。

主な機能
---
- データ取得（J-Quants API 経由）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー取得（fetch / save）
  - レートリミット遵守、トークン自動リフレッシュ、ページネーション対応
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP（RSS → raw_news）
  - RSS の正規化・SSRF 対策・トラッキング除去
- AI スコアリング
  - 銘柄ごとのニュースセンチメントを OpenAI に問い、ai_scores に保存（score_news）
  - マクロセンチメントと ETF（1321）MA200乖離を合成して市場レジーム判定（score_regime）
  - API エラー時のフォールバックやリトライ実装
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
  - 発注フローの完全トレースを想定した設計

要件
---
- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, logging 等を利用

インストール（開発環境例）
---
1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```
2. 仮想環境の作成と有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   # または requirements.txt があれば:
   # pip install -r requirements.txt
   ```
4. パッケージとしてインストール（開発モード）
   ```bash
   pip install -e .
   ```

環境変数（主な設定）
---
KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（自動読み込み）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime 呼び出し時に未指定であれば参照）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォ: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォ: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — {development, paper_trading, live}（デフォ: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォ: INFO）

例 (.env)
```env
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

セットアップ（データベース初期化例）
---
- 監査ログ専用 DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 返り値は duckdb.DuckDBPyConnection
  ```
- 通常の DuckDB 接続（設定の duckdb_path を使用）:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

基本的な使い方（コード例）
---
- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定して実行可能
  print(result.to_dict())
  ```

- ニュースの AI スコア付与（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を利用
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

設計上の注意点（要点）
---
- ルックアヘッドバイアス回避
  - 多くのモジュールは datetime.today() や date.today() を内部で参照せず、明示的な target_date を受け取る設計です。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等性を確保しています。
- フェイルセーフ
  - LLM / API 呼び出しの失敗時は部分的にスキップして継続する（多くはスコア=0 や空結果へフォールバック）。
- セキュリティ
  - RSS フェッチでは SSRF 対策、XML の安全なパース（defusedxml）、URL 正規化等の対策を実装しています。
- リトライ・レート制御
  - J-Quants クライアントには固定間隔での RateLimiter、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュがあります。
- DuckDB 互換性
  - 一部の executemany 呼び出しやパラメータバインドは DuckDB の挙動（バージョン差）を考慮して実装されています。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py — 環境設定読み込みと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM に送って銘柄スコアを生成（score_news）
  - regime_detector.py — マクロセンチメント + MA200 を合成した市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL の主要ロジックと run_daily_etl 等
  - etl.py — ETLResult 型の再エクスポート
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - news_collector.py — RSS 収集・正規化・保存
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク等）
  - audit.py — 監査ログテーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
- research.* / others — 研究向けユーティリティ類

運用時のヒント
---
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env / .env.local を自動でロードします。テストや CI で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは API の課金・レートに注意してください。テストでは _call_openai_api をモックする設計になっています。
- DuckDB のファイルパスは settings.duckdb_path で一元管理されます。バックアップやローテーションは運用で検討してください。
- run_daily_etl は内部で market_calendar を先に更新し、営業日調整を行ってから株価・財務を取得します（営業日判定に依存する場合はこの順序が重要です）。

ライセンス・貢献
---
（リポジトリの LICENSE を参照してください）

問い合わせ・開発
---
バグレポートや機能提案は issue を立ててください。開発にあたってはユニットテスト・モックを用いた外部 API の分離を推奨します（特に OpenAI/J-Quants 呼び出し周り）。

以上が KabuSys の概要と導入・利用手順です。必要に応じて README に追記したい具体的な実行フロー（cron / systemd 組込例、Docker イメージ、CI 設定など）があれば教えてください。