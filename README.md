# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）／ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログなどの機能を含みます。

主な設計方針：
- DuckDB を中心としたローカル分析基盤
- Look‑ahead バイアス回避（内部で date を明示指定し、現在時刻を直接参照しない設計）
- 冪等性（ETL／保存は ON CONFLICT / upsert を利用）
- API 呼び出しはリトライ・バックオフやレート制御を備える

## 機能一覧
- データ取得 / ETL
  - J-Quants から株価（日足）、財務、上場情報、JPX カレンダーを差分取得（fetch_*）
  - 差分ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存（news_collector）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores へ保存（score_news）
  - マクロ記事を用いた市場センチメントを算出（regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - zscore 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの初期化・運用ヘルパー（init_audit_schema / init_audit_db）
- 設定管理
  - .env / 環境変数からの設定読み込み（自動ロード機能、無効化可）

## 前提条件（推奨）
- Python 3.9+
- DuckDB
- OpenAI SDK（openai）
- defusedxml（RSS パースの安全対策）

必要なパッケージ例：
- duckdb
- openai
- defusedxml

pip でインストールする例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをプロジェクト開発モードで使う場合
pip install -e .
```

## 環境変数（.env の例）
このプロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます（自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

代表的な環境変数（README 用サンプル）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-....

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# DB / ファイル
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `kabusys.config.settings` 経由で取得できます（例: `from kabusys.config import settings; settings.jquants_refresh_token`）。

## セットアップ手順（簡易）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt が無い場合は上の必須パッケージを個別インストール）
4. .env をプロジェクトルートに作成して各種シークレットを設定
5. 初回で監査DB等を初期化（任意）
   - 監査 DB を作る:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

## 使い方（サンプル）
以下はライブラリを直接インポートして使う簡単な例です。実行前に必要な環境変数（特に API キー類）を設定してください。

- 日次 ETL を実行する（DuckDB 接続を用いて）:
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存:
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- マクロ + MA200 を用いた市場レジーム判定:
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（audit）スキーマを既存 DB に追加:
  ```
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- RSS を取得する（news_collector の低レベル関数）:
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["datetime"], a["title"])
  ```

注意点:
- OpenAI を使う関数は引数で API キーを注入可能（api_key=...）。省略時は環境変数 `OPENAI_API_KEY` を参照します。
- ETL / 保存処理は冪等化されていますが、実行する前に DB スキーマ（raw_prices 等）を適切に作成しておいてください（プロジェクト実行環境によっては初期スクリプトが必要です）。
- DuckDB に対する大量の executemany はバージョン差異で挙動が変わることがあります（コード内に互換性対策あり）。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）
- __init__.py — パッケージ初期化（version 等）
- config.py — 環境変数 / .env 自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI 連携）
  - regime_detector.py — ETF/MA とニュースセンチメントから市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得／保存ロジック含む）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 取得・正規化・保存ロジック
  - calendar_management.py — JPX カレンダー管理、営業日ユーティリティ
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 等のファクター計算
  - feature_exploration.py — forward returns / IC / factor_summary 等

その他:
- docs / tests（存在する場合）やトップレベルの設定ファイル（pyproject.toml 等）

## 運用上の注意
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。CI やテストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制御や OpenAI のリトライはコード内で行われますが、実運用では API 使用量 / コストに注意してください。
- 多くの関数は外部 API のエラーを踏まえてフォールバックする実装（フェイルセーフ）になっていますが、ログ監視を必ず行ってください。

---

追加で README に入れたい内容（例: テスト実行方法、ライセンス、貢献ガイドなど）があれば教えてください。必要なら .env.example の雛形ファイルを生成します。