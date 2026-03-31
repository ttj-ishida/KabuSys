# KabuSys

日本株向けのデータプラットフォーム／自動売買補助ライブラリ。  
DuckDB を用いたデータ格納・ETL、J-Quants API クライアント、ニュース収集・NLP（OpenAI）連携、研究用ファクター計算、監査ログスキーマ等を備えたモジュール群です。

本 README はこのコードベースの概要、主要機能、セットアップ手順、使い方の例、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、ニュース収集と LLM を利用したセンチメントスコアリング、研究（ファクター計算・特徴量解析）、および取引監査ログ（発注〜約定のトレーサビリティ）を提供するライブラリ群です。  
設計上、バックテストでのルックアヘッドバイアスを避ける配慮があり、DuckDB を使った ETL / 永続化、OpenAI（gpt-4o-mini）を用いた JSON モードの LLM 呼び出し、J-Quants API の堅牢なレート制御・リトライを備えます。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（settings オブジェクト）
- データ取得（J-Quants）
  - 日足株価（OHLCV）、財務情報、上場銘柄情報、マーケットカレンダー取得
  - レートリミッタ、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（calendar, prices, financials）と品質チェックの一括実行
  - 差分取得、バックフィル対応、品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS 収集（SSRF 対策、gzip 限度、トラッキング除去、記事IDハッシュ化）
  - raw_news / news_symbols への冗長性を考えた保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、銘柄ごとのセンチメント（ai_scores）を保存
  - レート制限や 5xx 等の堅牢なリトライ
- 市場レジーム判定
  - ETF（1321）200 日 MA 乖離とマクロニュース LLM スコアの合成で日次の市場レジームを判定
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）、ファクター要約、Z スコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブルの DDL／初期化ユーティリティ
  - 監査用 DuckDB 初期化関数（init_audit_db / init_audit_schema）

---

## セットアップ手順

以下は開発・実行に必要な一般的な手順例です。環境に合わせて適宜調整してください。

1. Python 環境作成（推奨: 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（主要依存）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

3. 環境変数設定 (.env)
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な環境変数（本コードで必須/想定されている例）:

     - JQUANTS_REFRESH_TOKEN (必須: jquants 認証)
     - KABU_API_PASSWORD (必須: kabuステーション API パスワード)
     - SLACK_BOT_TOKEN (必須: Slack 通知等)
     - SLACK_CHANNEL_ID (必須)
     - OPENAI_API_KEY (LLM を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO

   - .env の読み込みは以下の優先順位:
     OS 環境変数 > .env.local > .env

   - なお、.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

4. DuckDB ファイルの準備
   - デフォルトの DuckDB パス: data/kabusys.duckdb（settings.duckdb_path）
   - 監査 DB を別ファイルで用意する場合: data/audit.duckdb 等

---

## 使い方（簡単な例）

以下は主要関数を呼ぶ際の基本的な利用例です。例は Python スクリプト内で実行する想定です。

- 共通準備

```python
import duckdb
from datetime import date
from kabusys.config import settings
```

- DuckDB 接続を開く（ファイルは settings.duckdb_path）

```python
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日が対象になる
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース NLP（特定日分のスコアリング）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数または api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 19))
print("書き込んだ銘柄数:", written)
```

- 市場レジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 19))
```

- 監査ログ DB 初期化（監査用 DuckDB を新規に作る）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルにアクセス可能
```

- 研究用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## 設定（.env の挙動と注意点）

- 自動ロード:
  - パッケージ読み込み時にプロジェクトルートを起点に .env / .env.local を自動で読み込みます。
  - 無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

- パースルールのポイント:
  - "export KEY=val" 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
  - クォートなし値では '#' が直前に空白/タブがある場合のみコメントとして扱います。

- settings オブジェクト:
  - from kabusys.config import settings で各種設定（トークン、DB パス、環境種別など）へアクセスできます。
  - settings.jquants_refresh_token 等は未設定時に ValueError を投げます（必須設定）。

---

## 開発 / テスト時の注意

- LLM 呼び出しやネットワーク要求が発生する関数は、ユニットテスト時にモック差し替えがしやすい設計になっています（内部の _call_openai_api や _urlopen 等を patch 可能）。
- 自動 .env ロードを無効化してテスト環境を制御するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックしています。テスト用 DB は ":memory:" も利用可能です。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py (再エクスポート)
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールはドキュメント文字列と詳細な実装注釈を含んでいるため、個別の機能はファイルヘッダや関数 docstring を参照してください。

---

## 参考: よく使う関数一覧

- ETL / データ:
  - kabusys.data.pipeline.run_daily_etl(conn, ...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)

- ニュース:
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)

- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究:
  - kabusys.research.factor_research.calc_momentum(...)
  - kabusys.research.factor_research.calc_volatility(...)
  - kabusys.research.factor_research.calc_value(...)
  - kabusys.research.feature_exploration.calc_forward_returns(...)
  - kabusys.data.stats.zscore_normalize(...)

- 監査:
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

---

## ライセンス / 貢献

（ここにライセンス情報・貢献ルール等を追記してください）

---

必要であれば、この README を元に具体的な実行スクリプト例、requirements.txt、CI 設定、あるいは各モジュールの API リファレンスを追加で作成します。どの情報を優先で補足したいか教えてください。