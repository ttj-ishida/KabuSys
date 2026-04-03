# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants（株価・財務・マーケットカレンダー）と連携する ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）、監査ログなどを含むモジュール群を提供します。

## 特徴（機能一覧）
- データ ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分/バックフィル、ページネーション、冪等保存（ON CONFLICT）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 & 前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols 保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを結合して LLM に投げ、センチメント（ai_scores）を取得する `score_news`
  - マクロ記事を用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）`score_regime`
  - JSON Mode + リトライ・バリデーション実装（フェイルセーフ設計）
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ / 流動性等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの初期化関数（冪等）
  - 発注フローの監査・追跡をサポート
- 設定管理
  - .env（プロジェクトルート）または環境変数から自動読み込み（無効化可）

## 動作環境（目安）
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai (v1 SDK 想定: OpenAI クラスを使用)
  - defusedxml
  - その他標準ライブラリ（urllib 等）

※ pyproject.toml や requirements.txt がある場合はそれを使ってください。

## セットアップ手順

1. リポジトリをクローン（省略可）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb openai defusedxml
   - （プロジェクト配布方法により）pip install -e . で開発インストール
4. 環境変数／.env の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須項目（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...（kabu API を使う場合）
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY=...
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

## 主要な使い方（コード例）

※ すべての操作は Python スクリプト / REPL 内で実行できます。DuckDB 接続には `duckdb.connect(path)` を使用します。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア（銘柄ごとに ai_scores を更新）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ma200 とマクロニュースを元に market_regime 書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査テーブルを作成）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 conn を使って監査テーブルへ書き込み等を行う
```

- RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])
```

- リサーチ / ファクター利用例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は dict のリスト
```

## 設定管理のポイント
- 環境変数は .env（プロジェクトルート）→ .env.local（上書き）→ OS 環境変数 の順でロードされます。自動ロードを防ぐには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主要な設定は `kabusys.config.settings` 経由で取得できます（例: settings.jquants_refresh_token）。
- `KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかで、無効値は例外になります。

## 注意事項 / 運用上の考慮点
- OpenAI や J-Quants の API 呼び出しはリトライやフェイルセーフを実装していますが、API キー・トークンの管理は厳重に行ってください。
- LLM を用いる機能は外部通信依存のため、オフライン環境やテスト時はモック（関数置換）することを想定しています（コード内にモックしやすいファサードを用意）。
- DuckDB の executemany は空リストの渡し方に制約がある箇所があるため、ライブラリ側で空チェックが実装されています。独自に利用する際も注意してください。
- 日付処理はルックアヘッドバイアス防止のため、内部で `date.today()` を不用意に参照しない設計になっています。バックテスト等で使用する際は `target_date` を明示してください。

## ディレクトリ構成（抜粋）
プロジェクトの主なファイル・モジュール構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — 市場カレンダーロジック（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（監査スキーマ作成 / init）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラ/バリュー等
    - feature_exploration.py     — 将来リターン / IC / summary 等
  - ai/、research/ のほか、strategy/、execution/、monitoring/ モジュール（初期エクスポート用）など

（実際のツリーはリポジトリを参照してください）

## テスト / モック
- OpenAI 呼び出しや HTTP リクエストはテスト時にモック可能な設計です。各モジュール内で API 呼び出しをラップしており、ユニットテストでは関数を patch して外部依存を排除してください。
- .env 自動ロードはテストの際に影響を与えることがあるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して挙動を固定できます。

---

さらに詳しい使い方や運用手順（デプロイ、監視、誤発注対策など）はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。README の補足や例を追加してほしい箇所があれば教えてください。