# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）  
このリポジトリは、J-Quants / JPX 等からのデータ取得（ETL）、ニュース収集・NLP、ファクター計算、監査ログ、及び市場レジーム判定やAIベースのニュースセンチメント解析を行うユーティリティ群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要APIと例）
- ディレクトリ構成
- 補足 / 注意事項

---

## プロジェクト概要

KabuSys は日本株向けデータ基盤と研究 / 戦略実行のための共通ライブラリです。主に以下をカバーします。

- J-Quants API からの差分ETL（株価日足 / 財務 / 市場カレンダー）
- DuckDB を利用したデータ保存・クエリ
- ニュース収集（RSS）と前処理、記事 - 銘柄の紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（ai.news_nlp）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースのセンチメント合成）
- ファクター計算・特徴量探索（research）
- データ品質チェック（quality）
- 監査ログテーブル（audit）と監査DB初期化ユーティリティ
- kabuステーション等への実際の発注・実行は execution モジュール（別途実装想定）

設計上、ルックアヘッドバイアスの防止や、API呼び出しのリトライ／フェイルセーフを考慮した実装になっています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 / 保存 / ページネーション / トークンリフレッシュ）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS取得、前処理、SSRF対策、トラッキングパラメータ削除）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA とマクロニュースを合成）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / ranking）
- config
  - 環境変数管理（.env 自動読み込み、必須キー取得ユーティリティ settings）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 環境（推奨：3.10+）を用意（仮想環境推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール（例）
   - 最低限必要な依存（本コードベースで参照されている主要ライブラリ）：
     - duckdb
     - openai
     - defusedxml
   例：
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では logging, urllib 等の標準ライブラリに加え、kabu API クライアントや Slack 通知周りのパッケージが必要になる場合があります。プロジェクトに requirements.txt があればそちらを利用してください。

4. 開発用インストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数（.env）と設定

`kabusys.config.Settings` がアプリ設定を提供します。起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動的に読み込みます（優先順位：OS環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu API のパスワード（必須）
- KABU_API_BASE_URL : kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（ai モジュールで使用）
- SLACK_BOT_TOKEN : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack チャネルID（必須）
- DUCKDB_PATH : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH : 実行プロセス監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視設定
- KABUSYS_ENV : environment（development / paper_trading / live）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）

設定は `from kabusys.config import settings` で利用できます。必須変数が不足している場合は ValueError が発生します。

---

## 使い方（主要APIとサンプル）

以下は主要ユーティリティの簡単な使用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を正しく設定してください。

- DuckDB 接続の例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（AI呼び出し）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数か引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {n}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査DB初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は監査テーブルを作成して接続を返します
  ```

- RSS 取得（ニュースコレクタの一部）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 研究（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  # recs は各銘柄の mom_1m / mom_3m / mom_6m / ma200_dev を含む dict のリスト
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## ディレクトリ構成

主要ファイル・モジュールの構成（src/kabusys 配下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュースセンチメント解析（OpenAI 呼び出し & バリデーション）
    - regime_detector.py-- 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント（取得/保存/トークン管理/レート制御）
    - pipeline.py       -- ETL パイプライン（run_daily_etl 等）
    - etl.py            -- ETLResult の再エクスポート
    - news_collector.py -- RSS 収集・前処理（SSRF 対策、正規化）
    - quality.py        -- データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
    - calendar_management.py -- 市場カレンダー管理（営業日判定 / calendar_update_job）
    - audit.py          -- 監査ログスキーマ定義・初期化
    - stats.py          -- 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*         -- ファクター/特徴量解析関連
  - (その他) strategy/, execution/, monitoring/ 等の名前が __all__ に含まれているが、
    実装はこのコードベースの別ファイルまたは将来の拡張を想定。

---

## 補足 / 注意事項

- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検証 / プライベートIP拒否）や XML 脆弱性対策（defusedxml）を実装していますが、実運用ではさらにネットワーク制限や監視を行ってください。
- OpenAI 呼び出し
  - ai モジュールは OpenAI の JSON Mode を使用します。API の制限・料金に注意してください。API エラー時はフェイルセーフとしてスコアを 0.0 にフォールバックする箇所があります。
- ルックアヘッドバイアス
  - ライブラリ内の多くの関数はルックアヘッドバイアスを防ぐ設計（target_date より前のデータのみ参照）になっています。バックテストで利用する際はこの点に注意してください。
- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

README はここまでです。詳細なAPI仕様や追加の運用手順（バッチスケジューリング、ログ集約、発注実装、テストスイートなど）は別ドキュメント（Design / DataPlatform / StrategyModel 等）を参照してください。必要であれば README にサンプル .env.example、requirements.txt、起動スクリプト例を追加します。どの情報を追加したいか教えてください。