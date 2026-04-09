# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース/NLP による銘柄スコアリング、マーケットレジーム判定、監査ログ（監査テーブル）など、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API からの差分取得（株価・財務・マーケットカレンダー）、DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と LLM を用いたニュースセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの組合せ、LLM によるマクロセンチメント）
- 監査ログ（signal / order_request / executions テーブル）初期化ユーティリティ
- 研究用モジュール：ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、Z スコア正規化

---

## 機能一覧（抜粋）

- kabusys.config
  - 環境変数の読み込み（.env/.env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 設定オブジェクト `settings`
- kabusys.data
  - jquants_client: J-Quants API 呼び出し / ページネーション / 保存（raw_prices, raw_financials, market_calendar）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 収集と前処理、raw_news への冪等保存
  - audit: 監査テーブル作成 / 初期化（init_audit_schema / init_audit_db）
  - calendar_management: 営業日判定・次営業日/前営業日・バッチ更新ジョブ
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に渡して銘柄ごとの ai_score を計算・ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime テーブルへ保存
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）、特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 要件

- Python 3.10 以上（型注釈の記述から想定）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

必要なパッケージは pyproject.toml / requirements.txt があればそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -e .                # パッケージ化されている場合
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。auto-load はパッケージ __file__ を基準にルートを探索します（.git または pyproject.toml が目印）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject）
     - KABUSYS_ENV: development / paper_trading / live
   - 注意: settings クラスが未設定の必須変数にアクセスすると ValueError を投げます。

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下は Python スクリプト／REPL から利用する例です。DuckDB のパスは settings.duckdb_path を利用できます。

1) ETL（データ取得・保存・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY 環境変数を参照
print("ai_scores written:", n_written)
```

3) 市場レジーム判定（OpenAI API 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB 初期化（監査テーブルを別 DB に作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

5) 研究モジュール（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026,3,20))
# records: list[dict] を次工程へ渡して利用
```

---

## 主要 API（概要）

- kabusys.config.settings: 設定アクセス用オブジェクト（プロパティで各種値を取得）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - （RSS 取得→ raw_news 保存などはモジュール関数を組み合わせて利用）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

各関数は docstring に詳細な挙動と設計方針（ルックアヘッドバイアス回避、冪等性、リトライ仕様など）が記載されています。呼び出す前に docstring を参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                                    — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                                 — ニュースセンチメントの LLM 呼び出しと保存ロジック
  - regime_detector.py                          — ETF MA + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                            — J-Quants API クライアント & 保存ロジック
  - pipeline.py                                  — ETL パイプライン（run_daily_etl 等）
  - quality.py                                   — データ品質チェック
  - news_collector.py                             — RSS 収集と前処理
  - calendar_management.py                        — 市場カレンダー管理（営業日判定等）
  - stats.py                                      — 共通統計ユーティリティ（zscore 正規化）
  - audit.py                                      — 監査ログテーブル定義 / 初期化
  - etl.py (export ETLResult)
- research/
  - __init__.py
  - factor_research.py                            — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py                        — 将来リターン / IC / 統計サマリー
- monitoring/ (存在想定: 実行監視関連)
- execution/ (存在想定: 発注関連)
- strategy/ (存在想定: 戦略定義)

---

## 設計上の注意点・運用メモ

- ルックアヘッドバイアス防止:
  - AI モジュール・ETL は内部で `datetime.today()` を直接参照しないよう設計されています。必ず `target_date` を与えて実行してください。
- 環境変数の自動読み込み:
  - パッケージ初期化時にプロジェクトルート（.git / pyproject.toml）を探索し `.env` → `.env.local` の順に読み込みます。OS 環境変数は保護され `.env.local` の上書き対象外にされます。挙動を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 利用:
  - OpenAI 呼び出しには `OPENAI_API_KEY` を環境変数で渡すか、関数引数 `api_key` を使用してください。API 呼び出しはリトライ・バックオフ実装ありですが、API 利用料に注意してください。
- J-Quants:
  - `JQUANTS_REFRESH_TOKEN` が必須です。トークンのリフレッシュ・キャッシュ・レート制御を内部で行います。
- DuckDB バージョン:
  - 本コードは DuckDB の特性（executemany の空リスト扱いなど）を考慮しています。運用環境の DuckDB バージョンにより挙動が変わることに注意してください。

---

## 開発 / 貢献

- コードスタイル・テストはリポジトリに合わせてください。ユニットテストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックする設計になっています（関数単位で差し替え可能）。
- 重大な変更は設計方針（Look-ahead 回避、冪等性、トレーサビリティ）を尊重してください。

---

README は以上です。必要であれば、.env.example の具体例、CI / デプロイ手順、より詳細な API リファレンスやユースケース（cron で日次 ETL を回す方法等）を追加します。どの情報を優先的に追記しましょうか？