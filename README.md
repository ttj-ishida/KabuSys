# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、ニュース収集・NLP、マーケットカレンダー管理、ファクター計算、監査ログ（発注・約定追跡）など、自動売買システムの基盤機能を提供します。

主な設計方針
- ルックアヘッドバイアス防止（date/time を明示的に受け取る設計）
- DuckDB を用いたローカルデータレイヤ
- J-Quants / OpenAI 等の外部 API 呼び出しはリトライ・レート制御・フェイルセーフ実装
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧

- 環境設定管理
  - .env ファイル / OS 環境変数から設定を読み込み（自動ロード、優先順位: OS > .env.local > .env）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得 / ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / マーケットカレンダー）
  - 差分ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果集約用データクラス `ETLResult`

- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合などのチェック
  - 問題を `QualityIssue` として収集（error / warning）

- カレンダー管理
  - JPX カレンダーの保存・判定（営業日/半日/SQ）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- ニュース収集・NLP（OpenAI）
  - RSS フィード取得・前処理（SSRF対策、トラッキングパラメータ除去、サイズ制限 等）
  - ニュースを銘柄に紐付けて ai_scores に保存するバッチ処理（gpt-4o-mini を想定）
  - レート制限・エラーハンドリング（429/タイムアウト/5xx などのリトライ）

- 市場レジーム判定
  - ETF 1321 の 200日MA乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して
    daily に market_regime を計算・保存

- 研究系ユーティリティ
  - ファクター計算（momentum / value / volatility / liquidity）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ

- 監査ログ（発注・約定トレース）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 冪等キー（order_request_id / broker_execution_id）によるトレーサビリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈・ `X | Y` 構文を使用）
- ネットワーク接続（J-Quants / OpenAI 等の外部 API へアクセス）

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の最低要件）
   - pip install duckdb openai defusedxml

   追加で利用するライブラリがあれば適宜インストールしてください。

3. パッケージをインストール（開発モード）
   - pip install -e .

   （ソースを直接参照するだけの場合は不要ですが、パッケージとして使う場合に推奨）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI を使う処理（news_nlp / regime_detector）で必要

任意 / デフォルトあり
- KABUS_API_PASSWORD, KABU_API_BASE_URL（kabuステーション連携用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（代表例）

以下は Python REPL / スクリプトでの利用例です。各例では `duckdb` が接続済みで、必要なテーブルは ETL 等で作成されることを想定します。

- DuckDB に接続する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニュース NLP（ai_scores へ書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY() は環境変数または引数で指定
n_written = score_news(conn, target_date=date(2026,3,20))
print("written:", n_written)
```

- 市場レジーム判定を実行（market_regime テーブルに書き込む）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を初期化する（別ファイルでも可）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して発注ログ周りのテーブルが初期化される
```

- RSS を取得する（ニュース収集の低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```
（raw_news への永続化は ETL / 収集パイプライン側で行います）

---

## 使用上の注意 / 運用ノウハウ

- OpenAI / J-Quants / kabu API を使う処理は外部料金・レート制限の対象です。APIキーの管理とレート制御ポリシーに注意してください。
- AI モジュールはレスポンスパースに失敗した場合はフェイルセーフ（0.0 やスキップ）で継続する設計です。ログを確認して手動対応してください。
- ETL は部分失敗を許容して他のステップは継続する設計です。`ETLResult` の `errors` / `quality_issues` を確認して問題を把握してください。
- 自動 .env ロードの挙動:
  - 起点: 現在のパッケージファイル位置から上位へ .git または pyproject.toml を探索してプロジェクトルートを特定します。（CWD依存しない）
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の executemany はバージョン依存で空リストを許容しない場合があるため、空チェックを行う実装が含まれています。

---

## ディレクトリ構成

主要ファイル / モジュールを抜粋しています（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py    # 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント & DuckDB 保存
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult の再エクスポート
    - news_collector.py    # RSS 収集・前処理
    - calendar_management.py # マーケットカレンダー管理
    - quality.py           # 品質チェック群
    - stats.py             # 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py             # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py   # Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py # IC / forward returns / summary utilities

（上記は主要モジュールの要約です。詳細は各ソースファイルのドキュメント文字列を参照してください。）

---

## 追加情報 / 開発メモ

- ログレベルは環境変数 `LOG_LEVEL` で制御できます（デフォルト INFO）。
- 実運用では `KABUSYS_ENV=paper_trading` / `live` を適切に使い分けてください（settings.is_live / is_paper / is_dev を利用）。
- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境を固定化すると安定します。
- OpenAI 呼び出しは内部で `OpenAI(api_key=...)` を使っています。テストでは `_call_openai_api` をパッチしてスタブ化することが想定されています。

---

必要であれば、README にサンプル .env.example、より詳しい ETL 実行手順、CI 用の設定例、よくあるトラブルシューティング（API レートや JSON パースエラーの対処）などを追記します。どの情報が欲しいか教えてください。