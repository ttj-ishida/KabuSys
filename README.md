# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ (KabuSys)。  
データ取得（J-Quants）、ETL、データ品質チェック、監査ログ、ニュース NLP、マーケットレジーム判定、研究用ファクター計算などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のシステムトレードに必要なデータ基盤と解析機能を集めたパッケージです。主に以下を目的とします:

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集 / 前処理 / OpenAI を用いた銘柄別センチメント算出（ai_scores）
- 市場レジーム判定（ETF MA とマクロニュースを組み合わせた判定）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）
- リサーチ向けファクター計算・統計ユーティリティ

設計方針として「ルックアヘッドバイアスを避ける」「冪等性」「フェイルセーフ（API失敗は局所的に扱う）」を重視しています。

---

## 主な機能一覧

- data/
  - J-Quants クライアント（fetch / save 関数）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS fetch + 前処理、SSRF対策、トラッキングパラメータ除去）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄毎の ai_score を ai_scores テーブルへ保存）
  - レジーム判定（score_regime: ETF(1321) MA200乖離とマクロニュースセンチメントを合成）
- research/
  - ファクター計算（momentum, value, volatility 等）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- config
  - 環境変数の自動読み込み（.env / .env.local）と Settings オブジェクト

---

## 動作環境 / 前提

- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API のリフレッシュトークン
- OpenAI API キー（ニュース NLP / レジーム判定に使用）

requirements.txt が無い場合は上記を pip で導入してください:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境で編集する場合:
     ```
     pip install -e .
     ```
   - または通常インストール:
     ```
     pip install .
     ```

2. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（config モジュールがプロジェクトルートを探索して読み込みます）。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

3. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要なら）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_* 関数で利用）
   - その他（オプション）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB: data/monitoring.db）
     - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 等

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=xxxx
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DB 用ディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

※ すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受けます。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- 個別に株価 ETL を実行
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュース NLP スコア算出（ai_scores テーブルへ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
print(f"scored {count} codes")
```
- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# 以降、監査テーブルへアクセス可能
```

- JPX カレンダー更新ジョブを単独で実行
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

---

## 設定（Settings）項目一覧

config.Settings で参照される主な環境変数（代表）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須: kabu API を使う場合)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI を使う場合、関数に api_key を渡すことも可)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (paper_trading 時のモック挙動: instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|...)
- PID_FILE_PATH, KILL_FLAG_PATH, など（監視用）

詳細は kabusys/config.py を参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュール構成（本リポジトリの現状に基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP -> ai_scores
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + save_* 関数
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py           — 市場カレンダー管理
    - news_collector.py                — RSS 取得・前処理・SSRF 対策
    - audit.py                         — 監査ログスキーマ初期化
    - etl.py                           — ETL 結果クラス再エクスポート
  - research/
    - __init__.py
    - factor_research.py               — momentum / value / volatility 等
    - feature_exploration.py           — forward_returns, IC, factor_summary, rank

---

## 実装上の注意点 / 設計方針（ハイライト）

- ルックアヘッドバイアス防止:
  - 日付関連処理は内部で date.today() に依存しない設計（target_date を明示的に渡す）。
  - 取得・処理は「その日付以前のデータのみ」を参照するように実装されています。
- 冪等性:
  - DB への保存関数は ON CONFLICT DO UPDATE / DO NOTHING を利用し冪等保存を実現。
- フェイルセーフ:
  - OpenAI や外部 API の失敗時は局所でフォールバックし、全体処理を停止させない設計。
- セキュリティ:
  - ニュース収集は SSRF 対策、XML パース時の defusedxml 利用、URL 正規化によるトラッキング除去などを実装。
- ロギング:
  - 各モジュールは logger を利用して重要イベント・警告・エラーを出力します。

---

## 開発 / テスト

- 自動環境変数読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から探索して行われます。テストで無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI や外部 API 呼び出し部分は内部の _call_openai_api 等をモックすることでユニットテストが可能です（コード内にテスト差し替えの想定あり）。

---

## 参考

- 各モジュールの詳細な仕様・設計意図はソースコード内の docstring / コメントに記述されています。実装や運用上のポリシー変更がある場合はそちらを参照してください。

---

もし README に追加したい「実行コマンド例（CLI）」や「テーブルスキーマ一覧」「.env.example の自動生成」などがあれば、用途に合わせて追記できます。必要な情報を教えてください。