# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定のトレース）などを提供します。

---

## 概要

KabuSys は日本株の定量分析・自動売買プラットフォーム構築のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存する ETL
- raw_news の収集・前処理・LLM によるニュースセンチメント算出（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを組合せ）
- 研究向けファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）を管理する監査スキーマ初期化ユーティリティ

設計上の特徴：
- Look-ahead バイアス軽減（内部で date.today() をバックテスト用に直接参照しない等の配慮）
- 冪等操作（DuckDB への保存は ON CONFLICT を利用）
- API 呼び出しに対するリトライ・レート制御・フェイルセーフ（LLM/API失敗時のデフォルト挙動）

---

## 機能一覧

- 環境設定管理（自動 .env ロード・必須項目チェック）
- J-Quants API クライアント（認証、ページネーション、保存関数）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース収集（RSS → raw_news、SSRF や gzip 保護、URL 正規化）
- ニュース NLP（gpt-4o-mini を用いた銘柄別/マクロのセンチメント評価）
- 市場レジーム判定（MA200 とマクロセンチメントの重み合成）
- 研究ユーティリティ（ファクター計算、forward returns、IC、zscore 正規化等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査テーブル初期化（signal_events, order_requests, executions 等）
- ユーティリティ（統計、カレンダー管理、duckdb 用保存ユーティリティ）

---

## セットアップ手順（開発環境想定）

1. リポジトリをクローンして仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（プロジェクトに requirements.txt がない場合は主要依存を例示）
   ```bash
   pip install duckdb openai defusedxml
   # 必要に応じてその他パッケージを追加してください
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（.git/pyproject.toml を基点にプロジェクトルート判断）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用（必須）
   - OPENAI_API_KEY : OpenAI API キー（ニュース NLP / レジーム判定で利用）
   - KABUSYS_ENV : development / paper_trading / live（既定: development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（既定: data/monitoring.db）

   .env の例（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース準備
   - DuckDB ファイルはデフォルトで `data/kabusys.duckdb` を使用します。ディレクトリを作成しておいてください。
   ```bash
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は Python からの簡単な利用例です。

- ETL を実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄別 ai_score を ai_scores テーブルに保存）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査ログスキーマの初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続に対して init_audit_schema(conn)
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(records[:5])
```

---

## 注意点 / 運用メモ

- OpenAI 呼び出しに失敗した場合、フェイルセーフでスコアを 0.0 にフォールバックする設計の箇所があります（news_nlp / regime_detector）。
- J-Quants API に対してはレート制御とリトライを実装していますが、運用時は API 利用制限に注意してください。
- DuckDB を用いるため、多数の行挿入は executemany を使ったバルク処理で実行されています。DuckDB のバージョンにより空の executemany に対する挙動が異なるため、内部でガードされています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基に行われます。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

## ディレクトリ構成

リポジトリ内の主なモジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP / ai_scores 書込
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存関数
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETLResult 再エクスポート
    - news_collector.py     # RSS 取得・前処理
    - calendar_management.py# 市場カレンダー管理
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（zscore 等）
    - audit.py              # 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム/ボラ/バリュー等
    - feature_exploration.py# forward_returns, IC, factor_summary, rank
  - ai, data, research 以下に更に細分化された機能群あり

---

## さらに読む / 拡張

- 各モジュールの docstring に設計意図・注意点が記載されています。実運用やテストの際は該当箇所を参照してください。
- LLM（OpenAI）を利用する機能は API キーやコストが発生します。プロンプトやモデル選定は運用に応じて調整してください。

---

もし README に追記してほしい実例（CI での ETL 実行方法や schema の SQL 定義抜粋、テストの実行方法など）があれば教えてください。README をそれに合わせて拡張します。