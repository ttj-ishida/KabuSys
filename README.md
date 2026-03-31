# KabuSys

日本株向けのデータプラットフォーム＋リサーチ／自動売買基盤の一部を提供するライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログ（オーダー監査）などを含み、DuckDB を中心としたデータワークフローと OpenAI を使ったニュースセンチメント評価を備えています。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（fetch / save）
  - run_daily_etl による日次一括 ETL（calendar → prices → financials → 品質チェック）
  - 差分取得・バックフィル・健全性チェック実装

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）

- ニュース収集 / NLP
  - RSS フィード取得時の SSRF 対策、トラッキング除去、前処理、raw_news への冪等保存を想定
  - OpenAI（gpt-4o-mini）を用いた銘柄単位ニュースセンチメント（score_news）
  - マクロニュース＋ETF MA200乖離を組み合わせた市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ、Zスコア正規化

- 監査（Audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ（UUIDベースの階層）

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数やパスのラッパー（kabusys.config.settings）

---

## 要件（ざっくり）

- Python 3.10 以上（ソースでの型ヒントや union 型表記を利用）
- 必要ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
（プロジェクトには requirements.txt がない想定のため、必要に応じてインストールしてください）

例：
```
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（主要なもの）

必須（実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（jquants_client で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用するボットトークン（Slack を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等を行う場合）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールの score_news / score_regime で使用）

オプション / デフォルト:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、ルート直下の `.env` と `.env.local` を自動で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- テストなどで自動読込を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python インタプリタを用意（3.10+ 推奨）
2. 依存パッケージをインストール
   - 例（pip）:
     ```
     python -m pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt / poetry 等を用意しているはずなので、それに従ってください。

3. 環境変数を設定
   - プロジェクトルートに `.env` を用意するか、OS 環境変数として設定します。
   - 例 `.env`（最低限の例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     ```

4. DuckDB の初期化（監査 DB を使用する場合）
   - Python から監査テーブルを初期化できます。例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続に対して init_audit_schema(conn) を呼び出してスキーマを追加できます。

---

## 使い方（代表的な呼び出し例）

- 日次 ETL を実行する（DuckDB 接続を渡す）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（銘柄単位）を作成する（OpenAI API キー必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対する前日15:00JST〜当日08:30JST を対象に集計して ai_scores に書き込み
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- マクロ + MA200 で市場レジームを判定して書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
results = calc_momentum(conn, target_date=date(2026, 3, 20))
# results: list of dicts with keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

- 監査スキーマの初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- RSS を取得する（ニュース収集の低レイヤ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# returns list of NewsArticle dicts
```

注意:
- AI モジュール（score_news, score_regime）は OpenAI API を使用します。OPENAI_API_KEY が環境にセットされているか、各呼び出しに api_key を渡してください。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, など）は ETL や別モジュールで要求されます。実際に運用するにはスキーマ定義（data/schema 等）が別途必要です（このリポジトリ内のDDL 一部は audit に含まれています）。

---

## ディレクトリ構成（コードベースの抜粋）

以下は主要モジュールのファイル構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py                   — ETL のメインロジック（run_daily_etl 等）
    - etl.py                        — ETLResult の公開インターフェース
    - calendar_management.py        — 市場カレンダー管理
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — 品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore）
    - audit.py                      — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — forward returns, IC, rank, summary
  - research/... (その他ユーティリティ)

---

## 実運用上の注意点（設計上の重要ポイント）

- Look-ahead bias 回避
  - 多くの関数は datetime.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性に配慮してください。

- フェイルセーフ
  - OpenAI や外部 API 呼び出しは失敗時にフォールバック（例: macro_sentiment = 0.0）するよう設計されています。運用時はログ監視と適切なアラートを設けてください。

- 冪等性
  - J-Quants 保存や監査ログ作成は基本的に冪等（ON CONFLICT / PRIMARY KEY）を意識していますが、ETL 呼び出し方やトランザクション選択に注意してください。

- セキュリティ
  - news_collector は SSRF 対策や XML の安全パーサ（defusedxml）を使用しています。外部 API の認証情報やキーは安全に管理してください。

---

## サポート / 貢献

この README はコード内ドキュメントに基づく概要です。実際にプロジェクトを動かす際は次を確認してください:
- 追加のスキーマ定義ファイル（テーブル作成 SQL）がプロジェクトに存在するか
- CI / テスト、requirements / pyproject の内容
- 運用レベルでの設定（ログ集約、監視、シークレット管理）

不明点があれば、コード内の docstring（各モジュール冒頭）を参照するか、具体的なユースケースを添えて質問してください。