# KabuSys

日本株向け自動売買・データ基盤ライブラリ集です。ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI によるセンチメント評価）、ファクター計算、マーケットカレンダー管理、監査ログ（発注トレーサビリティ）など、量的投資システムで必要となる機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・レート制御・リトライ付き）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の結果を表す ETLResult 型

- ニュース収集 / NLP
  - RSS フィードからのニュース収集（SSRF 対策・トラッキングパラメータ除去・サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）生成
  - マクロニュースを用いた「市場レジーム判定」（bull / neutral / bear）

- 研究・ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB + SQL ベース）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Zスコア正規化

- カレンダー管理
  - market_calendar テーブルの管理・更新、営業日判定・次/前営業日取得、SQ 判定

- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）
  - 発注の冪等性・ステータス管理対応

- 汎用ユーティリティ
  - 環境変数ローディング（.env / .env.local 自動読み込み、無効化フラグ対応）
  - ログレベル・環境（development/paper_trading/live）設定
  - DuckDB を前提とした非依存（pandas 等に依存しない）実装

---

## 必要条件（概要）

- Python 3.9+（型注釈や標準ライブラリ機能を利用）
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- J-Quants / OpenAI / Slack / kabuステーション 等の外部 API キー（環境変数で設定）

※実際のプロダクション導入時は適切な仮想環境とパッケージバージョン固定を推奨します（requirements.txt / poetry 等を用意してください）。

---

## 環境変数（主なもの）

このプロジェクトは環境変数または .env / .env.local から設定を読み込みます。自動読み込みはプロジェクトルートに `.git` または `pyproject.toml` がある場合に有効になります。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（すべて大文字）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/…、デフォルト INFO)

設定は kabusys.config.settings を通じてアクセスできます。

---

## セットアップ手順（開発用）

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他、実行環境に応じて追加パッケージをインストールしてください
4. 環境変数を準備
   - プロジェクトルートに .env を作成するか、環境へ直接設定します
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=xxxx
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
5. DuckDB 用ディレクトリ作成（必要な場合）
   - mkdir -p data

---

## 使い方（主要なエントリポイント例）

以下はライブラリを直接インポートして使う際のサンプルコード例です。実行前に環境変数を設定してください。

- ETL（日次）を実行する例

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（銘柄別）を生成（OpenAI 必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- マクロニュース＋MA200 で市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（発注トレーサビリティ）用 DB を初期化

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# これで signal_events / order_requests / executions テーブルが作成される
```

- J-Quants の ID トークンを手動で取得

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

- RSS フィードを取得（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 開発者向けメモ / 実装上のポイント

- 環境自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動的に読み込みます。
  - テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - `.env.local` は `.env` の上書き（優先）読み込みされます。

- Look-ahead bias 対策
  - AI / 研究モジュールは date の扱いで現在日付を参照しないように設計されています（内部クエリは target_date より前または半開区間を採用）。
  - バックテストで使用する際は、データ取得時刻（fetched_at）や取得範囲に注意してください。

- 冪等性
  - J-Quants と DuckDB への保存は冪等（ON CONFLICT DO UPDATE 等）で実装されています。
  - 発注監査テーブルでは order_request_id を冪等キーとして想定しています。

- エラーハンドリング
  - 外部 API 呼び出しはリトライ（指数バックオフ）とフォールバック（失敗時はスキップして進める）を行う設計が多く採用されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）処理
    - regime_detector.py — マクロ＋MA200 による市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - etl.py — ETL インターフェース再エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 統計ユーティリティ（Zスコア等）
    - quality.py — データ品質チェック
    - audit.py — 監査テーブル定義と初期化
    - jquants_client.py — J-Quants API クライアント + 保存ロジック
    - news_collector.py — RSS 収集・前処理・SSRF 対策
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - (その他) strategy/, execution/, monitoring/ パッケージ参照用の __all__（初期構成）

---

## よくあるタスク / ヒント

- デバッグ時に環境読み込みを確実にテストしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて明示的に .env を読み込む／無効化する。
- OpenAI の呼び出しをユニットテストで置き換える場合、モジュール内の _call_openai_api をモックすることで外部呼び出しを回避できます（news_nlp/regime_detector に該当）。
- DuckDB に対する executemany の空リスト渡しは一部バージョンで問題があるため、コード側で空チェックが入っています。空データの扱いに注意してください。

---

README 上の例はライブラリの主要な使い方を示したものです。実際の運用ではログ設定・例外監視・バックテスト環境の分離・API キーの管理（シークレットストア利用）などを適切に行ってください。必要であれば README を拡張して、実行コマンドや CI 設定、requirements.txt / poetry 設定例を追加します。