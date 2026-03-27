# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注 → 約定のトレーサビリティ）など、研究／運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local を自動ロード（プロジェクトルートを特定して安全に読み込み）
  - 必須変数は Settings 経由で取得（未設定時に明示的な例外）

- データETL（J-Quants）
  - 株価日足（OHLCV）／財務データ／市場カレンダーの差分取得・保存（ページネーション対応）
  - レート制限・再試行・トークン自動リフレッシュを実装
  - DuckDB への冪等保存（ON CONFLICT を使用）

- ニュース収集・NLP
  - RSS フィードの収集（SSRF対策、サイズ制限、URL 正規化）
  - ニュースを銘柄単位で集約して OpenAI（gpt-4o-mini）でセンチメント判定（JSON-mode）
  - エラー耐性とリトライロジック

- 市場レジーム判定
  - ETF (1321) の 200日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジームを保存

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合 を検出
  - QualityIssue オブジェクトとして集約

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化処理
  - UUID ベースのトレーサビリティ、冪等性を考慮した設計

---

## 必要条件・依存ライブラリ（想定）

- Python 3.10+（型アノテーションで union | を使用）
- duckdb
- openai (OpenAI Python SDK, v1系の API を想定)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

（プロジェクトの requirements.txt / pyproject.toml があればそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール
   - pyproject.toml または requirements.txt がある場合はそれに従ってください。
   - 最小限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（パッケージとして扱う場合）:
     ```
     pip install -e .
     ```

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（環境変数優先）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
     - LOG_LEVEL: ログレベル (DEBUG/INFO/...)

5. DuckDB データベース初期化（監査ログ用など）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続に監査スキーマを追加:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（簡単な例）

- 設定（Settings）の利用:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  ```

- DuckDB に接続して ETL を実行（run_daily_etl）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを作成して ai_scores に保存:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジームのスコアリング:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（研究用）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しを伴う関数（score_news, score_regime）は api_key を引数で与えるか、環境変数 OPENAI_API_KEY を設定してください。
- バックテストでの「look-ahead bias」を避けるため、各モジュールは内部で datetime.today() を直接参照しない設計になっています（target_date を明示的に渡すことを推奨）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュースの集約・OpenAI スコアリング、ai_scores への保存
    - regime_detector.py      -- 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py  -- 市場カレンダー管理・営業日計算
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - etl.py                  -- ETL 結果クラス公開
    - jquants_client.py       -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       -- RSS 取得と前処理
    - quality.py              -- データ品質チェック
    - stats.py                -- 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      -- モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py  -- 将来リターン・IC・統計サマリー等
  - (その他: execution, monitoring, strategy パッケージを __all__ に含める想定)

---

## 動作上の注意 / 設計方針（抜粋）

- Look-ahead バイアス対策:
  - 多くの処理は target_date を引数に取り、内部で現在時刻を直接参照しないようになっています。
  - API 取得時に fetched_at を記録して「いつデータを知り得たか」をトレース可能にします。

- 冪等性:
  - DuckDB への保存は ON CONFLICT（更新）を使って冪等に保存します。
  - 発注ログ（order_request_id 等）で発注の二重処理を防ぎます。

- フェイルセーフ:
  - LLM 呼び出しや外部 API の失敗時は例外でプロセス全体を止めずにフォールバック（0.0 等）やスキップで継続する設計になっています。ただし、必要に応じて呼び出し元で失敗を検出してください。

---

## よくある質問（Q&A）

- .env の自動読み込みを無効にするには？
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI のレスポンスが不安定な場合は？
  - モジュール内で再試行（指数バックオフ）を行います。テスト時は内部の _call_openai_api をモックしてください。

- DuckDB のスキーマはどこで定義されますか？
  - 各モジュール（etl, audit, etc.）に必要な DDL が用意されており、初回実行時に呼び出して作成する想定です。監査用スキーマは `init_audit_schema` / `init_audit_db` を利用してください。

---

この README はコードベースの主要機能と使用方法をまとめたものです。実際の運用・デプロイ手順（kabuステーションとの連携、Slack通知、CI/CD、監視）は別途ドキュメント化することを推奨します。質問や補足があればお知らせください。