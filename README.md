# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ用スキーマなどを提供します。

主に研究（research）、データ基盤（data）、AI（news sentiment / regime）を切り分けたモジュール構成で、DuckDB を用いたローカルデータベース操作を前提としています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダー等の差分 ETL を行い DuckDB に格納する
- RSS ベースのニュース収集と前処理・SSRF 対策
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄単位）およびマクロセンチメントからの市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）および特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引監査ログ用スキーマ（signal → order_request → execution の追跡）

設計上のポイント:
- ルックアヘッドバイアス回避（関数は date/target_date を明示的に受け取る）
- DuckDB を中心に SQL と Python を併用
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフを実装

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのセンチメント）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースで判定）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env / 環境変数の自動読み込みと Settings（必須設定の検査・型変換）

---

## セットアップ手順

1. リポジトリをクローン／パッケージを配置
2. Python 3.10+（typing の | 型注釈を使用）の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml
   - 必要に応じて他の HTTP ライブラリやテスト用パッケージを追加
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くことで自動読み込み）
   - 必須項目や推奨例は後述の「環境変数（.env 例）」参照
5. DuckDB 用ディレクトリを作成（settings.duckdb_path の親ディレクトリ）
   - 例: mkdir -p data

補足:
- 自動で .env を読み込む仕様（config.py）。テストや一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 利用部分は API キーを環境変数 OPENAI_API_KEY で渡すか、各 API 呼び出しで明示的に api_key を渡せます。

---

## 使い方（主要 API / 例）

以下は最低限の利用例です。詳細は各モジュールの docstring を参照してください。

前提:
- DuckDB 接続（duckdb.connect(...)）を作成
- 必要な環境変数を設定（J-Quants トークン、OpenAI キーなど）

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（ai.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続、OPENAI_API_KEY を環境変数に設定している前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
```

4) 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
# OPENAI_API_KEY が必要（引数 api_key でも可）
score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算（research）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

6) 監査 DB 初期化（独立した監査用 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/monitoring.db")
# audit_conn に対して監査テーブルが初期化される
```

注意:
- OpenAI への呼び出しは料金が発生します。API キー、モデル、呼び出し頻度に注意してください。
- J-Quants API の利用には別途アカウント・リフレッシュトークンが必要です。

---

## 環境変数（.env 例）

config.Settings により自動的に .env / .env.local をロードします。必須のキーは .env.example を参考に設定してください。最小構成例:

.env
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API（もし使用する場合）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack 通知（必要時）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境・ログレベル
KABUSYS_ENV=development          # development | paper_trading | live
LOG_LEVEL=INFO
```

ポイント:
- settings.jquants_refresh_token / slack_* / KABU_API_PASSWORD は Settings で必須取得を行います。未設定だと ValueError を発生させます。
- 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

以下は主要ファイル / ディレクトリの概要（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         -- ニュースセンチメントの生成 (score_news)
  - regime_detector.py  -- マクロ + MA による市場レジーム判定 (score_regime)
- data/
  - __init__.py
  - jquants_client.py   -- J-Quants API クライアント（fetch / save）
  - pipeline.py         -- ETL パイプライン (run_daily_etl 等)
  - etl.py              -- ETL の公開型再エクスポート（ETLResult）
  - news_collector.py   -- RSS 取得・前処理（SSRF 対策等）
  - calendar_management.py -- 市場カレンダー管理（営業日判定など）
  - quality.py          -- データ品質チェック
  - stats.py            -- 汎用統計ユーティリティ（zscore_normalize）
  - audit.py            -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py  -- momentum/value/volatility の計算
  - feature_exploration.py -- 将来リターン / IC / サマリー 等

（実際の追加ユーティリティ・クライアントはコードベースを参照）

---

## 補足・運用上の注意

- OpenAI 呼び出し部分はリトライ・フォールバックを実装していますが、API レートや費用には十分注意してください。
- ETL 実行中は J-Quants のレート制限を尊重するため内部でレートリミッタを用いています。
- データ品質チェックは Fail-Fast ではなく問題を列挙する方式です。ETL の成否判断は呼び出し元で行ってください。
- DuckDB を用いた executemany の仕様差異（空リストの扱いなど）に注意して実装されています。

---

この README はコードベースの概要と代表的な運用方法をまとめたものです。詳細な設計や利用法は各モジュールの docstring / コメントを参照してください。必要であれば README に追加すべき項目（例: CI の実行例・テスト方法・開発ルール等）を教えてください。