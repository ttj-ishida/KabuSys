# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（発注/約定トレーサビリティ）など、複数のコンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究／実行周りのユーティリティをまとめたライブラリです。主な目的は以下の通りです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL。
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・市場レジーム判定（AI スコアリング）。
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用統計ユーティリティ。
- 監査ログスキーマ（signal / order_request / execution）を提供し、発注フローのトレーサビリティを確保。

設計上の特徴：
- Look-ahead bias を避ける実装（内部で datetime.today()/date.today() を直接参照しないなど）。
- DuckDB を基盤に idempotent（ON CONFLICT DO UPDATE）な保存。
- API 呼び出しに対するリトライ・レートリミット・フェイルセーフの実装。
- セキュリティ配慮（RSS の SSRF 対策、XML の defusedxml 使用など）。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数）: fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
  - ニュース収集（fetch_rss、URL 正規化、記事ID生成）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - 品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- ai
  - ニュース NLP（score_news: 銘柄ごとに ai_scores を生成）
  - 市場レジーム判定（score_regime: ma200 + macro sentiment を合成して market_regime を書き込み）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存ライブラリのインストール（例）
   - pip install duckdb openai defusedxml
   - 必要に応じて他のライブラリを追加（urllib 等は標準ライブラリ）。

   （このリポジトリに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. パッケージを開発モードでインストール（オプション）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込みます（無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須、ETL 用）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（発注周り）
   - オプション:
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime を呼ぶ際に指定しない場合に使用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知用（オプション）
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : 監視 DB のパス（data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連設定
     - KABUSYS_ENV : development / paper_trading / live （デフォルト development）
     - LOG_LEVEL

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な例）

以下はライブラリを利用する典型的なコード例です。すべて Python スクリプト内から呼び出します。

- DuckDB 接続の作成（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ai.score_news（ニュースセンチメントの生成）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- ai.score_regime（市場レジーム判定）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（research）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブルとインデックスを作成します
```

- RSS フィード取得例
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点・テストフック:
- OpenAI への呼び出しは内部でリトライ・フォールバックを行います。ユニットテスト時はモジュール内の _call_openai_api を patch してレスポンスを模擬できます（例: unittest.mock.patch）。
- 関数の多くは api_key や id_token を引数で注入可能で、テストや CI 環境での再現性を高めています。

---

## よく使う API（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path)

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント生成（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - execution/ (発注関連モジュール等 想定)
  - monitoring/ (プロセス監視/メトリクス 想定)
  - ai/、research/ 以下にそれぞれの実装モジュール

---

## 運用上の注意

- 必須環境変数（JQUANTS_REFRESH_TOKEN など）は適切に管理してください。`.env` ファイルを使う場合は機密情報が含まれるためリポジトリにコミットしないでください。
- OpenAI API はコストとレート制限があります。バッチサイズやリトライ設定はモジュール内の定数で調整できます（news_nlp の _BATCH_SIZE 等）。
- ETL は既存データを上書きする（ON CONFLICT）ため、バックテスト用途での look-ahead 回避には保存タイミングに注意してください。関数は Look-ahead を防ぐよう設計されていますが、呼出し側が過去データをどの時点で利用可能にするかは運用方針に依存します。
- ニュース収集での外部 URL に対しては SSRF 対策が施されていますが、運用環境のネットワークポリシーと合わせて検討してください。

---

## 貢献・開発

- テスト: 各モジュールは外部 API（OpenAI / J-Quants / ネットワーク）に依存するため、外部呼び出しをモックしてユニットテストを作成してください。多くの内部関数は patch しやすい設計になっています（例: _call_openai_api の差し替え、_urlopen の差し替えなど）。
- コードスタイル: ロガーを多用しており情報・警告・エラーを出しています。ログレベルは環境変数 LOG_LEVEL で調整できます。

---

必要であれば、README に以下を追加で含めます：
- 具体的な .env.example の完全なテンプレート
- CI / デプロイ手順（systemd サービス例、監視フラグ扱い等）
- さらに詳細な API リファレンス（各関数の引数詳細と戻り値）