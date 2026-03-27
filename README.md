# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM によるニュースセンチメント、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定のトレーサビリティ）などを含みます。

主な設計方針は次の通りです。
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.now() を不用意に参照しない設計）
- DuckDB を中心としたローカルデータストア
- API 呼び出しはリトライ・レート制御を備える（J-Quants、OpenAI 等）
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（jquants_client）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質（quality）
  - 欠損、重複、スパイク、日付不整合の検出と QualityIssue レポート
- カレンダー管理（calendar_management）
  - 営業日判定 / 前後営業日取得 / カレンダーの夜間更新ジョブ
- ニュース収集（news_collector）
  - RSS 収集、前処理、記事ID 正規化（SSRF 対策やサイズ上限あり）
- ニュース NLP（ai.news_nlp）
  - ニュースを銘柄ごとにまとめて LLM に投げてセンチメント（ai_scores）を算出・保存
- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成してレジーム判定（bull / neutral / bear）
- リサーチ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン計算、IC / サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions を含む監査スキーマ生成・初期化ユーティリティ
- 共通ユーティリティ
  - 設定管理（config.Settings, .env 自動読み込み）、統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

前提
- Python 3.10+（型注釈で `|` を使用）
- Git 等の開発環境

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使ってください）。主に必要なもの:
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリ以外の依存が必要な場合は適宜追加

   例:
   ```
   pip install duckdb openai defusedxml
   # もしローカル開発インストールするなら:
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` として必要な環境変数を配置すると、自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（このプロジェクトで直接参照される代表的なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID — Slack の送信先チャネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV (development | paper_trading | live) — デプロイ環境
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY — AI 機能を使う場合に必要。score_news / score_regime 呼び出し時に引数で渡すことも可能。

   簡単な `.env` 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は Python REPL / スクリプトでの簡単な利用例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作られます
```

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメントを取得して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定済みであれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジーム判定を実行（market_regime テーブルへ保存）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査データベースの初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査スキーマが作成されます
```

6) RSS を取得する（記事の保存は別途 raw_news への INSERT が必要）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI API を呼ぶ関数（score_news, score_regime）は API キーを明示的に引数で与えるか、環境変数 OPENAI_API_KEY を設定してください。キー未設定だと ValueError が投げられます。
- J-Quants を使う ETL は `JQUANTS_REFRESH_TOKEN` が必要です（settings.jquants_refresh_token を参照）。

---

## よく使う関数（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
  - fetch_listed_info(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, ...)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(text)

---

## 環境変数 / 設定 (config.Settings)

config.Settings クラスは以下のプロパティを通じて設定値を提供します（一部抜粋）:

- jquants_refresh_token -> JQUANTS_REFRESH_TOKEN (必須)
- kabu_api_password -> KABU_API_PASSWORD (必須)
- kabu_api_base_url -> KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- slack_bot_token -> SLACK_BOT_TOKEN (必須)
- slack_channel_id -> SLACK_CHANNEL_ID (必須)
- duckdb_path -> DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- sqlite_path -> SQLITE_PATH (デフォルト: data/monitoring.db)
- env -> KABUSYS_ENV (development | paper_trading | live)
- log_level -> LOG_LEVEL

自動で .env/.env.local を読み込む仕組みがあり、読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要な Python モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（LLM）処理
    - regime_detector.py         — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                — ETL パイプライン
    - jquants_client.py          — J-Quants API クライアント / 保存処理
    - calendar_management.py     — マーケットカレンダー管理
    - news_collector.py          — RSS 収集・前処理
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore 正規化等）
    - etl.py                     — ETL 結果クラスの再エクスポート
    - audit.py                   — 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー

各モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理する設計です。

---

## トラブルシューティング / 注意点

- OpenAI / J-Quants の API キーが未設定の場合、該当関数は明示的にエラーを出します。環境変数を再確認してください。
- DuckDB の executemany は空リストバインドに制約があるケース（古いバージョン）があります。関数内で空リストはガードされていますが、問題が出る場合は DuckDB バージョンを確認してください。
- news_collector は RSS フィードに対して SSRF / Gzip Bomb 対策やサイズ上限を実装しています。大きなフィードや非標準フィードでは空結果が返ることがあります。
- audit.init_audit_schema は transactional=True を指定すると BEGIN/COMMIT を使って実行します（DuckDB のトランザクションの特徴に注意）。

---

## 貢献 / 開発

- コードスタイル・型注釈・小さな関数単位のユニットテストを推奨します。
- 外部 API を呼ぶ箇所はモック可能な設計（関数差し替えや patch）になっています。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると .env 自動読み込みを抑制できます。

---

README の内容はソースコードのコメント・ドキュメントに基づきまとめています。具体的な API の使用例や運用手順、.env.example の配布は実運用時に追記してください。