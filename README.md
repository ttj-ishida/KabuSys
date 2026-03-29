# KabuSys

日本株向けの自動売買・データプラットフォーム用 Python パッケージ群です。  
ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・自動売買の基盤機能をまとめたライブラリです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- ニュース収集（RSS）と LLM を用いた銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ用テーブルと初期化）
- 設定管理、環境変数ロード、DB 初期化ユーティリティなど

設計上の特徴:
- DuckDB を主要なローカルデータストアとして利用
- OpenAI（gpt-4o-mini） をニュース NLP／マクロセンチメントに使用（JSON Mode）
- Look-ahead バイアスに配慮（内部で date.today()/datetime.today() を参照する処理を避ける）
- 冪等性（DB への保存は ON CONFLICT / DELETE→INSERT を用いて安全に上書き）
- フェイルセーフ: API 失敗時はスコアを中立にフォールバックする実装が多い

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - カレンダー管理・営業日ユーティリティ（is_trading_day, next_trading_day, など）
  - ニュース収集（RSS -> raw_news / news_symbols）
  - データ品質チェック（missing / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF（1321）MA とマクロニュースを合成して market_regime テーブルへ書き込む
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定管理（settings オブジェクト）
  - 自動 .env 読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## セットアップ手順

以下は開発環境での基本的なセットアップ手順例です。

前提:
- Python 3.10+
- Git
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース など）

1. リポジトリをクローンしてパッケージをインストール（編集可能モードを推奨）

   ```bash
   git clone <repository-url>
   cd <repository-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"     # または最低限: pip install -e .
   ```

   ※ requirements はリポジトリに合わせて用意してください。基本的に必要なライブラリ:
   - duckdb
   - openai (公式 SDK)
   - defusedxml
   - その他標準ライブラリのみを使う実装が多いです

2. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を作成すると自動でロードされます（読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（実運用時）
   - SLACK_BOT_TOKEN: Slack 通知に使うボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しで未指定時に使用）
   - （オプション）DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL

   例: .env（簡易）

   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベースディレクトリ作成（必要に応じて）

   DuckDB のデフォルトパスは `data/kabusys.duckdb`（settings.duckdb_path）です。`kabusys.data.audit.init_audit_db` は親ディレクトリを自動作成しますが、一般的に `data/` を作成しておくとよいです。

---

## 使い方（主要なユースケース）

例では DuckDB 接続を用いた関数実行方法を示します。実際は適宜ロギング設定や例外処理を追加してください。

1. DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメント（AI）スコアリング

score_news は raw_news/news_symbols/ai_scores を操作します。OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡します。

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"{written} 銘柄のスコアを書き込みました")
```

3. 市場レジーム判定（ETF 1321 MA + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4. 監査DBの初期化（専用 DB を作成してスキーマを初期化）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログを書けるようになります
```

5. 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 設定と環境変数の詳細

設定は `kabusys.config.settings` 経由で参照できます。重要なプロパティ:

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (デフォルト: data/kabusys.duckdb)
- settings.sqlite_path (デフォルト: data/monitoring.db)
- settings.env (development / paper_trading / live)
- settings.log_level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- settings.is_live / is_paper / is_dev

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` と `.env.local` を自動ロードします。
- 読み込み優先は OS 環境変数 > .env.local > .env
- 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利）。

必須環境変数が欠けると `settings` のプロパティを参照したときに `ValueError` が発生します。

---

## テスト / モックのヒント

- OpenAI 呼び出しは内部で `_call_openai_api` を経由しており、ユニットテストでは該当関数を patch してレスポンスを制御できます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", new=mock_fn)
  - regime_detector でも同様に `_call_openai_api` をモックできます（両モジュールは意図的に実装分離されています）。
- J-Quants クライアントはネットワークアクセスを行うため、ETL のユニットテストでは `kabusys.data.jquants_client._request` や fetch_* をモックしてください。
- ニュース収集の RSS フェッチ (`fetch_rss`) は内部で URLopen をラップしており、`kabusys.data.news_collector._urlopen` をモックすると RSS レスポンスを差し替えられます。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

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
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在すればモニタリング関連)
  - strategy/ (戦略レイヤーがある場合)
  - execution/ (約定/ブローカー連携がある場合)

また README に含まれる機能は上記モジュールに対応しています。実際のリポジトリは top-level に pyproject.toml や .git を含む想定です。

---

## 注意点 / 運用上の留意事項

- OpenAI（LLM）呼び出しはコストとレイテンシが発生します。プロダクションではレート制御やキャッシュを検討してください。
- J-Quants API はレート制限（120 req/min）を守る実装が組み込まれていますが、運用環境での負荷に応じて適切に設定してください。
- データ品質チェックは ETL の最後に実行され、エラー／警告を集約して返します。品質問題が見つかった場合はログと結果を確認して運用判断してください。
- 監査ログテーブルは削除を想定していない（監査用途）ため、運用での保守ポリシーを検討してください。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかを指定してください。live 環境では発注ロジック等を厳格に扱うべきです。

---

## トラブルシューティング

- 環境変数エラー: settings のプロパティ参照で ValueError が出る場合、.env を確認して必須変数が設定されているか確認してください。
- DuckDB 接続・スキーマ不一致: ETL や audit 初期化前に適切なスキーマが作成されていることを確認してください。audit.init_audit_db はスキーマを作成します。
- OpenAI パースエラー: LLM の出力を厳密な JSON として期待していますが、実際にはエラーや余計なテキストが含まれる場合があります。該当モジュールはパース失敗時にスコアを中立にフォールバックするため、ログを確認してください。

---

この README はコードコメントと設計ドキュメントの内容を要約したものです。より詳細な設計や利用方法は各モジュールの docstring を参照してください。必要であれば README にサンプルワークフロー（cron ジョブ、Airflow 連携例、Slack 通知設定等）を追記できます。必要な情報があれば教えてください。