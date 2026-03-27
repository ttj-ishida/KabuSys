# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ群。  
DuckDB を用いた市場データ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・監査ログ化・外部API連携（J-Quants、OpenAI 等）を行うためのユーティリティ群です。  
以下の用途に適しています。

- J-Quants からの株価・財務・カレンダーの差分 ETL（DuckDB 保存、冪等）
- RSS ニュース収集と OpenAI を使った銘柄別センチメントスコア付与
- マクロニュース + ETF MA を用いた市場レジーム（bull/neutral/bear）判定
- ファクター生成（モメンタム / ボラティリティ / バリュー）とリサーチ用ユーティリティ
- 監査ログ（signal → order_request → execution）用スキーマの初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の要点:
- ルックアヘッドバイアスを避ける（target_date 指定ベース、datetime.today() を直接使用しない箇所が多い）
- DuckDB を単一の分析用 DB として利用（オンメモリ or ファイル）
- API 呼び出しはリトライ／バックオフやレート制御を備える
- 冪等性を重視（ON CONFLICT / INSERT/DELETE の扱い）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・保存用ユーティリティ）
  - データ品質チェック（missing, spike, duplicates, date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを用いた銘柄別 AI スコアリング（OpenAI）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py: .env 自動読み込み・設定管理
- audit, pipeline, calendar 等、実運用に必要なスキーマ・ジョブ群

---

## 動作要件

- Python 3.10+
- 必要な主要パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

（実プロジェクトでは pyproject.toml / requirements.txt に依存関係を明示してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあれば `pip install -r requirements.txt`）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（config.py がプロジェクトルートを .git または pyproject.toml で探索します）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須の環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の引数に渡すことも可）

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi

例: .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（クイックスタート）

以下は主要 API を簡単に利用する例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の生成
```python
import duckdb
from kabusys.config import settings

# ファイル DB を使う場合:
conn = duckdb.connect(str(settings.duckdb_path))

# インメモリ DB:
# conn = duckdb.connect(":memory:")
```

- 日次 ETL 実行（J-Quants からデータを取得して保存 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に置くか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査用の DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト: [{"date":..., "code":..., "mom_1m": ..., ...}, ...]
```

注意:
- score_news / score_regime は OpenAI を呼び出すため API キーが必須（api_key 引数か OPENAI_API_KEY 環境変数）。
- ETL / 外部 API 呼び出しはネットワークや API レートに依存します。ログや例外を確認してください。

---

## よく使う関数一覧（参照用）

- ETL / Data
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
  - data.jquants_client.fetch_daily_quotes(...)
  - data.jquants_client.save_daily_quotes(...)
  - data.calendar_management.is_trading_day(...)
  - data.calendar_management.calendar_update_job(...)

- AI
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Research
  - research.factor_research.calc_momentum(...)
  - research.factor_research.calc_volatility(...)
  - research.factor_research.calc_value(...)
  - research.feature_exploration.calc_forward_returns(...)

- Audit
  - data.audit.init_audit_schema(conn)
  - data.audit.init_audit_db(path)

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義、version
  - config.py — 環境変数 / .env 自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメントスコアリング（score_news）
    - regime_detector.py — マクロ + ETF MA を用いた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/認証/保存ロジック）
    - pipeline.py — ETL パイプラインと ETLResult
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
    - news_collector.py — RSS 取得・前処理・保存ロジック
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — 汎用統計（zscore_normalize）
    - audit.py — 監査ログスキーマと初期化関数
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value のファクター計算
    - feature_exploration.py — 将来リターン / IC / summary / rank
  - research/...（その他の研究ユーティリティ）
  - その他: strategy, execution, monitoring（パッケージ内で __all__ に含まれているが該当コードはプロジェクト内の別モジュールで実装される想定）

---

## 設計上の注意点 / 運用上のヒント

- 環境変数は .env / .env.local から自動ロードされます。OS 環境変数は .env の上位優先で保護されます。テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- OpenAI 呼び出しはリトライ・バックオフ・JSON バリデーションが組み込まれていますが、コストやレート制限に注意してください。batch サイズやチャンク設定はモジュール定数で調整可能です。
- DuckDB のスキーマや監査テーブルは init_audit_schema / init_audit_db で初期化してください。監査ログは削除しない前提で設計されています。
- ETL は差分更新かつバックフィル（後出し修正吸収）を行います。run_daily_etl の backfill_days を運用要件に合わせて調整してください。
- news_collector は SSRF や XML Bomb 等のリスク低減措置を実装しています。外部 RSS ソースを追加する場合は URL の妥当性を確認してください。

---

必要であれば、README に「開発ルール」「テスト実行方法」「CI 設定」「デプロイ手順」等のセクションを追加できます。どの情報を追加したいか教えてください。