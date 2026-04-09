# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、ニュース NLP（OpenAI）を用いた銘柄スコアリング、研究用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## 特徴（概要）

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存するETLパイプライン
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース記事収集 / 前処理 & OpenAI を用いた銘柄別センチメント（ai_scores）生成
- マクロセンチメントと ETF MA200 を合成した市場レジーム判定（bull / neutral / bear）
- 研究用ファクター計算モジュール（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 環境変数 / .env 自動ロード（プロジェクトルート検出による）

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client によるページネーション対応 API 呼出し、保存関数（save_*）
- データ品質
  - quality.run_all_checks をはじめとした多様なチェック（欠損 / 重複 / スパイク / 日付）
- ニュース NLP
  - score_news(conn, target_date, api_key=None) — 銘柄ごとの ai_score を ai_scores に書き込む
  - fetch_rss / news_collector（RSS 取得と前処理）
- 市場レジーム判定
  - score_regime(conn, target_date, api_key=None) — ETF (1321) の MA200 乖離 + マクロ新聞センチメントを合成
- 研究用
  - research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査ログ（トレーサビリティ）
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path) — 監査用 DuckDB を作成して初期化
- 設定管理
  - kabusys.config.settings で各種設定値・パスを参照可能（.env 自動ロードあり）

---

## 動作要件（主な依存）

（実際の pyproject / requirements の内容に依存しますが、ソースから分かる主な依存）
- Python 3.10+
- duckdb
- openai
- defusedxml

その他: 標準ライブラリ（urllib, json, logging など）

インストール例（開発環境）:
```bash
# ソースルートで
pip install -e ".[dev]"   # pyproject/requirements による想定
# または最低限
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成し依存をインストール
3. プロジェクトルートに `.env` を作成（例は下記）
   - パッケージ起動時に .env を自動で読み込みます（.git または pyproject.toml の位置からルート検出）
   - テストなどで自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
4. DuckDB / SQLite データディレクトリを作成（settings が自動で path の parent を作る関数を提供する場所もあります）
5. OpenAI / J-Quants の API キーを .env に設定

.env の例（テンプレート）
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# 実行環境
KABUSYS_ENV=development        # development | paper_trading | live
LOG_LEVEL=INFO

# Paper trading の Fill モード（instant, partial, never, reject）
PAPER_FILL_MODE=instant
```

重要：
- 必須: JQUANTS_REFRESH_TOKEN（ETL）
- OpenAI を使う機能：OPENAI_API_KEY（score_news / score_regime 等）

---

## 初期化（監査DB など）

監査用のスキーマを作成する例:
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイルDB を作る例
conn = init_audit_db("data/kabusys_audit.duckdb")
# またはメモリ:
# conn = init_audit_db(":memory:")
```

既存の DuckDB 接続へスキーマだけ追加する場合:
```python
from kabusys.data.audit import init_audit_schema
# conn は既に開いている duckdb connection
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要な API と実行例）

DuckDB 接続の取得と ETL 実行（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # ENV OPENAI_API_KEY を使う
print(f"written {num_written} scores")
```

市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

研究用ファクター計算の例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

ニュース収集（RSS）例
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```
（fetch_rss は SSRF 対策、gzip 対応、XML パースの安全処理が組み込まれています）

---

## 環境設定の挙動

- .env の自動読み込み:
  - 検出順: OS 環境 > .env.local > .env
  - プロジェクトルートはこのモジュールファイルを起点に上位ディレクトリに `.git` か `pyproject.toml` がある場所を探します。見つからなければ自動ロードをスキップします。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- settings で参照できる主なキー:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD, KABU_API_BASE_URL
  - OPENAI_API_KEY（score_news / regime）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL（DEBUG/INFO/...）
  - PAPER_FILL_MODE（paper trading の模擬約定挙動）

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                           — 環境変数 / .env ロードと Settings
- ai/
  - __init__.py
  - news_nlp.py                        — ニュースの OpenAI スコアリング（score_news）
  - regime_detector.py                 — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                  — J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
  - etl.py                             — ETL 結果型再エクスポート
  - stats.py                           — zscore_normalize 等の統計ユーティリティ
  - quality.py                          — データ品質チェック
  - calendar_management.py             — 市場カレンダーと営業日判定
  - news_collector.py                  — RSS 収集・前処理
  - audit.py                           — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                 — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py             — calc_forward_returns / calc_ic / factor_summary / rank
- ai/ (上記)
- research/ (上記)
- その他: strategy / execution / monitoring 等のトップレベルモジュールは __all__ に含まれます（詳細はパッケージ内参照）

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス対策として、多くの関数は内部で現在時刻を参照せず、明示的な target_date 引数を必須または利用する設計です。バックテストや再現性のある処理では target_date を明示的に渡してください。
- OpenAI 呼び出しは外部サービス依存のため、API キーや料金に注意してください。API 呼び出しはリトライ＆フォールバックロジックを備えていますが、失敗時は安全側のデフォルト（score=0.0 等）で処理を継続します。
- ETL は差分更新＆バックフィル設計になっており、既存データ保護のため DB への書き換えは冪等（ON CONFLICT DO UPDATE）を基本としています。
- ニュース収集では SSRF 対策（リダイレクト先検査 / プライベートIPブロック）や XML の安全パーシング（defusedxml）を行っています。

---

## 貢献

- バグ報告・機能提案は Issue へお願いします。
- コード修正は PR を送ってください。スタイルやテストの指針はリポジトリの CONTRIBUTING を参照してください（存在する場合）。

---

以上が README の概要です。必要であれば、環境別のデプロイ手順（systemd ジョブ、cron、Dockerfile 等）やより詳細な API リファレンス（各モジュールの公開関数一覧・シグネチャ）を追記します。どの追加情報が必要か教えてください。