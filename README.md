# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定のトレーサビリティ）などの機能を提供します。

主な設計方針
- ルックアヘッドバイアス対策（日付の取り扱いに注意）
- DuckDB を中心としたローカル DB 管理（冪等保存、トランザクション）
- 外部 API 呼び出しはリトライ＋バックオフ、レート制御を実装
- テストしやすい設計（依存注入・差し替え可能な内部呼び出し）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード、必須変数の取得（kabusys.config）
- データ ETL（J-Quants 経由）
  - 株価日足、財務データ、JPX マーケットカレンダーの差分取得・保存（kabusys.data.jquants_client / pipeline）
  - ETL の統合実行（run_daily_etl）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（kabusys.data.quality）
- カレンダー管理
  - 営業日判定や next/prev_trading_day 等（kabusys.data.calendar_management）
- ニュース収集
  - RSS フィードの安全な取得・前処理（SSRF 対策・サイズ制限）（kabusys.data.news_collector）
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル初期化／管理（kabusys.data.audit）
- AI（OpenAI）を使った NLP
  - 銘柄ニュースごとのセンチメントスコア算出（score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（score_regime）
- リサーチ / ファクター解析
  - Momentum / Volatility / Value 等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 汎用統計ユーティリティ（z-score 正規化等）

---

## 要件（主な依存パッケージ）

- Python 3.10+（typing の構文などを使用）
- duckdb
- openai
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## インストール手順（開発環境）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトがパッケージ化されていれば）
   - pip install -e .

---

## 環境変数 / 設定

kabusys はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。読み込み順序（優先度）は次の通りです：
1. OS 環境変数
2. .env.local（存在する場合、.env を上書き）
3. .env

自動ロードを無効にするには：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する

主な環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必須）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（デフォルト: INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack 設定（必要に応じて）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等で使用）（デフォルト: data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ（DuckDB / 監査DB の初期化例）

監査ログ用の DB を初期化してテーブルを作成する例:

```python
from pathlib import Path
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

db_path = settings.duckdb_path  # Path object
conn = init_audit_db(db_path)   # DuckDB 接続を返す（監査テーブル作成済み）
# conn は通常の duckdb.DuckDBPyConnection として利用可能
```

既存の接続にスキーマだけ適用する場合は init_audit_schema(conn) を使えます。

---

## 使い方（主要ワークフロー例）

1. 日次 ETL を実行する（J-Quants からデータ取得 → 保存 → 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. ニュース N=LP（銘柄ごとのスコア算出）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} ai_scores")
```

3. 市場レジーム判定（ETF とマクロニュースを組み合わせる）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4. ファクター計算 / リサーチ

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# Z-score 正規化
mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

5. RSS ニュースの取得（安全な取得と前処理）

```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    text = preprocess_text(a["title"] + " " + a["content"])
    # raw_news への保存等はプロジェクトの ETL/保存ロジックを使って行う
```

---

## 開発時の注意点

- AI（OpenAI）呼び出しは外部 API のため、API キーの管理とレート・コストに注意してください。
- J-Quants API はレート制限があります。get_id_token / _request は自動リフレッシュ・レート管理・リトライを行いますが、連続実行は避けてください。
- DuckDB の executemany の制約（空リスト不可など）に注意して実装されています。直接 SQL を編集する際は互換性に気を付けてください。
- 時刻は可能な限り UTC で保存します（audit モジュール等）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
    - パッケージの公開 API（data, strategy, execution, monitoring 等）
  - config.py
    - 環境変数・設定管理（.env 自動ロード、設定プロパティ）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事の LLM による銘柄センチメント算出（score_news）
    - regime_detector.py
      - ETF MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・安全対策
    - calendar_management.py
      - 市場カレンダー管理・営業日判定
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL・初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

（strategy / execution / monitoring はパッケージ公開対象ですが、ここに示したコードスニペットでは実装ファイルが含まれていない可能性があります。プロジェクト全体のソースを参照してください。）

---

## よくある質問 / トラブルシュート

- .env の読み込みが効かない  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時などで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI のレスポンスパースに失敗した場合  
  - モジュールはフェイルセーフとしてスコア 0.0 を返す設計です（警告ログ出力）。問題の切り分けはログを確認してください。

- J-Quants の認証エラー（401）  
  - get_id_token はリフレッシュ機能を持ちます。リフレッシュトークン（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。

---

## 参考

- 設定や使い方の詳細は各モジュール（kabusys.data.jquants_client, kabusys.ai.news_nlp, kabusys.data.pipeline など）の docstring を参照してください。README は全体像と基本的な起動手順を示すことを目的としています。

---

この README は、提供されたコードベースの構造と docstring に基づいて作成しています。実運用前に環境変数や API キーの管理、DB パスや権限の確認を必ず行ってください。