# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（モジュール群）。  
ETL（J-Quants からのデータ取得／保存）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と前処理（raw_news テーブル）
- ニュースを OpenAI で NLP（センチメント）して ai_scores へ保存
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の特徴：
- DuckDB を中心としたローカル分析 DB を想定
- Look-ahead バイアス回避（target_date を明示し、内部で datetime.today() を無秩序に使わない）
- 冪等性（DB 保存は ON CONFLICT で上書き）
- 外部 API 呼び出しはリトライ・バックオフやレートリミット制御あり
- テスト容易性を意識した設計（キー注入や内部呼び出しの差し替えが可能）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数の読み込み・管理（.env / .env.local を自動ロード）
  - 必須設定取得ヘルパー（settings オブジェクト）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline: ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理（SSRF 対策、トラッキング除去）
  - calendar_management: 市場カレンダー判定・更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM (gpt-4o-mini) でセンチメント化して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロ記事の LLM センチメントを合成して market_regime に書き込む

- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用した正規化

---

## 必要条件

- Python 3.10+（タイプヒントに union | を使用）
- 依存パッケージ例（実行する機能に応じて）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）

インストール前に仮想環境を作成することを推奨します。

---

## インストール（開発用）

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"     # setup.py/pyproject がある場合。無ければ必要パッケージを個別 pip install
# あるいは最低限:
pip install duckdb openai defusedxml
```

※ pyproject.toml / setup.py に依存関係が定義されている想定です。なければ上記の必須パッケージを個別に入れてください。

---

## 環境変数（主なもの）

以下は settings クラスで参照される主要な環境変数です。必須のものは README や .env.example を参考に .env に設定してください。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants の refresh token（ETL で ID トークン取得に使用）

- KABU_API_PASSWORD (必須)
  - kabuステーション API 連携用パスワード（発注等で使用）

- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
  - kabu API のベース URL（デバッグ用にローカルを指定する場合など）

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
  - 監視・通知用の Slack 設定（本パッケージの一部監視機能で使用）

- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス（監査 DB などで使用）

- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
  - 監視用 SQLite のパス

- KABUSYS_ENV (任意、デフォルト: development)
  - 有効値: development / paper_trading / live

- LOG_LEVEL (任意、デフォルト: INFO)
  - DEBUG/INFO/WARNING/ERROR/CRITICAL

- OPENAI_API_KEY
  - OpenAI 呼び出しに使用（news_nlp / regime_detector）。関数呼び出し時に api_key を直接渡すことも可能。

自動 .env 読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env、.env.local を自動ロードします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 既存 OS 環境変数は保護され、.env/*.local による上書きは行われません（ただし .env.local は override=True としてロードされますが OS 環境は protected されます）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境作成・有効化
3. 依存パッケージをインストール
4. プロジェクトルートに `.env` または `.env.local` を作成し必要な環境変数を設定（.env.example を参考）
5. DuckDB や監査 DB の初期化（例を参照）

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

下記は Python REPL / スクリプト内から呼び出す例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を確立して ETL を実行（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースを OpenAI でスコアリングして ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究: モメンタムや将来リターンの計算（バックテスト前の特徴量生成など）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
```

- 監査ログスキーマ初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成される
```

- RSS フェッチ（ニュースコレクタ）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 注意点 / 運用上のヒント

- OpenAI の呼び出しはコストが発生します。news_nlp / regime_detector は gpt-4o-mini を想定しており、API キーは漏洩しないように管理してください。
- J-Quants API のレート制限・401 リフレッシュ挙動に対応していますが、大量のページネーションを行う場合はモジュールの RateLimiter の挙動に注意してください。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、実装側でチェック済みです（空の書き込みは行いません）。
- Look-ahead バイアスに注意して、バックテストでは過去のみのデータを DB に入れてから分析を行ってください。
- 自動 .env ロードは便利ですが、CI などでは KABUSYS_DISABLE_AUTO_ENV_LOAD を指定して明示的に設定する方が確実です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュール）

- src/kabusys/__init__.py
  - パッケージ初期化、公開モジュール一覧

- src/kabusys/config.py
  - 環境変数管理、settings オブジェクト

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — ETF とマクロニュースを合成する市場レジーム判定（score_regime）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + DuckDB への保存関数（fetch_* / save_*）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集 / 前処理 / 保存補助
  - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等統計ユーティリティ
  - audit.py — 監査ログスキーマ定義・初期化（init_audit_schema / init_audit_db）

- src/kabusys/research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー

---

## 既知の制約・設計ノート

- LLM 呼び出し（OpenAI）は network リトライや 5xx の扱いを備えていますが、レスポンスのフォーマットが期待どおりでない場合はスコアを 0 にフォールバックする等のフェイルセーフが入っています。
- DuckDB のバージョン差異に対して互換性を考慮した実装になっています（例: executemany の空リスト対策、日付型の取り扱い）。
- news_collector は SSRF 対策（リダイレクト検査、プライベート IP 検出など）を実装しています。

---

## サポート / 貢献

バグ報告や機能要望は Issue にお願いします。プルリク歓迎です。ドキュメント改善・ユニットテスト追加も助かります。

---

README は以上です。各モジュールの詳細はソースコードの docstring に設計方針・使用例が含まれているため、必要に応じて参照してください。