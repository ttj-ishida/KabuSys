# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォーム兼リサーチ／実行基盤のライブラリ群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、JPX カレンダー）
- DuckDB を使ったローカルデータベース保存（冪等保存）
- ニュースの収集・前処理・LLM を使ったセンチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- kabuステーション・Slack 等との統合に必要な設定管理

設計上、バックテストやルックアヘッドバイアス防止に配慮した日付取り扱いがなされています（datetime.today()/date.today() を直接参照しない箇所等）。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（rate limiting、リトライ、トークン自動リフレッシュ）
  - news_collector（RSS 収集、前処理、SSRF 対策、圧縮対応）
  - market calendar 管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - data quality checks（欠損・スパイク・重複・日付不整合）
  - audit（監査ログテーブルの初期化・DB 作成ヘルパー）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news(): 銘柄ごとのニュースセンチメントを生成して ai_scores テーブルへ保存
  - regime_detector.score_regime(): ETF（1321）200日MA乖離 + マクロニュースで market_regime を判定
  - OpenAI 呼び出しはリトライや JSON モードを使用する設計（gpt-4o-mini を想定）
- research/
  - factor 計算（momentum, value, volatility）
  - feature exploration（forward returns, IC, factor summary, rank）
- config.py
  - 環境変数の読み込み（.env, .env.local 自動読み込み、無効化フラグあり）
  - settings オブジェクト経由で各種設定を取得

---

## 必要な環境変数

以下は主要な設定です。プロジェクトルートの `.env.example` を基に `.env` を作成してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動で .env を読み込む仕組みがあり、優先順位は OS 環境変数 > .env.local > .env です。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 例（pip）:
     - pip install duckdb openai defusedxml
     - あるいはプロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。
4. .env を用意
   - プロジェクトルートに .env（または .env.local）を作成し、上記の環境変数を設定してください。
5. （オプション）開発インストール
   - pip install -e .

推奨パッケージ（最低限）:
- duckdb
- openai
- defusedxml

その他、標準ライブラリの urllib 等を使用します。

---

## 使い方（例）

以下は主要な API の使い方サンプルです。実行は Python スクリプト / REPL で行ってください。

- DuckDB 接続の準備例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（J-Quants からの差分取得・保存・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に保存（score_news）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 環境変数 OPENAI_API_KEY が設定されていれば api_key 引数は不要
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {written}")
```

- 市場レジームを判定して market_regime に保存（score_regime）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化する（audit テーブル作成）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査ログを記録できます
```

- 市場カレンダーの更新ジョブを手動で実行:

```python
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)
```

注意:
- OpenAI を呼ぶ機能は API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。
- J-Quants は JQUANTS_REFRESH_TOKEN を必要とします（config.settings.jquants_refresh_token で参照）。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージ初期化。公開サブパッケージを定義。
- config.py
  - 環境変数・設定管理（.env 自動読み込み、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの集約、OpenAI でのセンチメント評価、ai_scores への書き込み
  - regime_detector.py
    - ETF(1321)のMA乖離とマクロニュースを合成して market_regime を判定
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（fetch_*、save_*、認証、レート制御、リトライ）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 収集、前処理、SSRF/サイズ/圧縮対策
  - calendar_management.py
    - 市場カレンダー管理、営業日判定、calendar_update_job
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize などの統計ユーティリティ
  - audit.py
    - 監査ログスキーマの初期化・インデックス定義・監査 DB 初期化
- research/
  - __init__.py
  - factor_research.py
    - momentum/value/volatility 等のファクター計算（prices_daily/raw_financials 参照）
  - feature_exploration.py
    - forward returns, IC, factor_summary, rank
- research パッケージはリサーチ用途の関数群を提供

その他:
- data/ 内のテーブル名（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, news_symbols 等）を想定して動作します。ETL を実行してテーブルを作成・充填してください。

---

## 開発・テスト時の注意点

- .env 自動読み込みは config.py で行われます。テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しは各モジュール内でモック可能な設計になっています（内部の _call_openai_api や _urlopen 等を unittest.mock.patch で差し替えられます）。
- DuckDB の executemany に空のリストを渡すと問題になる箇所（DuckDB 0.10 互換性）を考慮した実装があります。テスト用 DB として ":memory:" を利用できます。
- 監査ログ初期化は UTC タイムゾーンに固定されます（SET TimeZone='UTC'）。

---

## ライセンス・貢献

（ここにプロジェクトのライセンス・貢献方法・連絡先などを追記してください）

---

README は以上です。README の追加項目（インストールコマンド、CI 手順、具体的な .env.example のテンプレート、詳しい API リファレンスなど）が必要であれば、該当する情報を教えてください。