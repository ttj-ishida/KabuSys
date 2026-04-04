# KabuSys

日本株向け自動売買 / データプラットフォームのライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、研究用のファクター計算、監査ログ、J-Quants / kabu API 客を含むモジュール群を提供します。

---

## 目次

- プロジェクト概要
- 主な機能
- 動作要件
- セットアップ手順
- 環境変数（.env）一覧
- 使い方（簡単なコード例）
- 主要モジュールの説明
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせて、日本株のデータ管理・解析・自動売買パイプラインを構築するための内部ライブラリです。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA + マクロセンチメントの組合せ）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック
- 監査ログ（signal → order_request → executions を追跡するテーブル）
- kabu API / LINE 等との連携を想定した設定管理

設計上の考慮点として、ルックアヘッドバイアス回避、API 呼び出しのリトライ・レート管理、冪等性（DB書き込み）に注意しています。

---

## 主な機能（抜粋）

- ETL
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の日次パイプライン
  - 差分取得・バックフィル（データ後出し修正吸収）
- データ取得 / 保存
  - J-Quants クライアント（fetch / save 系）
  - DuckDB へ冪等保存（ON CONFLICT を使用）
- ニュース
  - RSS 収集（SSRF 防御、URL 正規化、トラッキングパラメータ排除）
  - ニュースを銘柄ごとに集約して OpenAI へ投げる（score_news）
- AI
  - score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
- 研究（research）
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析ユーティリティ
  - zscore_normalize：Zスコア正規化（data.stats）
- データ品質
  - 欠損・重複・スパイク・日付不整合チェック（quality.run_all_checks）
- 監査ログ
  - init_audit_db / init_audit_schema：監査用テーブルの初期化（DuckDB）

---

## 動作要件

- Python 3.10 以上（| 演算子などの構文を利用）
- 推奨パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml

（実運用時はその他の依存関係やバージョン固定を requirements.txt で管理してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージソースを配置

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   (パッケージの依存管理はプロジェクト実態に合わせて requirements.txt / pyproject.toml を用意してください)

4. 環境変数を設定
   - プロジェクトルートに .env を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数の例は次節参照。

---

## 環境変数（主要）

config.Settings から参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の取得に使用。

- KABU_API_PASSWORD (必須)
  - kabu ステーション API 用パスワード。

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)

- OPENAI_API_KEY
  - OpenAI 呼び出しに利用。score_news / score_regime は引数で渡すことも可能。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - LINE 通知に使用（任意）。

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - 監視・監督用フラグ・PID ファイルの設定。

- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視閾値

- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env ファイルは通常プロジェクトルート（.git または pyproject.toml がある場所）に置くと自動ロードされます。

---

## 使い方（簡単な例）

以下は DuckDB を使った代表的な呼び出し例です。実際にはログ設定・例外処理を追加してご利用ください。

- DuckDB 接続を作成して ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが環境変数に設定されている場合）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:

```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 監査DB を初期化して接続を取得する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

注意点:
- score_news / score_regime は OpenAI による呼び出しを含むため、API キーと利用料金に注意してください。
- ETL / J-Quants クライアントは rate limiting / retry を組み込んでいますが、id_token や API 上限には留意してください。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env の自動読み込み（プロジェクトルート基準）。Settings クラスで環境変数を型安全に取得します。
- kabusys.data.jquants_client
  - J-Quants API との通信、ページネーション、id_token リフレッシュ、DuckDB への保存関数を提供。
- kabusys.data.pipeline
  - run_daily_etl を中心とした ETL パイプライン。ETLResult を返します。
- kabusys.data.news_collector
  - RSS フィードの取得、前処理、raw_news への保存。SSRF/サイズ上限/XML 脆弱性対策済み。
- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - OpenAI を用いたセンチメント解析と市場レジーム判定の実装（JSON Mode を利用）。
- kabusys.research
  - ファクター計算・特徴量解析ユーティリティ（モメンタム / ボラティリティ / バリュー / IC 等）。
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）。
- kabusys.data.audit
  - 監査ログ用テーブルの DDL / 初期化。signal → order_request → executions のトレーサビリティを確保。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

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
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - audit.py
    - etc.
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - monitoring/, strategy/, execution/  # パッケージ公開候補として __all__ に含まれるがコードは一部（省略）

（上記はコードベースの一部を抜粋した構成です。実際のリポジトリには他のモジュール / テスト / CI 設定等が含まれる場合があります）

---

## 設計上の留意点（短いメモ）

- ルックアヘッドバイアス防止:
  - 各種処理は date 引数を明示的に受け、内部で datetime.today()/date.today() を直接参照しない実装を重視しています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE（あるいは DO NOTHING）で重複を排除します。
- フォールトトレランス:
  - OpenAI / J-Quants 呼び出しはリトライ（指数バックオフ）を行い、致命的でない場合はフォールバック値で継続します。
- セキュリティ:
  - RSS の URL 正規化 / トラッキングパラメータ除去、SSRF 対策、defusedxml を利用しています。

---

必要であれば、この README を元に .env.example や requirements.txt、簡単な使い方の Jupyter ノートブック（チュートリアル）を追加で作成します。どの部分を優先して補足しますか？