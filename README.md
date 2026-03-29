# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレース）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、上場・カレンダー情報を差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT / アップサート）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS フィードからニュースを収集し raw_news に保存（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores へ書き込み）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成し市場レジームを判定・保存
- 研究用ユーティリティ
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン・IC（情報係数）・統計サマリー
  - Z スコア正規化ユーティリティ
- 監査・トレーサビリティ
  - signal → order_request → execution を遡れる監査テーブル群の定義・初期化ユーティリティ
- 環境設定管理
  - .env / .env.local からの自動読み込み（優先度: OS 環境 > .env.local > .env）
  - 自動ロード無効化フラグあり（テスト時便利）

---

## 動作要件

- Python 3.10+
- 主な依存（最低限）:
  - duckdb
  - openai
  - defusedxml
- （必要に応じて）urllib, json 等の標準ライブラリ

プロジェクトとしては pyproject.toml 等で依存管理する想定ですが、開発環境で手早く試すなら:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env`（と任意で `.env.local`）を用意
   - config.Settings が読み込む環境変数は自動で取り込まれます（ただし project root が .git または pyproject.toml を基準に探索されます）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨の .env に含める主要変数（必須・任意）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, default "development") — "development" / "paper_trading" / "live"
- LOG_LEVEL (任意, default "INFO")

注: 開発中に .env.example 等を参照して `.env` を作成してください（このリポジトリには .env.example は明示されていませんが、Settings のエラーメッセージを参考に環境変数を準備してください）。

---

## 使い方（主要な API 例）

以下は幾つかの典型的な利用例です。すべて Python で duckdb 接続を渡すスタイルです。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに保存される
```

- 監査DB 初期化（init_audit_db / init_audit_schema）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査関連テーブルにアクセスできます
```

- RSS フィード取得（fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 市場カレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しは API キーを要求します。引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ほとんどの関数は「ルックアヘッドバイアス防止」を意識して実装されています（内部で date.today() を使わない等）。バックテストでの取り扱いには注意してください。

---

## ディレクトリ構成（主なファイルと説明）

この README は src/kabusys 配下のコードに基づきます。主要モジュールは次の通りです。

- src/kabusys/
  - __init__.py — パッケージ初期化、公開サブパッケージ定義
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメントスコアリング（ai_scores への書き込み）
    - regime_detector.py — 市場レジーム判定（ETF MA と LLM を合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB への保存関数
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集、前処理、raw_news 保存ロジック
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 共通統計ユーティリティ（Z スコア等）
    - audit.py — 監査テーブル定義・初期化（signal/order_request/execution）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数

補足:
- 各モジュールの docstring に設計方針・処理フロー・フェイルセーフの方針が明記されています。運用・拡張時はこれらを参照してください。

---

## 開発・運用に関する注意点

- .env ファイル自動読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。ルートが見つからない場合は自動ロードをスキップします。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です（テスト時に便利）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env の上書き）
- API キー・トークンの管理
  - J-Quants のリフレッシュトークンは `JQUANTS_REFRESH_TOKEN` に、OpenAI は `OPENAI_API_KEY` に設定してください。
  - jquants_client は 401 受信時に自動リフレッシュして再試行する実装があります。
- LLM 呼び出し
  - news_nlp / regime_detector は OpenAI の JSON Mode を用いて厳密な JSON を期待します。レスポンスパースに失敗した場合はフォールバックやスキップを行うフェイルセーフがあります。
- DuckDB の互換性
  - 一部実装は DuckDB のバージョン (ex. executemany の空リスト扱い等) を想定しています。必要に応じて DuckDB バージョンを揃えてください。
- セキュリティ
  - news_collector は SSRF 対策、XML パースのハードニング（defusedxml）、レスポンスサイズ制限などを行っています。
- テスト
  - 実際の API キーやネットワーク呼び出しを必要とする部分はモック可能な設計になっています（内部の _call_openai_api などはユニットテストで差し替えが想定されています）。

---

## 参考（よく使う関数一覧）

- ETL / Data
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
  - data.jquants_client.fetch_daily_quotes(...)
  - data.jquants_client.save_daily_quotes(...)
- News / AI
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - data.news_collector.fetch_rss(url, source)
- Research
  - research.factor_research.calc_momentum(conn, target_date)
  - research.factor_research.calc_value(conn, target_date)
  - research.factor_research.calc_volatility(conn, target_date)
  - research.feature_exploration.calc_forward_returns(conn, target_date)
- Audit
  - data.audit.init_audit_db(path)
  - data.audit.init_audit_schema(conn, transactional=False)

---

README はここまでです。必要であれば以下も提供できます:
- サンプル .env.example（推奨する環境変数テンプレート）
- 実稼働向け運用手順（cron / Airflow / systemd の例）
- より詳しい API 使用例（コードスニペット / モジュール毎の詳細）