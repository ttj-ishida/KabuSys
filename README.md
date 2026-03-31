# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを含み、運用・研究両面に対応します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と OpenAI によるニュースセンチメント評価
- 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
- ファクター算出（モメンタム・バリュー・ボラティリティ等）とリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- J-Quants / kabu ステーションとの連携ユーティリティ

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」を重視しています。

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 関数、ID トークン管理、レートリミット）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF や Gzip/Bomb 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に書き込み）
  - レジーム判定（score_regime: ETF 1321 の MA とマクロニュースを合成）
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - 環境変数読み込み（.env / .env.local 自動読み込み）と Settings オブジェクト

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（最低限）
   - pip install duckdb openai defusedxml

   プロジェクトに requirements.txt がある場合はそれを使用してください。

3. ソースをインストール（開発モード）
   - pip install -e .

   ※ setup / pyproject がある前提。なければプロジェクト直下で PYTHONPATH に src を追加するか、上記パッケージをインストールして利用してください。

4. 環境変数（.env）を作成
   - プロジェクトルートの .env または .env.local に必要なキーを設定します。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例 (.env):
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

必須（ライブラリ機能を使うために少なくとも設定が必要なもの）:
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（ai 機能を使う場合）
- KABU_API_PASSWORD（kabu API 連携をする場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）

---

## 使い方（主要例）

以下は代表的な利用例です。DuckDB 接続にはパスを与えてください（settings.duckdb_path 参照）。

- 基本の ETL 実行（日次パイプライン）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別に株価 ETL を実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュースセンチメントスコア計算（AI）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返ってきた conn に対してアプリケーションは監査テーブルを使用できます
```

- ファクター算出例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(recs), recs[:3])
```

注意事項:
- AI（OpenAI）呼び出しは OPENAI_API_KEY を参照。api_key 引数で明示的に渡すことも可能。
- モジュールの多くは DuckDB のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）を前提にしています。ETL を実行してテーブルを作成/埋めてください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save 等）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL インターフェース再エクスポート
    - calendar_management.py -- マーケットカレンダー管理
    - news_collector.py      -- RSS ニュース収集
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー等

補足:
- モジュールごとにログを出すよう設計されています（logging を利用）。アプリ側で logging.basicConfig(...) 等を設定して運用してください。

---

## 実運用・開発上の注意点

- ルックアヘッドバイアス防止:
  - 多くの関数が date 引数を受け取り、内部で datetime.today() を参照しないように設計されています。バックテスト時は必ず過去時点のデータのみを渡して利用してください。
- 冪等性:
  - J-Quants の保存関数や監査スキーマ初期化は冪等に設計されています（ON CONFLICT や IF NOT EXISTS を使用）。
- フェイルセーフ:
  - AI API の失敗時はフォールバック（0.0 等）で処理を継続する設計が多く採用されています。重大な失敗はログに出力されますが、運用判断は呼び出し元で行ってください。
- セキュリティ:
  - news_collector は SSRF 対策、XML 害対策（defusedxml）、レスポンスサイズ制限等が組み込まれています。
- テスト:
  - OpenAI 呼び出しなどは内部で分離された関数を用意しており、unittest.mock.patch による差し替えが想定されています。

---

## ライセンス / 貢献

この README はコードベースから自動生成した概要です。実際に運用する際はリポジトリの LICENSE や CONTRIBUTING を参照してください。

---

必要であれば、README に動作フロー図・DB スキーマ一覧・よくあるエラーと対処法などを追加します。どの項目を詳しく追記しましょうか？