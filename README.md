# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データの取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなどを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない）
- DuckDB をデータ層に使用し、ETL は冪等性を重視
- 外部 API 呼び出しはリトライ / バックオフ / フェイルセーフを備える
- LLM（OpenAI）をニュース分析・マクロセンチメントに利用（JSON Mode）

---

## 機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）
- データ取得（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダー、上場銘柄情報の取得
  - レートリミット、トークン自動リフレッシュ、ページネーション対応
- ETL パイプライン
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得 / バックフィル / 品質チェック（品質問題を収集して返す）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合の検出
- ニュース収集 / NLP
  - RSS 取得と前処理（URL トラッキング除去・SSRF 対策）
  - OpenAI を用いた銘柄別ニュースセンチメント集計（news_nlp.score_news）
  - マクロセンチメント + MA 乖離から市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ生成・初期化（init_audit_schema / init_audit_db）
- その他ユーティリティ
  - 市場カレンダー操作（is_trading_day / next_trading_day / get_trading_days 等）
  - DuckDB ベースの保存ユーティリティ（save_*）

---

## 要件
- Python 3.10+
- 必要なライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / datetime 等を使用

（実際のパッケージ化時には requirements.txt / pyproject.toml で依存を管理してください）

---

## セットアップ手順

1. レポジトリをクローン（あるいはパッケージを配置）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはパッケージ化されていれば:
   # pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可）。必須の主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: モニタリング DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: one of development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な例）

以下は Python REPL やスクリプトから利用する基本例です。先に DuckDB コネクションを作成してください。

- DuckDB 接続の作成
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores テーブルへ保存
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # 環境変数 OPENAI_API_KEY を使用する場合、api_key は省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("score_regime result:", res)
  ```

- RSS フィードを取得（ニュース収集テスト）
  ```py
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["title"], a["datetime"])
  ```

- 監査ログ DB の初期化（専用 DB を作る）
  ```py
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される
  ```

- 研究向けユーティリティ
  ```py
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, date(2026, 3, 20))
  # records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
  ```

注意点:
- OpenAI 呼び出しは JSON Mode を利用するため、API レスポンスの形式チェック・パースが厳密です。
- ETL / 保存関数は冪等に設計されています（ON CONFLICT DO UPDATE 等）。
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

---

## 開発向けメモ
- ログレベルは環境変数 LOG_LEVEL で制御
- KABUSYS_ENV の有効値: development, paper_trading, live
- DuckDB バージョンによる executemany の挙動差異に対処済み（空リストの扱い等）
- OpenAI / J-Quants 呼び出し箇所はユニットテストでモック可能な内部ラッパーを使っています

---

## ディレクトリ構成（主なファイル・モジュール）
src/kabusys/
- __init__.py — パッケージ初期化（version 等）
- config.py — 環境変数 / 設定管理（.env 自動ロード, Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの銘柄別スコアリング（score_news）
  - regime_detector.py — マクロ + MA200 で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py — ETL パイプライン / run_daily_etl / ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得と前処理
  - calendar_management.py — 市場カレンダー操作・calendar_update_job
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（各種チェック + run_all_checks）
  - audit.py — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility / Liquidity の計算
  - feature_exploration.py — 将来リターン / IC / factor_summary / rank 等
- ai/__init__.py, research/__init__.py 等で公開 API を整理

---

## 最後に / 参考
- 本ライブラリはバックテスト・運用を通じて Look-ahead を避ける設計を重視しています。ETL・スコアリング・レジーム判定はいずれも「対象日以前のデータのみ」を参照するように実装されています。
- 実際の運用では API キー管理、ログ監視、失敗時のアラート、モニタリング DB（sqlite）への統合などをご検討ください。

ご要望があれば、README に入れるサンプル .env.example、CI 実行例、より詳しい API 仕様（各関数の引数・返り値の例）を追加します。