# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース NLP（OpenAI を用いたセンチメント）・市場レジーム判定・リサーチ用ファクター計算・監査ログ（注文/約定のトレーサビリティ）などを含みます。

注意: 本リポジトリはトレード戦略実行のための基盤ライブラリです。実際の売買を行う場合は十分なテストと安全対策（接続先の設定、認証情報管理、発注冪等性確認、リスク管理）を行ってください。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、JPX カレンダー取得（ページネーション、リトライ、レートリミッティング対応）
  - 差分更新・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）
  - raw_prices / raw_financials / market_calendar 等への冪等保存

- ニュース収集 & NLP
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores への保存）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）

- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクターの統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - 監査DB 初期化ユーティリティ（UTC タイムゾーン固定）

- 設定・運用
  - 環境変数 / .env ファイルからの設定読み込み（自動読み込み機能、無効化可能）
  - 環境別フラグ（development / paper_trading / live）やログレベル管理
  - 監視設定（PID ファイル、CPU/MEM/DISK 閾値など）

---

## システム要件（主な依存）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ：urllib, json, logging, datetime など多数）

依存管理は各自の環境で requirements.txt を作成するか、下記のように個別にインストールしてください。

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

.env / .env.local ファイルがプロジェクトルートにある場合、自動で読み込まれます（環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発向けの簡易手順）

1. リポジトリをクローンして、パッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```
   （`setup.py` / `pyproject.toml` がある前提。無い場合は必要な依存を手動で pip インストールしてください）

2. 必要な環境変数を設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成し、上記の必須変数を設定してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     ```

3. DuckDB 監査データベース（監査ログ）を初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection（以後の処理で利用）
   ```

4. データベース接続（ETL / 解析）
   - DuckDB を直接開いて ETL や解析を実行します。
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

---

## 使い方（主要な機能の呼び出し例）

- 日次 ETL（J-Quants から株価・財務・カレンダーを取得し品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を使って銘柄別スコアを ai_scores に書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（MA200 乖離 + マクロニュース）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマ初期化（別 DB を使用する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  forward = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
  ```

- RSS ニュース取得（ニュース収集）※fetch_rss はリモートサーバに HTTP リクエストを行います
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

---

## 運用上の注意点

- OpenAI 呼び出しはコストとレート制限が発生します。テスト実行時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください。
- J-Quants API の利用にはレート制限（120 req/min）や認証トークン管理があります。get_id_token は自動リフレッシュを行いますが、実運用ではトークン管理に注意してください。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、ETL 実装では空チェックを行っています。DB バージョン互換性に注意してください。
- ニュースの RSS 取得では SSRF / private host 対策、最大レスポンスサイズ制限を実装していますが、運用時の外部コンテンツでは追加の検証が必要になる場合があります。
- KABUSYS_ENV を "live" に設定すると本番運用向けのフラグが有効になります。誤設定に注意してください。

---

## ディレクトリ構成

プロジェクト主要ファイル（src 以下）構成の概略:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - calendar_management.py         — JPX カレンダー管理・営業日判定
    - etl.py / pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - stats.py                       — 汎用統計ユーティリティ（zscore 正規化）
    - quality.py                     — データ品質チェック（欠損・スパイク等）
    - audit.py                       — 監査ログスキーマ / 初期化
    - jquants_client.py              — J-Quants API クライアント (fetch/save)
    - news_collector.py              — RSS 収集・前処理
    - etl.py                         — ETL の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value の計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー 等
  - (その他)                         — strategy / execution / monitoring 等のパッケージが想定される

簡易ツリー（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ calendar_management.py
│  ├─ audit.py
│  └─ stats.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## テスト・開発時の補助

- OpenAI / J-Quants など外部 API はユニットテストでモック化することを推奨します（コード内にも patch で差し替えられる設計の箇所があります）。
- データベース初期化やテストデータ投入は DuckDB の in-memory モード（":memory:"）を利用すると簡単に行えます。

---

## ライセンス / 責任

このリポジトリはトレード支援フレームワークを提供しますが、実際の資金運用による損失に対しては作者は責任を負いません。実運用前に必ず法令遵守・リスク管理・十分な検証を行ってください。

---

README で説明しきれない内部ロジックや実装の詳細は、各モジュールの docstring を参照してください（kabusys/data/*.py, kabusys/ai/*.py, kabusys/research/*.py）。必要であればサンプルのワークフローや設定テンプレート（.env.example）を別途用意できます。ご希望があれば作成します。