# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
DuckDB ベースのデータレイク、J-Quants からの ETL、ニュース NLP / LLM を使ったセンチメント評価、研究用ファクター計算、監査ログなどを提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保持する ETL パイプライン
- RSS ニュース収集および OpenAI（gpt-4o-mini）を用いたニュース／マクロセンチメント評価
- ファクター計算（モメンタム・バリュー・ボラティリティ等）および研究用ユーティリティ
- 取引フローの監査ログ（監査テーブル / 初期化ユーティリティ）
- データ品質チェック、マーケットカレンダー管理、ニュース収集に関する堅牢な実装

設計上の共通方針として、ルックアヘッドバイアス防止（バックテストに安全）、冪等性（DB 書き込み）、外部 API のリトライ・レート制御、失敗時のフェイルセーフを重視しています。

---

## 主な機能

- データ取得 / 保存
  - J-Quants からの株価日足、財務指標、JPX カレンダーの差分取得（ページネーション対応、トークンリフレッシュ、レート制限）
  - raw_prices / raw_financials / market_calendar 等への冪等保存（ON CONFLICT）
- ETL
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの一連処理
  - 個別 ETL：run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース（収集 / 分析）
  - RSS フィード収集（SSRF防御、URL 正規化、前処理）
  - OpenAI を用いた銘柄別ニュースセンチメント score_news
  - 市場レジーム判定 score_regime（ETF 1321 の MA200 とマクロセンチメントを合成）
- 研究用ユーティリティ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events, order_requests, executions）の初期化ユーティリティ

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK; 本コードでは OpenAI クライアントを使用)
- defusedxml
- その他標準ライブラリ

※実際の `pyproject.toml` / `requirements.txt` を用意している場合はそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ... && cd kabusys

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e .  （ローカル開発インストール）
   - もしくは必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルート（このパッケージを含むディレクトリ）に `.env` または `.env.local` を作成すると自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで使用）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須): J-Quants の refresh token
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime が使用）
     - KABU_API_PASSWORD: kabu API 用パスワード（発注系と統合する場合）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
     - SQLITE_PATH (任意): 監視用 SQLite のデフォルト data/monitoring.db
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など

---

## 使い方（簡単な例）

以下は主要 API を使う際のサンプルです。全ての操作は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を渡して実行します。

1) DuckDB 接続準備（デフォルト DB パスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（target_date は省略可で今日扱い）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント解析（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う場合は api_key=None
print(f"written {written} scores")
```

4) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ DB 初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# テーブルが初期化されます
```

6) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
momentum_records = calc_momentum(conn, d)
value_records = calc_value(conn, d)
vol_records = calc_volatility(conn, d)
```

7) ニュース収集（RSS フェッチ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# raw_news テーブルへの保存は別処理（ETL パイプラインや専用関数を用意してください）
```

注意:
- OpenAI を使う機能は OPENAI_API_KEY（環境変数）または関数引数で api_key を渡す必要があります。
- J-Quants API は JQUANTS_REFRESH_TOKEN が必須です（settings.jquants_refresh_token で参照）。
- 各関数はルックアヘッドバイアス防止のため internal で日付フィルタリングに注意した実装になっています。

---

## 重要な設計ノート / 実行時の注意

- .env 自動ロード:
  - packages/config.py はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み順は: OS 環境変数 > .env.local (override=True) > .env (override=False)
- OpenAI 呼び出し:
  - レスポンスのパースや API エラーはフォールバック（ゼロスコア等）をする実装で、部分失敗時にも他銘柄の処理を継続します。
  - テストでは内部の _call_openai_api をモックして API 呼び出しを差し替えられるよう設計されています。
- ETL:
  - 差分取得・バックフィル・品質チェックは個別に呼べます。run_daily_etl はそれらを統合して順次実行します。
- DuckDB への executemany の挙動（バージョン依存）に配慮して空パラメータの executemany を避ける実装がなされています。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 検出）、XML の安全パース（defusedxml）を実装しています。
  - jquants_client は API レート制限遵守のための RateLimiter とリトライを実装しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージメタ情報)
  - config.py  (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースセンチメント: score_news)
    - regime_detector.py  (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - pipeline.py         (ETL パイプライン: run_daily_etl 等)
    - etl.py              (ETLResult 再エクスポート)
    - jquants_client.py   (J-Quants API クライアント／保存ロジック)
    - news_collector.py   (RSS 取得・前処理)
    - calendar_management.py (マーケットカレンダー管理)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ: zscore_normalize)
    - audit.py            (監査ログテーブル定義 / 初期化)
  - research/
    - __init__.py
    - factor_research.py  (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - research/*（調査用ユーティリティ）
  - その他: strategy, execution, monitoring パッケージ（本 README のコード群と連携する想定）

各モジュールは docstring に機能説明と設計方針が記載されています。実装詳細は各ファイル内のコメントを参照してください。

---

## 開発／テスト

- 単体テストを書く際は、外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックしてください。コード内は各所でモック差し替えが想定されています（例: _call_openai_api, _urlopen）。
- .env の自動読み込みを無効にしてテスト用環境を整える場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- duckdb のインメモリ DB(":memory:") を使えば副作用のないテストが可能です。

---

## 最後に

この README は提供されたコードベースの主要機能と使い方を要約したものです。実運用時は各種環境変数の管理（シークレット管理）、OpenAI / J-Quants の API 利用制限、監査ログ・エラーハンドリング方針を運用ルールとして確立してください。

質問や追加のドキュメント化（例: API リファレンス、運用手順書、.env.example の作成）をご希望であればお知らせください。