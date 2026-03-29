# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュース収集、データ品質チェック、ファクター計算、AI を用いたニュースセンチメント判定、監査ログ等の機能を含み、DuckDB を中心に設計されています。

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と差分 ETL
- RSS ベースのニュース収集と銘柄紐付け
- ニュースに対する LLM（OpenAI）による銘柄別 / マクロセンチメント評価
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 市場カレンダー管理・営業日計算

設計上の特徴：
- Look-ahead bias を避ける設計（内部で date.today()/datetime.today() を不用意に参照しない等）
- DuckDB を利用したローカルデータレイヤー
- 冪等（idempotent）な DB 保存ロジック
- 外部 API 呼び出しに対するリトライ / レート制御 / フェイルセーフ

---

## 主な機能一覧

- 設定管理
  - 環境変数と .env/.env.local の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由でのアクセス（例: settings.jquants_refresh_token）

- Data / ETL
  - J-Quants クライアント（fetch/save の実装、レートリミット・リトライを内包）
  - 日次 ETL パイプライン `run_daily_etl`（カレンダー、株価、財務、品質チェックを実行）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 統計ユーティリティ（Z スコア正規化等）
  - 監査ログ初期化（監査テーブルの DDL / インデックス生成）

- AI（OpenAI）
  - 銘柄別ニュースセンチメント: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコア合成）: score_regime(conn, target_date, api_key=None)
  - LLM 呼び出しは gpt-4o-mini を想定し、JSON Mode でレスポンス検証を行う

- Research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン算出、IC（Information Coefficient）、統計サマリー等

---

## 要件（Prerequisites）

- Python 3.10 以上（typing の新構文（|）を使用）
- 推奨パッケージ（最低限動かすため）:
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを pip editable install できる setup がある場合:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数 / 設定

settings（kabusys.config.settings）で利用される主要な環境変数：

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード（発注などに利用する想定）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID      : 通知対象 Slack チャネル ID

- 任意（デフォルトあり）
  - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視系 sqlite 等（デフォルト: data/monitoring.db）
  - KABUSYS_ENV           : run 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - LOG_LEVEL             : ログレベル ("DEBUG", "INFO", ...)(デフォルト: INFO)
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）

自動 .env 読み込みの挙動：
- プロジェクトルート（.git または pyproject.toml を基準）から .env を読み込み、.env.local を上書き読み込みします。
- OS 環境変数が優先されます。
- テストなどで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境と依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   # 追加で必要なパッケージがあれば適宜インストール
   ```

3. 環境変数を用意（.env/.env.local）
   - README 上の例を参考に .env を作成してください。

4. DuckDB 等の初期化（監査 DB を使う場合）
   Python REPL やスクリプトから：
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # または既存の接続にテーブルを追加
   # from kabusys.data.audit import init_audit_schema
   # init_audit_schema(conn)
   ```

---

## 使い方（主要な API 例）

以下は代表的な呼び出し例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で可
print(f"written {written} scores")
```

- 市場レジームスコアを算出して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- ニュース RSS を取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログスキーマ初期化（別 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 必要なテーブルを作成して返す
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list of dict with keys date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

各関数の引数や戻り値、エラー動作はソースコードの docstring を参照してください。

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env の自動ロードと settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py : 銘柄別ニュースセンチメント算出（score_news）
  - regime_detector.py : マクロセンチメント + ETF MA を使った市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（fetch/save）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py : ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py : RSS の収集・前処理・保存ヘルパー
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py : 統計ユーティリティ（zscore_normalize 等）
  - audit.py : 監査ログ（シグナル/発注/約定テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ等の計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク処理
- monitoring, strategy, execution など（パッケージ公開名に含まれるが今回提示コードでは一部が省略または別ファイルで実装想定）

（上記は本リポジトリ内にある主要モジュールの抜粋説明です）

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しはコストとレート制限があります。テスト時はモックすることを推奨します（ソース内にモック可能な内部関数設計あり）。
- J-Quants API の呼び出しはレート制御とリトライを備えていますが、API キーとリフレッシュトークンは安全に管理してください。
- ETL は部分失敗に耐える設計ですが、品質チェックの結果（QualityIssue）は運用ポリシーに従って対応してください（例えば重大な error を検出したらアラートする等）。
- DuckDB の executemany に関するバージョン差異へ配慮した実装になっていますが、DuckDB バージョンは適宜最新版を使用することを推奨します。
- 自動 .env ロードの挙動はプロジェクトルートの検出に依存します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと安定します。

---

この README はソースコードに基づく要約です。各機能の詳細・パラメータや戻り値についてはソースコード中の docstring を参照してください。必要であれば各モジュール用のより詳しいドキュメントを作成します。