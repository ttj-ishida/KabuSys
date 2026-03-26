# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注トレース）などを含みます。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集と前処理、ニュース -> 銘柄マッピング
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化ユーティリティ

パッケージ内部は DuckDB をデータ層、J-Quants/OpenAI を外部データソースとして想定しています。Look-ahead bias を防ぐ設計が各所で組み込まれています（内部で datetime.today() を直接参照しない等）。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API との取得・保存・認証・レート制御
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: 営業日判定・次/前営業日取得・JPX カレンダー同期ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル作成 / 監査 DB 初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得・ai_scoresへ書込
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロセンチメントを合成した市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み（.env / .env.local をプロジェクトルートから自動ロード。必要に応じて無効化可能）

---

## 前提 / 必要環境

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（パッケージ名 openai）
- defusedxml（RSS パース用）
- （任意）その他ライブラリ：logging 等は標準ライブラリ

推奨インストール（例）:
```
pip install duckdb openai defusedxml
# または開発用にプロジェクトを editable install する場合
pip install -e .
```

（プロジェクトに setup / pyproject があれば pip install -e . で依存をまとめて入れる想定）

---

## 環境変数

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先、.env.local は .env を上書き）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（主要）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector が使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注モジュール等）
- SLACK_BOT_TOKEN: 通知用 Slack ボットトークン
- SLACK_CHANNEL_ID: 通知先の Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（検証用・安全スイッチ）
- LOG_LEVEL: DEBUG/INFO/...

設定に失敗すると Settings プロパティから ValueError が送出されます。`.env.example` を用意して値を参考にしてください（プロジェクトルートに配置する想定）。

---

## セットアップ手順（例）

1. リポジトリをクローン / 取得
2. Python 仮想環境作成:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージをインストール:
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトルートで
   pip install -e .
   ```
4. 環境変数を設定（.env/.env.local）:
   ```
   # .env (例)
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   ※ セキュアな情報は .env.local に置き、.gitignore で管理することを推奨します。

5. DuckDB スキーマ作成（プロジェクトにスキーマ初期化スクリプトがある場合はその手順に従ってください）。監査 DB 初期化は以下で可能:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要ユースケースの例）

以下は簡単な Python からの呼び出し例です。実運用ではログ設定やエラーハンドリング、環境分離を整えてください。

- DuckDB に接続して日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を利用）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化（別 DB を使いたい場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された DuckDB 接続が返る
```

- 研究モジュール例（ファクター計算）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

---

## よく使う API（主要関数）

- kabusys.config.settings: 環境変数取得ラッパー
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline:
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

---

## ディレクトリ構成（概略）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
    - (その他モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (省略可能)
  - strategy/ (戦略実装場所、発注ロジック等)
  - execution/ (ブローカー連携の実装)
  - monitoring/ (監視・アラート実装)

（上記はコードベースから抜粋した主要ファイル群です）

---

## 注意事項 / ベストプラクティス

- APIキーやトークンは環境変数で管理し、ソース管理に含めないでください。
- OpenAI 呼び出しはコストとレート制限に注意してください。score_news と score_regime はリトライ・フォールバックを組み込んでいますが、実運用ではバッチ頻度を慎重に決めてください。
- DuckDB への書き込みはトランザクション管理が行われている箇所とそうでない箇所があります。スキーマ変更や大規模変更を行う場合はバックアップを忘れずに。
- 本リポジトリの関数は「Look-ahead bias を避ける」設計がなされていますが、バックテスト等で利用する場合は取り扱いに注意してください（データ取得タイミングや fetched_at の扱い等）。

---

問題や追加のドキュメント化（API ドキュメント、導入手順スクリプト、CI 設定など）が必要であれば、どの部分を優先して整備すべきか教えてください。README を用途（開発者向け / 運用者向け）に合わせて拡張します。