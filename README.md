# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）→ ETL → 品質チェック → 特徴量抽出 → AI（ニュースセンチメント／市場レジーム）→ 監査ログ までの主要機能をモジュール単位で提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム取引のための基盤ライブラリです。主に以下を目的としています：

- J-Quants API からの株価・財務・カレンダー取得、DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ETL パイプライン（日次差分取得 + 品質チェック）
- ニュース収集（RSS）＆ニュースの NLP（OpenAI）による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（シグナル → 発注 → 約定のトレース）の初期化支援

設計上、ルックアヘッドバイアスを避けるために日付参照は明示的な引数で行い、ETF/ニュース等の処理は idempotent（冪等）で実装されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック（欠損 / 重複 / スパイク / 日付整合性）
  - calendar_management: 営業日判定・next/prev_trading_day・カレンダー更新ジョブ
  - news_collector: RSS 収集・前処理・SSRF対策・正規化
  - audit: 監査ログ用スキーマ初期化（DuckDB）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 & ai_scores へ保存
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility（各種ファクター）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定（自動 .env 読み込み機能を含む）

---

## セットアップ手順

前提: Python 3.9+ を推奨（コードは型ヒントに union types 等を使用）。プロジェクトは src/ 配下にパッケージ構成されています。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係をまとめてください。Slack 通知等を使う場合は slack-sdk 等を追加でインストールしてください。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```
   （pyproject.toml / setup.py がある場合）

5. 環境変数 / .env の設定  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   代表的な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # オプション（デフォルトあり）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development          # development / paper_trading / live
   LOG_LEVEL=INFO                   # DEBUG/INFO/WARNING/ERROR/CRITICAL
   OPENAI_API_KEY=sk-...
   ```

---

## 使い方（簡単なコード例）

以下は主要コンポーネントの利用例です。日付引数は明示的に指定することでルックアヘッドバイアスを回避します。

- DuckDB コネクションの作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI）を取得して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数で設定するか、api_key 引数で明示的に渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードの取得（ニュースコレクター）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 設定値の取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意: OpenAI を使う関数は API 呼び出しに失敗した場合、エラーではなくフォールバック処理（スコア0.0 など）を行う設計の箇所があります。API キーが未設定の場合は ValueError が発生します。

---

## ディレクトリ構成

主要ファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (not shown in抜粋 but exported in package __all__ — 監視系モジュール想定)
  - strategy/ (戦略層、抜粋外)
  - execution/ (発注・ブローカー連携、抜粋外)

各モジュールは責務ごとに分離され、テスト容易性のために外部呼び出し（OpenAI や HTTP）を差し替え可能な実装になっています（例: internal _call_openai_api を mock で差替えなど）。

---

## 環境変数（要点）

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 自動 .env 読み込みを無効化（テスト等で利用）

- 必須（利用する機能に依存）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
  - OPENAI_API_KEY: OpenAI を使う場合に必要（news_nlp / regime_detector）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合

- オプション
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: ログレベル（デフォルト INFO）
  - DUCKDB_PATH / SQLITE_PATH: DB ファイルパス（デフォルト値あり）
  - KABU_API_BASE_URL / KABU_API_PASSWORD: kabu API 用

.env.example を用意して、必要なキーを設定してください。

---

## 開発・テストについての注意点

- ルックアヘッドバイアス防止のため、処理は明示的な target_date 引数で実行する設計です。内部で date.today()/datetime.today() を参照しない実装が多く採用されています。
- OpenAI など外部 API 呼び出しはリトライロジック・フォールバックが実装されていますが、ユニットテスト時は該当内部呼び出しをモックしてください（コード中に patch 想定の箇所あり）。
- DuckDB の executemany に関する挙動（空リスト不可など）に注意して実装されています。

---

もし README に追加して欲しい内容（例: 実行スクリプト例、CI 設定、詳細なスキーマ定義、requirements.txt、Dockerfile など）があれば指示してください。