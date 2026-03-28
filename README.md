# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ（発注→約定のトレース）などを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない等）
- DuckDB をデータ格納に使用／SQL と Python の混成実装
- ETL や保存処理は冪等（idempotent）に設計
- API 呼び出しはレートリミット・リトライ・フェイルセーフを備える

## 機能一覧
- データ取得・ETL
  - J-Quants からの株価（daily quotes）、財務データ、上場銘柄情報、JPX カレンダー取得（jquants_client）
  - 差分取得／バックフィル、ETL 実行エントリ（data.pipeline.run_daily_etl）
- データ品質
  - 欠損・重複・スパイク・日付不整合のチェック（data.quality）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日取得、カレンダー更新ジョブ（data.calendar_management）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news への保存想定（data.news_collector）
- AI（OpenAI）スコアリング
  - 銘柄別ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - バックオフ／リトライ・JSON Mode を使った堅牢な実装
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義・初期化（冪等）
  - 監査用 DB 初期化ユーティリティ（init_audit_db, init_audit_schema）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー算出（factor_research）
  - 将来リターン計算、IC、統計サマリ（feature_exploration）
- 汎用ユーティリティ
  - Zスコア正規化などの統計関数（data.stats）

---

## 必要条件
- Python 3.10 以上（PEP 604 タイプ表記を使用）
- 主な依存パッケージ（要インストール）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS 取得など）

推奨インストール例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（任意）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに配置することで自動読み込みされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知等に使用する Bot トークン（本実装では参照用）
- SLACK_CHANNEL_ID — Slack チャネル ID（参照用）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（参照用）
- OPENAI_API_KEY — OpenAI を使う機能を利用する場合に必要（score_news / score_regime に使用）

その他（任意／デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/…
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用、デフォルト data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

※ ここでは簡単なコード例を示します。実際の運用ではエラーハンドリングやログ設定、環境ごとの設定を適切に行ってください。

- 共通: settings の利用
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None で env の OPENAI_API_KEY を使う
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # parent dir がなければ自動作成
```

- ニュース RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用途（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list of dicts with keys like 'code', 'mom_1m', 'ma200_dev', ...
```

---

## ディレクトリ構成（主要ファイル）
（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py             — 銘柄別ニュースセンチメント（OpenAI）
    - regime_detector.py      — マーケットレジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 / 保存 / retry / rate limit）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - quality.py              — データ品質チェック
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - news_collector.py       — RSS 収集・前処理
    - stats.py                — zscore_normalize 等
    - audit.py                — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 計算
    - feature_exploration.py  — 将来リターン / IC / summary / rank
  - other モジュール（strategy / execution / monitoring 等は __all__ に列挙されています）

---

## 実装上の注意点（設計ポリシー）
- ルックアヘッドバイアス防止
  - AI・研究モジュールは内部で date.today()/datetime.today() を直接参照しない設計（target_date を明示的に渡す）。
- 冪等性
  - ETL 保存関数は ON CONFLICT DO UPDATE を使い、再実行可能に設計。
- レート制御・リトライ
  - J-Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフを実装。
  - OpenAI 呼び出しは 429/ネットワーク/5xx を再試行し、最終的にフェイルセーフ（macro_sentiment=0 等）で継続する箇所あり。
- トランザクション制御
  - 重要な書き込みは BEGIN/COMMIT または BEGIN/DELETE/INSERT/COMMIT のように冪等を保った上で行う。例外時は ROLLBACK を試行。
- セキュリティ
  - news_collector は SSRF 対策、応答サイズ制限、XML パーサーは defusedxml を使用などを実装。

---

## テスト・開発時のヒント
- 自動 .env ロードは config.py で行われます。テストで無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI 呼び出しは内部の _call_openai_api をモックすることでテストしやすくなっています（news_nlp._call_openai_api / regime_detector._call_openai_api を patch）。

---

以上がこのコードベースの概要および基本的な使い方です。  
運用前に必ず .env.example を作成し、DuckDB のスキーマ（テーブル定義）や初期化手順（監査テーブルなど）を環境に合わせて実行してください。必要なら README に追記してほしい項目（API シークレット管理、CI ワークフロー、追加ユーティリティ等）を教えてください。