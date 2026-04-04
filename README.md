# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と NLP による銘柄センチメント、マーケットレジーム判定、研究（ファクター計算・特徴量解析）、監査ログ（トレーサビリティ）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・レート制御・リトライ）
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
  - データ品質チェック（欠損値・スパイク・重複・日付不整合）

- ニュース関連 / NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄単位のニュースセンチメント（score_news）
  - マクロニュースと ETF（1321）の MA 乖離を合成した市場レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ

- 監査・実行ログ
  - シグナル〜発注〜約定までの監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注ログの冪等性、ステータス遷移の想定

- 設定管理
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml 基準）
  - 必須環境変数チェックを含む Settings クラス（kabusys.config.settings）

---

## 前提 / 推奨環境

- Python 3.10+
  - 型アノテーション（X | Y 形式）等を利用しているため Python 3.10 以上を推奨します
- 主な依存パッケージ（プロジェクトによって追加が必要）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging など）

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの pyproject.toml / requirements.txt を使う
   # pip install -e .
   ```

4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - 任意 / 設定可能:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH（実行監視用）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査 DB の初期化例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema, init_audit_db

   # 既存接続にスキーマを追加する場合
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn)

   # 監査専用 DB を初期化して接続を得る
   conn2 = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要ユースケース例）

- Settings（環境変数読み込み）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- カレンダー更新ジョブ（nightly）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

- ニュース RSS 収集（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

---

## 設定・環境変数の詳細

主なキー（kabusys.config.Settings で利用）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / NLP
  - OPENAI_API_KEY（score_news / score_regime などで必須）
- 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用: data/monitoring.db)
  - PID_FILE_PATH (実行監視)
  - KILL_FLAG_PATH (実行監視)
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意:
- ライブラリは .env の自動読み込みを行います（プロジェクトルートを自動検出）。自動読み込みを停止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings の必須キーが未設定の場合、呼び出し時に ValueError を送出します。

---

## ディレクトリ構成（主要ファイル）

（コードベースに基づく抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュース NLP / score_news
    - regime_detector.py      -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - etl.py                  -- ETLResult 再エクスポート
    - news_collector.py       -- RSS 収集・前処理
    - quality.py              -- データ品質チェック
    - stats.py                -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py  -- マーケットカレンダー管理・ジョブ
    - audit.py                -- 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py      -- Momentum / Value / Volatility 等
    - feature_exploration.py  -- forward returns / IC / summary

---

## 開発上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - 多くの処理（news window / MA / ETL 等）は内部で date 引数を取り、datetime.today() を直接参照しないことにより、バックテストや過去データ評価でのルックアヘッドを防止します。
- 冪等性:
  - DuckDB への保存は原則 ON CONFLICT DO UPDATE や明示的な DELETE→INSERT の手法で冪等性を保ちます。
- フェイルセーフ:
  - LLM 呼び出しや外部 API 失敗時は部分的なデフォールト値（例: macro_sentiment=0.0）で継続し、全体処理が停止しない設計を採用しています。
- セキュリティ:
  - RSS 収集では SSRF 対策、XML パースに defusedxml を利用、受信バイト数制限などを実装しています。
- 再試行 / レート制御:
  - J-Quants クライアントはレート制御（120 req/min）、指数バックオフ、401 時のトークン自動リフレッシュに対応しています。
  - OpenAI 呼び出しもリトライロジックを持っています（429 / タイムアウト / 5xx に対する再試行）。

---

## 貢献・ライセンス

- この README はリポジトリ内のコードから抽出した情報に基づく概要です。実際のプロジェクトでは pyproject.toml / setup.py / requirements.txt、LICENSE、CONTRIBUTING.md を整備してください。

---

README に記載の使い方はライブラリ内部 API の一例です。実運用時はログ設定、監視、バックアップ、シークレット管理、テスト（単体テスト／統合テスト）を十分に行ってください。質問や補足したい箇所があれば教えてください。