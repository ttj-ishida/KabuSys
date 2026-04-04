# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（軽量モジュール群）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を使用したセンチメント評価）、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要環境 / 依存パッケージ
- セットアップ手順
- 設定（環境変数・.env）
- 使い方（主要な API 使用例）
- ディレクトリ構成（主なファイル）
- 補足 / 注意点

---

## プロジェクト概要
KabuSys は日本株のデータ取得・前処理・AI（ニュースセンチメント）・因子計算・ETL・監査ログのユーティリティをまとめたモジュール群です。  
設計方針としては「ルックアヘッドバイアスを避ける」「DuckDB を中心としたローカル DB 管理」「外部 API の呼び出しに対する堅牢性（リトライ・レート制御・フェイルセーフ）」を重視しています。

---

## 機能一覧
- データ取得 / ETL
  - J-Quants からの日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース関連
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - ニュースセンチメント（OpenAI の gpt-4o-mini を利用）: 銘柄別 ai_score を ai_scores テーブルへ書き込み（score_news）
  - マクロセンチメント + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等の因子計算（prices_daily / raw_financials に対して）
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のスキーマ初期化・DB 管理ユーティリティ
  - init_audit_db / init_audit_schema による冪等初期化
- 設定管理
  - .env または OS 環境変数からの自動読み込み（プロジェクトルート検出）
  - Settings クラスで各種設定値の取得（例: JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）

---

## 必要環境 / 依存パッケージ（代表例）
- Python 3.10+
- duckdb
- openai (OpenAI の新しい SDK を想定)
- defusedxml
- （標準ライブラリの urllib, json, logging など多数）

インストール例:
```bash
python -m pip install duckdb openai defusedxml
```
（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置
2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. （任意）パッケージを editable インストール
   ```bash
   pip install -e .
   ```
5. 環境変数を設定（下記参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

---

## 設定（環境変数 / .env）

自動で .env をルートから読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for ETL）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能など）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- Settings クラスのプロパティは必須の変数が未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。
- .env のパースはシェル形式に近いですが、クォートやコメントの扱いに対応しています。

---

## 使い方（主要 API 例）

以下は代表的な利用方法（Python スニペット）です。各関数は DuckDB 接続を直接受け取る設計です。

- DuckDB 接続を作成して ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ファイルベースの DuckDB を使用
conn = duckdb.connect(str("data/kabusys.duckdb"))
# 日次 ETL（ターゲット日を指定しなければ今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- News NLP（銘柄別ニューススコア）を生成する:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム（マクロ + ETF MA）を算出する:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログ DB を初期化する（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
# 以降 conn に対して order_requests 等のテーブルが利用可能
```

- カレンダーや営業日判定ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- ファクター計算例:
```python
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主なモジュール）
- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py -- 市場カレンダー管理、営業日ユーティリティ
    - etl.py                 -- ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py            -- ETL 実装（run_daily_etl 等）
    - stats.py               -- 汎用統計関数（zscore_normalize）
    - quality.py             -- 品質チェック（欠損・スパイク等）
    - audit.py               -- 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py      -- J-Quants API クライアント（fetch / save）
    - news_collector.py      -- RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- forward returns / IC / summary / rank

---

## 補足 / 注意点
- OpenAI 利用について
  - news_nlp と regime_detector は OpenAI の Chat Completions（gpt-4o-mini など）を使用します。API キーは OPENAI_API_KEY に設定してください。API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0 など）を備えていますが、従量課金とレイテンシに注意してください。
- J-Quants API 使用について
  - J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。get_id_token → fetch_* 系で使用します。レート制限や 401 自動リフレッシュなどを実装しています。
- ルックアヘッドバイアス対策
  - 多くの処理は target_date を明示的に受け取り、内部で datetime.today() を直接参照しない実装になっています。バックテストで使用する場合は target_date を適切に設定してください。
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を読み込みます。テスト時などに無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB バージョン依存
  - DuckDB の executemany の挙動やバインド可能なリスト型に差があるため、コードは互換性を考慮して実装されていますが、使用する DuckDB のバージョンによっては注意が必要です。

---

ご不明点や README に追記したい具体的な利用例（CI 実行方法、デモスクリプト、Dockerfile など）があれば教えてください。README をその要件に合わせて拡張します。