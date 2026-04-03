# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたスコアリング）、市場レジーム判定、ファクター計算、監査ログ（発注→約定トレーサビリティ）などの機能を提供します。

## 特徴（概要）
- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS からのニュース収集と前処理（SSRF/トラッキング対策）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント/銘柄別 AI スコアリング（batch, retry, JSON mode 対応）
- ETF（1321）200日移動平均乖離 と マクロニュースセンチメントを合成した「市場レジーム」判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）・特徴量解析ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化ユーティリティ
- 環境変数による設定管理（.env 自動ロード機能あり）

---

## 機能一覧
- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 関数
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss, URL 正規化・SSRF/トラッキング対策・前処理
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログスキーマ: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 指定日ウィンドウのニュースを銘柄別に集約して OpenAI でスコア化し ai_scores に書き込み
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュースセンチメントの合成により market_regime にスコアを書き込み
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（主要な依存）
- Python 3.9+（ソースは typing | list[str] 等を使用）
- 外部ライブラリ:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS フィードへの HTTP(S)

（依存は setup / requirements にまとめてください。ここでは主要なものを列挙しています。）

---

## 環境変数（.env）
config.Settings で環境変数を読み込みます。プロジェクトルートの `.env` / `.env.local` を自動で読み込む仕組みがあります（CWD に依存せずパッケージの場所からプロジェクトルートを探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

最低限設定が必要な環境変数（用途）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視向け DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env の簡易テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存のインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそちらを利用）
   - 開発用に editable install: pip install -e .
4. 環境変数設定
   - プロジェクトルートに `.env` を作成（上記テンプレート参照）
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
5. DuckDB ファイル作成（必要に応じて）
   - ディレクトリ作成: mkdir -p data
   - 初期スキーマは利用するモジュール側で作成。監査ログ用 DB を作るには下記参照

---

## データベース初期化（監査ログ例）
監査ログ用の DuckDB を初期化するユーティリティがあります。

```python
import kabusys.data.audit as audit
conn = audit.init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

init_audit_db は transactional=True 相当でスキーマを作成します。引数に ":memory:" を渡せばインメモリ DB になります。

---

## 使い方（主要な API 例）

- DuckDB 接続の作成（設定からパスを取得）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

- ニュースを取得して銘柄別に AI スコアを生成（OpenAI API KEY が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数または api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

- 統計ユーティリティ（Zスコア正規化）
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意点 / 設計上の要点
- Look-ahead バイアス対策:
  - 日時比較には target_date を明示的に渡し、内部で date.today() を参照しない実装方針のモジュールがあります（AI スコアリング、レジーム判定等）。
- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を使用し冪等に保存します。
  - 監査ログでは order_request_id を冪等キーとして扱う設計です。
- エラーハンドリング:
  - 外部 API 呼び出しはリトライ・バックオフを備え、API 失敗時は安全側の値で継続する設計（LLM 失敗時は 0.0 にフォールバックなど）。
- セキュリティ:
  - RSS 取得では SSRF 対策（リダイレクト先検査・プライベートアドレス拒否）や XML の安全パーサ（defusedxml）を使用しています。
- テスト時のフック:
  - OpenAI 呼び出し箇所はモックしやすいように内部関数を分離しています（ユニットテストの差し替えが容易）。

---

## ディレクトリ構成（主なファイル）
（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースの AI スコア化（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存関数
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult の公開（エイリアス）
    - news_collector.py                — RSS 収集・前処理
    - calendar_management.py           — 市場カレンダー管理・判定
    - quality.py                       — データ品質チェック
    - stats.py                         — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py           — 将来リターン/IC/統計サマリー 等

---

## 開発 / テストのヒント
- 自動で .env をロードするため、テスト時に OS 環境変数を使いたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や J-Quants の実 API 呼び出しは単体テストでは外部依存になるため、network call をモックしてください（各モジュールは内部 `_call_openai_api` / `_urlopen` 等を差し替え可能な実装になっています）。
- DuckDB を ":memory:" で利用すればファイルを作らずに単純な統合テストが可能です。

---

README に記載した内容は実装の主要点に基づく概要です。運用やデプロイ時には .env の管理、API キーの保護、監視・ロギング設定を適切に行ってください。必要であれば README を拡張して CI/CD、デプロイ手順、具体的なスキーマ定義や SQL の例などを追加できます。