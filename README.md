# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュース解析、ファクター計算、監査ログ（注文→約定トレーサビリティ）、マーケットカレンダー管理などを含みます。

---

## 概要

KabuSys は日本株のアルゴリズム売買に必要なデータ基盤・研究ツール・監査機能を提供する Python パッケージです。主要な設計方針は以下のとおりです。

- Look-ahead bias を避ける（内部で datetime.today()/date.today() を直接参照しない等）
- ETL と品質チェックを分離して堅牢に実装
- J-Quants API との相互作用はリトライ・レートリミット制御付き
- ニュース解析は OpenAI（gpt-4o-mini）を用いる（JSON Mode 使用）
- DuckDB をデータストア／監査ログ用 DB として利用
- 冪等性（ON CONFLICT / idempotent）を重視

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch / save）：価格、財務、上場銘柄、マーケットカレンダー
  - ETL パイプライン（run_daily_etl / run_prices_etl / ...）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、前処理）
  - 監査ログ初期化・DB（order_requests / executions / signal_events）
- ai
  - news_nlp.score_news: ニュースを銘柄別に集約して LLM に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- config
  - .env / 環境変数自動ロード（プロジェクトルート検出、.env/.env.local を読み込み）
  - Settings オブジェクトを通じた設定参照

---

## 必要条件

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

開発・運用環境に応じて追加パッケージ（例: slack-sdk 等）を使う場合があります。

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用にパッケージ全体をインストールする場合、プロジェクトに setup.py/pyproject.toml があれば:
# pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env または環境変数から設定を読み込みます（プロジェクトルートに .git または pyproject.toml があると自動検出）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しに使用される API キー（score_news / score_regime で省略可）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

設定はコード内で `from kabusys.config import settings` を通じて参照できます。

注意: 必須のキーが未設定の場合、Settings のプロパティが ValueError を送出します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ワークツリーに配置
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くのが簡単）
   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```
5. DuckDB スキーマ / 監査 DB 初期化（必要に応じて）

---

## 使用方法（コード例）

以下は主要なユースケースの簡単な例です。実行前に環境変数を設定してください。

- DuckDB 接続作成:
```
import duckdb
conn = duckdb.connect(str("data/kabusys.duckdb"))
```

- ETL（日次パイプライン）を実行:
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコアリング（ai_scores へ書き込み）:
```
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```
score_news は OpenAI API キーを引数 `api_key` で渡せます（省略時は OPENAI_API_KEY 環境変数を参照）。

- 市場レジーム判定:
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（専用 DB を作る場合）:
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 返された conn_audit は監査テーブルが作成済み
```

- カレンダー更新バッチ（J-Quants から）:
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved {saved} calendar entries")
```

- 設定の参照:
```
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

テスト時のヒント:
- OpenAI への呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替えてテスト可能です（news_nlp, regime_detector それぞれ独立実装）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py (パッケージエントリ、__version__)
- config.py (環境変数 / .env 自動ロード / Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュースの LLM スコアリング -> ai_scores)
  - regime_detector.py (MA200 とマクロニュースを合成して market_regime)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、fetch/save)
  - pipeline.py (ETL パイプライン、run_daily_etl など)
  - etl.py (ETLResult 再エクスポート)
  - calendar_management.py (market_calendar 管理、営業日ロジック)
  - news_collector.py (RSS 収集・前処理・SSRF対策)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等統計ユーティリティ)
  - audit.py (監査ログスキーマ初期化 / init_audit_db)
- research/
  - __init__.py
  - factor_research.py (momentum/value/volatility)
  - feature_exploration.py (forward_returns, calc_ic, factor_summary, rank)

各モジュールは docstring に設計方針・処理フロー・想定テーブルを詳述しています。実行時のログ出力やエラー処理も内蔵しています。

---

## 運用上の注意

- OpenAI への API 利用はコストが発生します。batch サイズや文字数制限、リトライ戦略は実装に組み込まれていますが、実環境ではレートや料金管理が必要です。
- J-Quants API はレート制限があるため、_RateLimiter により制御しています。認証トークンの管理（リフレッシュ）を確実に行ってください。
- 本ライブラリは多数のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions など）を前提とします。テーブルスキーマ準備やスキーマ移行は運用側で管理してください（各関数は既存テーブルを前提に動作します）。
- DuckDB の executemany の挙動やバージョン差異に留意してください（pipeline.py 内にある注意参照）。

---

## ライセンス

このリポジトリ内に明示的なライセンスファイルがない場合は、利用前にライセンスを確認してください。

---

README は以上です。必要であれば、導入手順の詳細（requirements.txt / pyproject.toml の例、サンプル .env.example、初期スキーマ作成 SQL など）を追記します。どの部分を詳しく書きますか？