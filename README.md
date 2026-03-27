# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI を組み合わせて、データ取得（ETL）・データ品質チェック・ニュースセンチメント解析・市場レジーム判定・監査ログ管理などを提供します。

主な設計方針:
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() に依存しない）
- DuckDB を中心としたローカルデータレイヤ
- API 呼び出しに対するリトライ・レート制御・フェイルセーフ処理
- 冪等性（ETL・保存処理は ON CONFLICT/UPSERT を利用）
- LLM 呼び出しは JSON Mode（厳密な JSON 出力）で安全に扱う

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）・財務データ・JPX カレンダーを差分取得（ページネーション対応、レートリミット）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue として問題を収集

- ニュース収集 / 前処理
  - RSS フィードの安全な取得（SSRF 対策、gzip 上限チェック）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成・テキスト前処理

- ニュース NLP / センチメント解析
  - OpenAI（gpt-4o-mini）で銘柄単位のセンチメントを評価し ai_scores に書き込む
  - バッチ（最大20銘柄）での処理、リトライ・レスポンス検証・スコアクリップ

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して
    日次で regime（bull / neutral / bear）を判定して market_regime に保存

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - order_request_id による冪等性と完全な追跡性を確保

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（スピアマン ρ）、ファクターサマリ、Zスコア正規化

---

## 必要条件

- Python 3.10 以上（型ヒントに union 型 (X | Y) を使用）
- 必要な主要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/Mac)
   - .venv\Scripts\activate     (Windows)

3. パッケージのインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - pip install -e .   （ローカルパッケージとしてインストールする場合）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（少なくとも以下を設定）:
     - JQUANTS_REFRESH_TOKEN
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（score_news / score_regime 実行時に引数で渡すことも可能）

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

注意:
- .env のパースは quotes / コメント / export プレフィックスに対応しています。
- OS 環境変数が優先され、`.env.local` は `.env` より優先して上書きされます。

---

## 使い方（主要な例）

以下は一例です。実行は Python REPL / スクリプト内で行います。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックを含む）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に保存:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境変数に必要
print(f"written {n} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit）スキーマを初期化:
```python
from kabusys.data.audit import init_audit_db
# ファイル DB を作成してスキーマを作成
audit_conn = init_audit_db("data/audit.duckdb")
```

- J-Quants から株価を直接取得（ETL を使わずに）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
data = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

- ニュース RSS を取得（保存は別処理で実装）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

---

## 設定（settings）

kabusys.config.Settings を通じて以下のプロパティを取得できます（一部）:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: デフォルト http://localhost:18080/kabusapi
- slack_bot_token, slack_channel_id: Slack 通知用（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite（デフォルト data/monitoring.db）
- env: KABUSYS_ENV（development|paper_trading|live）
- log_level: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- is_live / is_paper / is_dev: env 判定ヘルパ

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 注意点・設計メモ

- LLM（OpenAI）呼び出しは JSON Mode を用いて厳密な出力を期待します。レスポンスのパースに失敗した場合はフェイルセーフでスコア 0.0 または処理スキップします。
- J-Quants クライアントは内部で固定間隔のレート制御（120 req/min）とリトライ・トークン自動リフレッシュを実装しています。
- ETL / 保存処理はできるだけ冪等に保たれており、部分失敗時にも既存データを不必要に削除しない工夫があります。
- DuckDB のバージョンによる executemany の空リスト挙動などの互換性に注意した実装があります。
- ニュース収集は SSRF 対策・受信サイズ上限・XML の脆弱性防御を備えています。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM センチメント解析（score_news）
  - regime_detector.py  — ETF MA とマクロニュースを組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（fetch_*/save_*）
  - pipeline.py         — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 収集・前処理
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - quality.py          — データ品質チェック（QualityIssue）
  - audit.py            — 監査ログスキーマ初期化
  - stats.py            — zscore_normalize 等
- research/
  - __init__.py
  - factor_research.py  — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

（上記は主要モジュールの抜粋です。詳細はソース内のドキュメント文字列を参照してください。）

---

## 開発・テストについて

- LLM や外部 API 呼び出しはモックしやすいように各モジュール内で分離されています（例: _call_openai_api を unittest.mock.patch で差し替え可能）。
- テスト時に自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の一時接続は ":memory:" を渡すことでインメモリ DB を利用できます（例: audit.init_audit_db(":memory:")）。

---

この README はコードベースの主要機能と使い方を概説しています。詳細な API 仕様や追加の実行スクリプト、CI 設定などはプロジェクトのドキュメント / docstrings を参照してください。問題・改善提案があれば Issue を立ててください。