# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォームおよび自動売買基盤の主要コンポーネントを集めたライブラリです。ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを含み、DuckDB を中核 DB として利用します。

---

## 主な概要

- データ取得（J-Quants API） → DuckDB 保存（原本テーブル: raw_prices, raw_financials, raw_news, market_calendar 等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と LLM によるニュースセンチメント / 銘柄ごとの AI スコア生成
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースによる LLM センチメント）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal / order_request / executions）スキーマと初期化ユーティリティ

パッケージ名: `kabusys`（バージョン 0.1.0 が設定済み）

---

## 機能一覧

- data
  - jquants_client: J-Quants API との通信（認証、ページング、レート制御、保存用ユーティリティ）
  - pipeline / etl: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損、重複、スパイク、日付整合性）
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - news_collector: RSS 取得・前処理・raw_news 保存ユーティリティ（SSRF/サイズ対策、URL 正規化）
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 共通統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI に投げて ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 比とマクロニュース LLM を合成して market_regime に書き込む
- research
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（統計解析補助）
- config
  - 環境変数読み込み (.env 自動読み込み機能) と Settings オブジェクト
- その他ユーティリティ群（ETL 結果クラス、型定義等）

---

## 必要条件 / 依存パッケージ（例）

最低限必要な Python ライブラリ（プロジェクトに合わせて適宜追加してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（ネットワークアクセス・J-Quants/OpenAI のクレデンシャルが必要）

pip の例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージ配布用 setup があれば: pip install -e .
```

---

## 環境変数 / .env

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード（config 参照）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=/path/to/data/kabusys.duckdb
KABUSYS_ENV=development
```

注意: Settings クラスのプロパティは必須項目未設定時に例外を投げます（_require を使用）。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB ファイルやデータディレクトリの作成（必要に応じて）
   - デフォルトは data/ 以下に作成されます

---

## 使い方（コード例）

以下は代表的なユースケースの Python スニペット例です。プロジェクトルートで実行するか、適切に PYTHONPATH を設定して下さい。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジーム判定を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

- RSS を取得して記事を確認（news_collector の低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- AI 系（score_news / score_regime）は OpenAI API を使用します。`OPENAI_API_KEY` を環境変数か関数引数で渡してください。
- J-Quants API を使用する ETL 系は `JQUANTS_REFRESH_TOKEN` が必要です（get_id_token を経由して id_token を取得）。
- DuckDB のテーブルスキーマはこの README に含まれていないため、初期スキーマは別途セットアップするか、DDL 初期化用ユーティリティ（もしあれば）を使用してください（audit モジュールには init_audit_schema が含まれます）。

---

## ディレクトリ構成（主要ファイル / モジュール）

src/kabusys/
- __init__.py — パッケージ初期化（__version__）
- config.py — 環境変数 / .env 自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント / ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（MA200 + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集／前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ用 DDL / 初期化（init_audit_schema, init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- その他サブモジュール（strategy, execution, monitoring）については __all__ に列挙済みだが、今回のソース配下では重複や未実装の箇所がある可能性があります。

---

## 運用・開発時の注意点

- Look-ahead バイアス防止: 多くの関数で内部で現在時刻(date.today()) を参照せず、引数で target_date を受け取る設計になっています。バックテストや再現性のため必ず target_date を明示的に与えるか挙動を理解してください。
- 自動 .env ロードはプロジェクトルートの判定に __file__ を用いた探索を行います。テストなどで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API はレート制限（120 req/min）を守る実装が組み込まれていますが、外部で並列化する場合は追加で配慮してください。
- OpenAI 呼び出しはレスポンスのバリデーションとリトライ（指数バックオフ）を内包していますが、クォータやコスト面の制御はユーザ側で考慮してください。

---

## さらに詳しく / 貢献

- 各モジュールの docstring に設計方針や処理フローが詳細に記載されています。実装確認や拡張の際は該当モジュールの docstring をまず参照してください。
- バグ報告 / 機能改善はリポジトリの Issue に記載してください（本 README はサンプルベースの説明のため、実運用向けの詳細ガイドや CLI は別途追加を推奨します）。

---

必要であれば、README に動作確認用のサンプルスクリプト、Docker / systemd での運用例、CI / テストの手順などを追記します。どの情報が欲しいか教えてください。