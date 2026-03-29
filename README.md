# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得 & DuckDB 保存）、ニュース収集と NLP（OpenAI を利用したセンチメント評価）、研究用ファクター計算、監査ログ（トレーサビリティ）など、運用に必要なコンポーネントを提供します。

---

## 主要機能（概要）

- データ取得 / ETL
  - J-Quants API からの株価（日次OHLCV）・財務データ・JPX カレンダー取得（ページネーション・再試行・レート制御対応）
  - 差分更新・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS からの記事収集（SSRF 対策・トラッキングパラメータ除去・前処理）と raw_news への冪等保存
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント算出（OpenAI を利用、バッチ送信・レスポンス検証・リトライロジック）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントを合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- 監査（Audit）
  - signal → order_request → execution のトレーサビリティを保つ監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env ファイルまたは環境変数から設定を安全に読み込み（自動ロード機能あり）

---

## システム要件（概略）

- Python 3.10+
- 必要な主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / ニュース RSS）

（実際の依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml や requirements ファイルがある場合はそれに従ってください。例（pip）:
   ```bash
   pip install -e .              # 開発インストール（setup がある前提）
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動的に読み込まれます（.git または pyproject.toml を検出してプロジェクトルートを判断）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須変数の例（.env の例）
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

     # DB パス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境設定
     KABUSYS_ENV=development    # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 必須環境変数が未設定の場合、Settings プロパティからアクセスした際に ValueError が投げられます。

---

## 基本的な使い方（コード例）

以下は主要ユースケースの最小例です。すべて Python スクリプト内から利用できます。

- 設定オブジェクトの取得
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)
  ```

- DuckDB に接続して日次 ETL を実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコアリング（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定する
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {written} codes")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB 初期化（監査テーブルを作成）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # ファイルがない場合は作成される
  ```

- J-Quants 認証トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- RSS フィードの取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```
  ※ collect → DB 保存処理はプロジェクト内の ETL / 保存機能と連携して実装してください（raw_news への冪等保存ロジックはモジュール内に用意されています）。

---

## 設定（Settings） - 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。不正な値はエラー。
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）。関数に api_key を渡すことも可能。
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）

※ Settings は実行時に .env / .env.local を自動でロードします。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行われます。

---

## 推奨ワークフロー（運用例）

1. .env に機密情報をセット（.env はリポジトリにコミットしない）
2. 日次 ETL をスケジューラ（cron / Airflow / GitHub Actions）で実行:
   - run_daily_etl を呼び出してデータ取得・保存・品質チェックを実行
3. ETL 後にニューススコアとレジーム判定を実行
   - score_news → ai_scores 更新
   - score_regime → market_regime 更新
4. 監査テーブルを初期化・利用してシグナル〜約定の追跡を行う
5. 研究用に kabusys.research モジュールを使ってファクター計算や IC 測定

---

## ディレクトリ構成（主要ファイル）

（根幹は `src/kabusys` 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの LLM スコアリング
    - regime_detector.py       — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得/保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - news_collector.py        — RSS 取得と前処理
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログ初期化 / schema
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py   — 将来リターン / IC / summary
  - research/*（その他研究用ツール）
  - ...（他モジュール：strategy / execution / monitoring はパッケージ化想定）

---

## 注意事項 / 設計上のポイント

- Look-ahead bias を防ぐため、各モジュールは内部で datetime.today() を無条件に参照しない設計（target_date 引数ベース）。
- OpenAI や J-Quants の呼び出しは再試行・バックオフや 5xx/429 のハンドリングを備えています。API キーやレート制御に注意してください。
- DuckDB に対する executemany や INSERT 文は一部バージョン依存の制約を考慮した実装があります（例: 空の executemany を呼ばない等）。
- .env 自動ロードは便利ですが、CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を推奨します。

---

## 追加情報 / 貢献

- バグ報告・機能要望は Issue を立ててください。
- 開発ルール（型チェック・テスト・CI）についてはプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

---

この README はリポジトリ内のモジュール設計とドキュメント注釈に基づいて作成しています。使い始めや運用にあたっては、pyproject.toml / requirements.txt / 実際のスクリプトを参照して環境を整えてください。