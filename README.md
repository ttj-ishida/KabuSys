# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの収集・NLP、マーケットレジーム判定、ファクター研究、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム／研究環境向けに設計されたモジュール群です。  
主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等データ取得と DuckDB への安全な保存（冪等）
- 日次 ETL パイプラインと品質チェック
- RSS ニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（AIスコア）算出と市場レジーム判定
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 発注〜約定まで追跡可能な監査ログスキーマ

設計上、バックテストや実運用での「ルックアヘッドバイアス」を避ける工夫（日時の明示的管理、API 呼び出しの扱い）が組み込まれています。

---

## 主な機能一覧

- config
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由の設定取得（JQUANTS_REFRESH_TOKEN など）
- data
  - jquants_client: J-Quants API からの取得（差分・ページネーション・トークン自動更新・レート制限）
  - pipeline / etl: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（株価, 財務, カレンダー）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS フィード収集と raw_news への保存補助
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev_trading_day など）
  - audit: 監査ログスキーマ初期化 / audit DB 初期化
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提: Python 3.9+（typing の一部記法に依存）。DuckDB や OpenAI クライアント等が必要です。

1. リポジトリをクローンして開発用インストール（任意）
   - pip を使用したインストール例:
     - pip install -e .（パッケージ化されている場合）
     - あるいは依存パッケージを個別にインストール

2. 依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリのみで済む部分も多いですが、上記は必須機能で必要）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
     自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（jquants_client で使用）
     - KABU_API_PASSWORD : kabuステーション API パスワード（注文実行部分で利用予定）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
     - OPENAI_API_KEY : OpenAI API キー（ai モジュールで使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / ... （デフォルト: INFO）
     - DUCKDB_PATH : デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH : デフォルト `data/monitoring.db`

4. データベース用ディレクトリ作成
   - DuckDB ファイルの親ディレクトリがなければ作成してください（save 関数は parent を作成する場合あり）。

---

## 使い方（簡易例）

以下は Python REPL やスクリプト内から呼ぶ際の例です。

- 設定値の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB に接続して日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント算出（AI）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（AI）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # parent dir は自動作成
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
values = calc_value(conn, date(2026,3,20))
normalized = zscore_normalize(momentum, ["mom_1m","mom_3m"])
```

- RSS フィード収集（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意:
- OpenAI クライアント呼び出しは API の成功/失敗にフォールバックする設計です（失敗時はスコア 0.0 等にフォールバック）。
- J-Quants 呼び出しはレート制限済みでリトライ・トークン自動更新機構があります。

---

## 環境変数（要約）

必須（利用する機能に応じて）
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## トラブルシューティング / 注意点

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時や CI で制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- J-Quants API はレート制限があり、jquants_client は固定間隔スロットリングで守っています。大量リクエストは避けてください。
- OpenAI のレスポンスは JSON mode を利用し厳密な JSON を期待していますが、パース失敗等に備えてフォールバック処理が実装されています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所では空チェックを行っています。
- 時刻は設計上 UTC（DuckDB 内） / JST の変換に注意しています。ai モジュールや news_window 等は UTC naive datetime を内部で扱う仕様です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch / save）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult の再エクスポート
    - quality.py                   -- データ品質チェック
    - news_collector.py            -- RSS 収集と前処理
    - calendar_management.py       -- 市場カレンダー管理（営業日判定等）
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- calc_momentum, calc_value, calc_volatility
    - feature_exploration.py       -- calc_forward_returns, calc_ic, factor_summary, rank

この README はプロジェクトの主要な使用方法と全体像の説明を目的としています。実際の運用や拡張では、環境変数の管理や API キーの保護、データベースのバックアップなど運用面の配慮を行ってください。必要であれば各モジュールごとの詳細ドキュメント（関数の引数・戻り値・副作用など）も別途作成できます。