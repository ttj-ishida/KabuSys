# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants / JPX / RSS / OpenAI（LLM）など外部データを取り込み、DuckDB 上で ETL・品質チェック・ファクター計算・監査ログまで一貫して提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「日本株のデータ基盤と研究・自動売買ワークフローを安全かつ再現可能にする」ことです。  
特徴的な設計方針は以下です。

- DuckDB を中心としたローカルデータベース（ETL → 品質チェック → 研究）  
- J-Quants API から差分取得／ページネーション／トークン自動リフレッシュ対応  
- RSS ニュース収集と LLM を用いたニュースセンチメント（OpenAI）評価  
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）  
- 監査ログ（signal → order_request → execution のトレーサビリティ）  
- 自動 .env 読込（プロジェクトルートに .env / .env.local を置くだけで利用可能）

---

## 機能一覧

- データ取得・保存
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーを取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue レポート）
- ニュース収集 / NLP
  - RSS フィード取得、前処理、raw_news への保存、news_symbols との紐付け
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを合成して market_regime に書き込み（score_regime）
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算 / IC 計測 / ファクター統計サマリ
  - zscore_normalize（クロスセクション正規化）
- 監査ログ
  - signal_events / order_requests / executions テーブルを作成する init_audit_schema / init_audit_db

---

## セットアップ手順（開発向け）

前提: Python 3.10 以上（型ヒントの `X | None` を使用しているため）

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   ※実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。開発インストール:
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git ある場所 or pyproject.toml のある場所）に `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（または重要）な環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（省略時 development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（省略時 INFO）

データベースパス（デフォルト）:
- DUCKDB_PATH = data/kabusys.duckdb
- SQLITE_PATH = data/monitoring.db
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

DuckDB 接続を作り、ETL 実行・AI スコア算出・レジーム判定・監査初期化などを行う基本例を示します。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI キーは環境変数 OPENAI_API_KEY、または引数 api_key で渡せます
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- ETL 実行後に品質チェック結果を参照
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

- News Collector（RSS 取得）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

注意点:
- OpenAI を使う API はネットワーク失敗や解析エラー時にフェイルセーフとして 0.0 を返す設計ですが、APIキーが未設定だと ValueError が発生します。
- ETL / news / regime の各処理は「ルックアヘッドバイアス」を避けるため、内部で date.today() を直接参照しない設計になっています（target_date を明示することが推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS 取得／前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン/IC/統計解析ユーティリティ

---

## よくある質問 / 注意事項

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検索）を基準に行われます。テスト環境などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しはリトライ・バックオフを組み込んでいますが、API 利用量やレスポンス形式に依存するため管理には注意してください。
- DuckDB に対する executemany の空配列渡しは一部バージョンで制約があるため、内部で空チェックが入っています。
- 本ライブラリは「研究・データ基盤・監査ログ」に重点を置いており、実際のブローカー送信ロジック（kabu API への発注）や資金管理ルールは別モジュールで実装することを想定しています。

---

## 貢献 / 開発

- バグ報告、機能提案は Issue へお願いします。
- Pull Request の際はユニットテスト（モックによる外部 API 切り離し）を追加してください。
- セキュリティ: RSS パーサ / HTTP リクエスト周りは SSRF / XML Bomb 対策を組み込んでいますが、新規コード追加時も外部入力を厳格に扱ってください。

---

必要であれば、README に
- さらに詳細な API リファレンス（関数一覧・引数説明）
- サンプル .env.example
- 開発用の docker-compose / CI 設定例
を追加できます。どの情報を優先して追加しますか？