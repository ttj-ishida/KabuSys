# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL、データ品質チェック、ファクター計算、ニュースNLP、LLMベースの市場レジーム判定、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集〜前処理〜リサーチ〜自動売買実行までを支援する Python ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- DuckDB を用いたローカルデータベース保存と品質チェック
- ニュース記事の収集・前処理・LLM による銘柄センチメント評価（ai_score）
- LLM（OpenAI）と価格指標（例：ETF 1321 の MA200 乖離）を組み合わせた「市場レジーム判定」
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 発注〜約定までの監査ログスキーマ（監査・トレーサビリティ）
- 実行環境設定の管理（.env 自動ロード）

本リポジトリはライブラリコード（src/kabusys）を中心に設計されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・ページング・トークン自動リフレッシュ・レート制御）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）

- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄センチメント → ai_scores）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリー、Zスコア正規化）

- config
  - .env / 環境変数の自動ロードと Settings API（settings オブジェクト）

---

## セットアップ手順

1. Python 環境を作成（例: Python 3.10+ 推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   本リポジトリに requirements.txt がない想定のため、最低限必要となるパッケージ例を示します。

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※実際にはプロジェクトの extras やテスト用依存関係がある場合はそれらも追加してください。

3. パッケージを編集モードでインストール（任意）

   ソースから直接 import して使う場合:

   ```bash
   pip install -e .
   ```

4. 環境変数（.env）を準備

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   代表的な環境変数（例）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_* を使う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（省略可）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment (development|paper_trading|live)
   - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
   - KILL_FLAG_CLEAR_ON_START, PID_FILE_PATH, その他の監視設定

   .env のフォーマットは標準的な KEY=VALUE、export KEY=VALUE、クォート付き値などに対応します。

---

## 使い方（例）

以下は主要機能の利用例です。全ての操作は Python スクリプトやジョブから利用できます。

- DuckDB 接続を作成して ETL を実行する

```python
import datetime
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
# ETL を実行（target_date を指定、省略時は今日）
res = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄ごと）をスコアリングして ai_scores に保存

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は duckdb 接続
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームをスコアリングして market_regime テーブルへ書き込む

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY を参照
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# audit 用に別 DB を作ることも可。ここでは設定値を利用する例
audit_conn = init_audit_db(settings.duckdb_path)
# テーブルが作成され UTC タイムゾーンが設定されます
```

- 研究（ファクター計算・IC 等）

```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

date0 = datetime.date(2026, 3, 20)
momentum = calc_momentum(conn, date0)
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])

ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- RSS ニュース取得（ニュースコレクタの下位 API）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
# 生記事から raw_news へ保存するロジックはプロジェクト側でトランザクション組んで実行してください
```

---

## Settings / 環境変数

設定は `kabusys.config.settings` オブジェクトからアクセスします。例:

```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を持つディレクトリ）にある `.env` および `.env.local` が自動読み込みされます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須系 (少なくとも ETL や API 呼び出しで必要になるもの)
- JQUANTS_REFRESH_TOKEN（J-Quants 用）
- OPENAI_API_KEY（AI スコアリング関数を使う場合）
- KABU_API_PASSWORD（kabu API を使う場合）

その他の設定は `src/kabusys/config.py` 内のプロパティを参照してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル・ディレクトリ構成（src 内）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ pipeline.py
   │  ├─ jquants_client.py
   │  ├─ calendar_management.py
   │  ├─ news_collector.py
   │  ├─ quality.py
   │  ├─ stats.py
   │  ├─ audit.py
   │  └─ etl.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ research/...
```

各モジュールは責務が明確に分かれており、DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る関数が多数あります。これにより、テスト時に in-memory DB（":memory:"）を用いた検証が可能です。

---

## 注意事項 / 動作設計上の留意点

- ルックアヘッドバイアス対策: 多くの関数が内部で `datetime.today()` / `date.today()` に依存せず、呼び出し側が `target_date` を与える設計です。バックテスト用途では過去データのみを使うよう注意してください。
- J-Quants クライアントはレート制御とリトライを実装していますが、API 利用制限は環境に合わせて監視してください。
- OpenAI を用いる部分は API エラーやパース失敗時にフェイルセーフ（通常 0.0 にフォールバック）を採用しています。料金・リクエスト数に注意してください。
- news_collector は SSRF 等の脆弱性対策（リダイレクト検査・プライベートIPブロック・受信サイズ制限等）を実装していますが、運用時はソースの追加やフィード先の安全性を確認してください。
- DuckDB の executemany 空リストの挙動やバージョン差に注意し、保存処理は各関数の前提に従ってください。

---

## 貢献・テスト

- 単体テスト・CI 設定は本説明に含まれていません。機能追加や修正の際はユニットテスト（特に DB 周りや外部 API 呼び出しのモック）を追加してください。
- OpenAI / J-Quants API など外部希少性のある箇所は patch を使ってモック化してテストすることを推奨します（実際のコードでもそのように設計されています）。

---

必要であれば、README に含める具体的な .env.example、より詳しいサンプルジョブスクリプト（cron / systemd 用）や Dockerfile・GitHub Actions の CI 設定例も作成します。どれを優先しますか？