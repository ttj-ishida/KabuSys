# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）評価、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などの機能を含むモジュール群です。

主な設計方針のポイント:
- Look‑ahead bias を避けるため、内部で日付を自動参照しない実装（呼び出し側が target_date を与える）。
- DuckDB を用いたローカルデータベース（冪等保存、ON CONFLICT 処理）。
- J-Quants / OpenAI 等外部 API 呼び出しはリトライ・バックオフ・レート制御などの堅牢化を実施。
- ニュース収集では SSRF 対策や XML パースの安全処理（defusedxml）を実装。
- 監査ログ（signal / order_request / executions）を用いた完全なトレーサビリティ。

---

## 機能一覧

- 環境設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む機能（無効化可）
  - 必須・任意設定のプロパティを提供（kabusys.config.settings）
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（fetch_daily_quotes / save_daily_quotes）
  - 財務データ取得・保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得・保存（fetch_market_calendar / save_market_calendar）
  - run_daily_etl 等の高レベル ETL パイプライン
- データ品質チェック
  - 欠損値、重複、スパイク、日付不整合チェック（quality モジュール）
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF対策・正規化・前処理）
  - ニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化（init_audit_schema / init_audit_db）
- J-Quants クライアント実装
  - レート制御、リトライ、401 トークン自動更新、ページネーション対応

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型などを使用）
- ネットワークアクセスが必要（J-Quants API / OpenAI / RSS ソース）

1. リポジトリをクローンして作業ディレクトリへ移動する
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール（最小）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存があれば追加）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   プロジェクトルートに `.env`（と必要なら `.env.local`）を作成してください。設定可能な主な環境変数（kabusys.config.Settings で定義）:

   必須（使用する機能に応じて）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token で使用）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）

   任意（デフォルト値あり）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - KABU_API_BASE_URL: kabuAPIのベースURL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視関連）
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）

   自動読み込みを無効化したい場合は環境変数:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース・監査ログ初期化（例）
   - Python REPL またはスクリプト内で:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
   ```

---

## 使い方（主要な例）

以下はライブラリの代表的な使用例です。実運用やバッチ実行ではログ設定やエラーハンドリングを適切に追加してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定（None: 今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み件数:", n_written)
```

- マクロ + ETF MA200 を用いた市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- J-Quants の生 API 呼び出し（例: 日足取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

- RSS 取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出し時は API レート・料金が発生します。テスト時はモック可能（各モジュールの _call_openai_api を patch）。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになる箇所があるため、内部でチェック済みです（pipeline/news_nlp 等）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ・モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント（OpenAI）と score_news
    - regime_detector.py    # ETF(1321) MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py  # 市場カレンダー管理（is_trading_day 等）
    - etl.py                  # ETL 公開インターフェース（ETLResult を再エクスポート）
    - pipeline.py             # ETL パイプラインの実装（run_daily_etl 等）
    - stats.py                # zscore_normalize などの統計ユーティリティ
    - quality.py              # データ品質チェック
    - audit.py                # 監査ログDDL/初期化（signal/order_request/executions）
    - jquants_client.py       # J-Quants API クライアント（fetch/save 系）
    - news_collector.py       # RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum/value/volatility）
    - feature_exploration.py  # forward returns / IC / factor summary / rank

各モジュールの公開関数はファイルヘッダの docstring に処理フロー・設計方針が記載されています。実装内の docstring を参照すると詳細が分かります。

---

## 実装上の重要な注意・設計メモ

- Look‑ahead bias 回避:
  - LLM や ETL / 計算関数は date を引数で受け、内部で現在日付を参照しないように設計されています（バックテスト用途に配慮）。
- 冪等性:
  - DB への保存は ON CONFLICT を用いた冪等保存を基本としています（jquants_client.save_*）。
- フォールトトレランス:
  - OpenAI / J-Quants の API 呼び出しはリトライ・バックオフを備え、致命的エラー時も処理を継続する設計箇所が多くあります（news_nlp/regime_detector/pipeline）。
- セキュリティ:
  - news_collector は SSRF 対策、トラッキングパラメータ除去、XML パース安全化（defusedxml）を実装。
- テスト容易性:
  - 一部内部関数（OpenAI 呼び出し等）はモックしやすいよう分離されています（ユニットテストで差し替え可能）。

---

## よくある質問（FAQ）

Q: データベースのデフォルトパスは？
A: DuckDB: data/kabusys.duckdb（DUCKDB_PATH）、監視用 SQLite: data/monitoring.db（SQLITE_PATH）

Q: .env ファイルの自動読み込みを無効にしたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

Q: OpenAI を使いたくない（テスト）
A: score_news / score_regime 呼び出し時に api_key を明示的に与えない場合は環境変数 OPENAI_API_KEY を参照します。ユニットテストでは kabusys.ai.* の内部 _call_openai_api を patch してスタブレスポンスを返すことが推奨されています。

---

この README はコードベースの主要な使い方・構成をまとめたものです。各モジュールの詳細な挙動・パラメータは該当ファイルの docstring と関数シグネチャを参照してください。必要であればサンプルスクリプトや CI / デプロイ手順の章を追加します。