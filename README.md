# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API からのデータ収集（ETL）、ニュースの NLP 評価（OpenAI）、市場レジーム判定、因子計算、データ品質チェック、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された内部ライブラリです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得および DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理、OpenAI を使ったニュースベースのセンチメントスコアリング
- ETF 200日移動平均とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定
- 因子（モメンタム・バリュー・ボラティリティ等）の計算・解析ツール（Research）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注／約定を辿るための監査ログスキーマ（DuckDB）

設計方針として「ルックアヘッドバイアス回避（target_date ベースの処理）」「ETL の冪等性」「API 呼び出しのリトライとレート制御」「外部依存を最小化（SQL + 標準ライブラリ）」が重視されています。

---

## 主な機能

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース処理・NLP
  - RSS 取得・前処理（kabusys.data.news_collector）
  - 銘柄ごとのニュースセンチメント計算（kabusys.ai.news_nlp.score_news）
- マーケットレジーム判定
  - ETF 1321 の MA200 乖離 + マクロニュース LLM スコアを合成（kabusys.ai.regime_detector.score_regime）
- 研究（Research）
  - モメンタム／ボラティリティ／バリュー因子計算（kabusys.research）
  - 将来リターン計算、IC、統計サマリ等
- データ品質チェック（kabusys.data.quality）
- 監査ログスキーマ初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
- マーケットカレンダー管理（kabusys.data.calendar_management）

---

## 依存関係（主なもの）

- Python 3.10+（| 型注釈などの使用から推奨）
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外の追加が必要な場合は適宜インストール）

※プロジェクトによってはさらに slack SDK や kabu API ライブラリ等が必要です（環境変数や機能に依存）。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. パッケージを編集モードでインストール（任意）
   - pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動ロードされます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# DB パス等（デフォルト値あり）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ワークフロー例）

以下はライブラリの代表的な呼び出し例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続と日次 ETL の実行
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キーは環境変数 または api_key 引数で指定）
```
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジーム判定
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査データベース初期化（約定監査テーブルを作る）
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して発注/約定ログを記録可能
```

- カレンダー・営業日確認
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS フィード取得（ニュース収集ユーティリティ）
```
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

テスト時のヒント:
- OpenAI 呼び出しはモジュール内の _call_openai_api を patch してモックできます（unit tests で想定）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能等で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定は .env / .env.local で管理できます（.env.local は .env 上書き）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に実装されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数管理・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py            # 市場レジーム判定（MA200 + LLM）
  - data/
    - __init__.py
    - calendar_management.py        # マーケットカレンダー管理
    - etl.py                        # ETL インターフェース再エクスポート
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - stats.py                      # 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
    - jquants_client.py             # J-Quants API クライアント（fetch/save）
    - news_collector.py             # RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py            # モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        # 将来リターン・IC・統計サマリ等

（上記以外に strategy/execution/monitoring 等のモジュール群が __all__ に想定されています）

---

## 開発・運用上の注意

- ルックアヘッドバイアス回避: 多くの関数は内部で date パラメータを受け取り、datetime.today() を直接参照しない実装です。バックテストや再現性のために target_date を明示してください。
- OpenAI 呼び出し: gpt-4o-mini 等のモデルを JSON mode で使用します。API の失敗時はフェイルセーフ（スコア0で継続）する設計ですが、API キーの管理と利用料に注意してください。
- J-Quants API のレート制御: 内部に RateLimiter を実装済み（120 req/min を遵守）。
- DuckDB に対する executemany の挙動やバージョン差異に注意（コード中に互換性対策あり）。
- ニュース RSS 処理は SSRF 対策・gzip サイズチェック等の安全対策を実装していますが、運用環境のネットワーク制約やフィード供給元の仕様に注意してください。
- 監査ログは削除を前提としません（immutable な監査証跡）。

---

## 参考 / 次の作業

- README に追記する項目（デプロイ手順、CI、ロギング設定、詳細な API 使用例、スキーマ定義・DDL）はプロジェクトの運用ポリシーに合わせて拡充してください。
- 実運用での live 環境では KABUSYS_ENV=live を使用し、paper_trading モードなど安全対策を組み込んでください。

---

この README はコードベースの docstring と実装に基づいて作成しています。さらに詳細な使い方や API 仕様が必要であれば、用途（ETL、研究、発注等）ごとにサンプルや README を分割して作成できます。必要なら続けて作成します。