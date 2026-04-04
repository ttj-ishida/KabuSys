# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP によるスコアリング、ファクター計算、監査ログの管理、マーケットカレンダー管理など、バックテスト〜本番運用に必要となるユーティリティ群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、上場銘柄情報、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース収集・NLP
  - RSS からニュース記事を収集して正規化・保存（SSRF・XML 脆弱性対策あり）
  - OpenAI（gpt-4o-mini 等）を利用した銘柄別ニュースセンチメントのバッチスコアリング（ai_scores テーブルへ保存）
  - マクロ経済ニュースを使った市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメント 合成）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターンの計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化など

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定まで追跡可能な監査テーブル定義（冪等性・タイムスタンプ・インデックス含む）
  - 監査DB初期化ユーティリティ

- マーケットカレンダー管理
  - market_calendar テーブルの取得 / 更新、営業日判定、next/prev trading day 等

- 設定管理
  - .env ファイルまたは環境変数から自動ロード（プロジェクトルート検出）
  - .env.local の優先・上書き、OS 環境変数保護、ロード無効化フラグあり

---

## 動作要件

- Python 3.10 以上（typing の構文と型注釈に依存）
- ランタイム依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそちらを使用してください）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布済みであれば:
# pip install -e .
```

---

## セットアップ

1. リポジトリをクローン／配置する（パッケージ構成は src/kabusys 以下）。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（または使用する機能によって必須になる）環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注等で使用）
- OPENAI_API_KEY : OpenAI を使う機能（news_nlp / regime_detector）で使用（各関数は引数で鍵を渡すことも可能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)（デフォルト INFO）

例 .env（最小）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUYS_ENV=development
LOG_LEVEL=DEBUG
```

設定取得は `from kabusys.config import settings` で行えます。settings オブジェクト経由で各種パスやフラグにアクセスできます。

---

## 使い方（主要な例）

以下はライブラリを直接インポートして使うサンプルです。各関数はテスト容易性のため api_key 等を引数で上書きできます。

- DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（対象日を指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を渡すことで環境変数を用いずに実行可能
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {n_written} symbols")
```

- 市場レジーム判定（ma200 乖離 + LLM マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 返り値は duckdb 接続。監査用テーブルが作成される。
```

- ファクター計算 / リサーチ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

date0 = date(2026,3,20)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

is_trading = is_trading_day(conn, date(2026,3,20))
next_day = next_trading_day(conn, date(2026,3,20))
days = get_trading_days(conn, start=date(2026,3,1), end=date(2026,3,31))
```

注意点:
- OpenAI を使う処理は API エラー時にフォールバックする設計（API 失敗時はスコア 0.0 やスキップなど）。API 呼び出しの再試行・バックオフは組み込まれています。
- J-Quants API 呼び出しもレートリミットや 401 自動リフレッシュ、再試行を備えています。
- 各種関数では内部で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。必ず target_date を明示するかデフォルトの挙動を確認してください。

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys 以下に実装されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                            # 環境変数・設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                        # ニュースセンチメント・OpenAI 呼び出し
    - regime_detector.py                 # 市場レジーム判定（MA + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント（取得・保存）
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - etl.py                             # ETLResult 再エクスポート
    - news_collector.py                  # RSS 収集・前処理・保存
    - calendar_management.py             # マーケットカレンダー管理・営業日の判定
    - quality.py                         # データ品質チェック
    - stats.py                           # 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                           # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py                 # ファクター計算（momentum, value, volatility）
    - feature_exploration.py             # 将来リターン・IC・統計サマリー等
  - monitoring/ (存在すれば監視用モジュール等を配置)

（上記はコードベースに含まれる主要モジュールの一覧です）

---

## 実運用時の注意点 / トラブルシューティング

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索します。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI/API キーを明示的に関数引数で渡すことが可能で、ユニットテスト時にモックしやすい設計になっています。
- DuckDB の executemany が空リストを受け付けないバージョン依存の挙動を考慮した実装がなされています。DB 操作で問題が発生した場合は使用している duckdb のバージョンを確認してください。
- ニュース収集は SSRF・XML インジェクション対策（リダイレクト検査、defusedxml など）を実装していますが、入力 RSS ソースの管理は利用者側で行ってください。
- 本コードベースは「データ取得・処理・リサーチ」用のユーティリティ群であり、実際の発注ロジック（kabu ステーション連携など）およびリスク管理ルールは別モジュール／上位実装で統合する前提です。

---

この README はコードベースの現在実装に基づく概要と利用ガイドです。詳細な API の使い方や追加のセットアップ（証券会社 API の接続、LINE 通知など）は各機能の実装ドキュメントや運用ドキュメントを参照してください。必要であれば、個別の使い方やサンプルスクリプトも作成します。