# KabuSys

日本株向け自動売買 / リサーチ / データプラットフォーム用ライブラリ。  
DuckDB をデータレイヤに、J-Quants からの ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダーの差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄毎 / マクロ）
- ファクター計算（Momentum / Value / Volatility など）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保存する DuckDB スキーマ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴：
- ルックアヘッドバイアス防止（内部で date.today() や datetime.today() に依存しない設計）
- DuckDB を用いたローカル高速分析・永続化
- 冪等性（ON CONFLICT / primary key ベースの upsert）を重視
- API 呼び出しに対するリトライ / レート制御 / フェイルセーフ設計

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save_* 関数、トークン自動更新、レートリミット管理）
  - market calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector（RSS 収集、URL 正規化、前処理、SSRF 対策）
  - quality（データ品質チェック群）
  - audit（監査ログスキーマ初期化、init_audit_db）
  - stats（zscore_normalize など共通統計ユーティリティ）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄ごとの NLP スコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — マクロ + ETF MA200 乖離で市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラスによる環境変数ラッパー（自動 .env ロード機能あり）

---

## セットアップ手順

必要な Python バージョン: 3.9+（typing|annotations の使用を想定）  
以下は例です。プロジェクトの実際の requirements.txt を参照してください。

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   実際のプロジェクトでは追加パッケージ（requests 等）が必要な場合があります。パッケージ管理ファイルがある場合はそちらを使用してください。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると、自動でロードされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD：kabuステーション API 用パスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN：Slack 通知を使う場合
   - SLACK_CHANNEL_ID：Slack 通知先チャンネルID
   - OPENAI_API_KEY：OpenAI 呼び出しを行う場合（score_news/score_regime で不要なら引数でも指定可）

   任意 / デフォルトあり:
   - KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH：デフォルト data/kabusys.duckdb
   - SQLITE_PATH：デフォルト data/monitoring.db

例（.env のサンプル）:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（Quick start）

以下は代表的な利用例です。DuckDB 接続 (duckdb.connect(...)) を渡して各 API を呼び出します。

1) 日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- run_daily_etl はカレンダー -> 株価 -> 財務 -> 品質チェック（オプション）の順で処理します。
- ETL の id_token（J-Quants 用）を直接渡すこともできます（テストやキャッシュ制御用）。

2) ニュースセンチメント（銘柄別）の計算

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY が使われる
print(f"written scores: {written}")
```

- score_news は内部で OpenAI を呼び、ai_scores テーブルへ書き込みます。
- テスト時は kabusys.ai.news_nlp._call_openai_api をモック可能。

3) 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- ETF（1321）の MA200 乖離とマクロニュース（LLM）を合成して market_regime に保存します。
- OpenAI の呼び出しも同様に api_key 引数または環境変数 OPENAI_API_KEY を使用します。
- テスト用に _call_openai_api をパッチできます。

4) 監査ログスキーマの初期化 / 専用 DB の作成

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

---

## 設計上の注意・セキュリティ

- news_collector は SSRF や XML Bomb に対して複数の防御（スキーム検証、プライベートホスト拒否、受信バイト上限、defusedxml）を実装しています。
- J-Quants クライアントはレート制限（120 req/min）を守るためのスロットリング、再試行、401 トークン自動更新を行います。
- AI 呼び出しではレスポンスのバリデーション / リトライ・バックオフ / フェイルセーフ（失敗時は 0.0 などにフォールバック）を行っています。
- ルックアヘッドバイアス防止のため、日付ロジックは常に明示的な target_date を受け取り、DB クエリには「< target_date」「<= target_date」等の排他条件を適切に使用しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / token）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマの作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## テスト・開発メモ

- OpenAI 呼び出し部分（_call_openai_api）はテストで容易にモック可能（unittest.mock.patch を利用）。
- news_collector ではネットワーク入出力箇所（_urlopen）をモックしてテスト可能。
- DuckDB を用いるため、テストでは ":memory:" を使うことでインメモリ DB を利用できます（例: init_audit_db(":memory:")）。

---

ご不明点や README に追記したい使用例・運用手順があれば教えてください。必要に応じてサンプル .env.example や docker-compose / systemd 用ランブックも作成できます。