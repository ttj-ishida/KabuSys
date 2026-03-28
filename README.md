# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスの排除（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を主要なローカルデータストアとして利用
- API 呼び出しはレート制御・リトライ・フォールバックを備える
- 冪等性を重視した DB 保存（ON CONFLICT / DELETE+INSERT 等）
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / カレンダー）
  - ETL パイプライン（差分取得、保存、品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）
- ニュース収集・前処理
  - RSS 取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック
- ニュース NLP / AI
  - 銘柄毎ニュースセンチメント（gpt-4o-mini を想定） -> ai_scores へ保存（score_news）
  - マクロニュースと ETF MA200 乖離を合成した市場レジーム判定（score_regime）
  - OpenAI API 呼び出しはリトライや JSON パースフォールバックを内蔵
- リサーチ / ファクター
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue オブジェクト）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化補助
  - init_audit_db / init_audit_schema による冪等初期化
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings API

---

## 動作要件（推奨）

- Python 3.10+
- 主要依存（抜粋）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

必要に応じて pyproject.toml / requirements.txt を用意して依存を管理してください。

---

## セットアップ手順

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（ローカル開発）
   - pip install -e .

   または依存を個別にインストール:
   - pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動的に読み込まれます（.git または pyproject.toml があるディレクトリをルートと判定）。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

必須環境変数（README 用サンプル、実運用では各サービスから取得してください）:
- JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- SLACK_BOT_TOKEN=（Slack bot token）
- SLACK_CHANNEL_ID=（通知先チャネルID）
- OPENAI_API_KEY=（OpenAI API キー） — AI 機能を使う場合

オプション（デフォルトあり）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

例: .env
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

このライブラリは CLI ではなく Python API として呼び出します。以下は主要な操作の例です。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores への書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（market_regime テーブルへ）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って後続処理で監査ログを書き込む
```

- RSS フェッチ
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しはネットワーク依存・課金対象です。テスト時は内部の _call_openai_api をモックすることを推奨します（コード内でその旨コメントあり）。
- ETL / API 呼び出しはリトライやレート制御を行いますが、適切な API キー・帯域を用意してください。

---

## 主要 API（抜粋）

- kabusys.config.settings: 環境変数からの設定取得（.jquants_refresh_token など）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（抜粋）

ここでは主要なモジュールと役割を示します（パッケージ root = src/kabusys）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメントの集約と OpenAI 呼び出し
    - regime_detector.py      — ETF MA200 とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得／保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理・判定ロジック
    - news_collector.py       — RSS 取得と前処理（SSRF 対策）
    - stats.py                — 統計ユーティリティ（zscore 正規化等）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログの DDL / 初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - ai/, data/, research/ 以下にさらに細かい実装とヘルパー群が存在します。

---

## 開発・運用上の注意

- 環境（KABUSYS_ENV）: production（live）で実際の発注を伴う場合は十分なレビューと安全対策を行ってください。設定値は環境変数で切り替えます。
- テスト: OpenAI / HTTP 呼び出しはモック化して単体テストを行ってください。コード内にモック可能な箇所（_call_openai_api 等）があります。
- DB スキーマ: DuckDB のバージョン差（executemany 空リストの挙動等）に注意してください。pipeline モジュール内に互換性対策が含まれています。
- セキュリティ: RSS 取得時の SSRF 対策や defusedxml を使用した XML パース等、外部データ取得に伴う脅威軽減が組み込まれていますが、運用環境に応じた監査と制限を行ってください。

---

必要に応じて README の補足（CLI、systemd タスク、Airflow ジョブ定義、運用ガイド、スキーマ定義の詳細等）を追加できます。追加したいトピックがあれば教えてください。