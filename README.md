# KabuSys

日本株自動売買プラットフォームのライブラリ/ユーティリティ群です。  
本リポジトリはデータ収集（J-Quants）、データ品質チェック、ファクター計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（約定トレーサビリティ）など、アルゴリズム取引基盤のコア機能を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買/リサーチ基盤を想定したモジュール群です。主な目的は以下です。

- J-Quants API からの差分ETL（株価、財務、マーケットカレンダー）
- raw データに対する品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集・NLP による銘柄ごとのセンチメント算出（OpenAI）
- 日次の市場レジーム判定（MA とマクロニュースの合成）
- リサーチ用ファクター計算・特徴量解析ツール
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ

設計上、バックテストでのルックアヘッドバイアス防止や API のレート制御、フェイルセーフ（API失敗時のフォールバック）に配慮しています。

---

## 機能一覧

- 環境設定管理（.env 自動ロード / Settings クラス）
- J-Quants API クライアント
  - fetch / save: 日足（OHLCV）、財務、上場銘柄情報、マーケットカレンダー
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（run_daily_etl 等）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュースNLP（OpenAI）による銘柄別スコアリング（score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）（score_regime）
- 研究用ファクター計算（momentum / volatility / value）および前方リターン / IC / 統計サマリー
- 監査ログ初期化（監査用テーブル・インデックスを DuckDB に作成、init_audit_db）

---

## 要件（主要）

- Python 3.10+
- 必要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- （実行に必要な外部サービス）
  - J-Quants API アクセス（JQUANTS_REFRESH_TOKEN）
  - OpenAI API（OPENAI_API_KEY）※ニュースNLP / レジーム判定に使用

※依存パッケージはプロジェクトの配布形態に応じて requirements.txt や pyproject.toml に記載してください。最低限、上記パッケージが必要になります。

---

## セットアップ手順

1. Python 環境を用意（3.10 以上推奨）
2. リポジトリをクローン / ダウンロードし、プロジェクトルートへ移動
3. 依存パッケージをインストール
   - 例（pip）:
     pip install duckdb openai defusedxml
   - または:
     pip install -e .  (パッケージ化されている場合)
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 自動読み込み: モジュール import 時にプロジェクトルートの `.env` と `.env.local` を参照します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使うなら必須）
   - 任意 / デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視関連

例 .env.example（プロジェクトルートに .env として保存）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=your_openai_api_key
KABUSYS_ENV=development
LOG_LEVEL=INFO

> 注意: リポジトリは自動的にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env を読み込みます。テスト等で自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

下記は Python REPL やスクリプトから呼び出す最小の例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）が設定されていることを確認してください。

- DuckDB 接続を作成し、ETL を日次実行（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルト DB パスは settings.duckdb_path ですが任意で指定可能
conn = duckdb.connect("data/kabusys.duckdb")

# target_date を指定しなければ今日が対象（内部で営業日に調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（score_news）を呼ぶ例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
print(f"scored {n_written} codes")
```

- 市場レジーム判定（score_regime）を呼ぶ例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査テーブル設定）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後、conn を使って監査ログを書き込み可能
```

- market calendar / trading day ヘルパーの利用:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

--- 

## 主要モジュールと API の概要

- kabusys.config
  - settings: 各種設定・環境変数取得ラッパー（例: settings.jquants_refresh_token）
  - 自動でプロジェクトルートの .env / .env.local を読み込む（例外的に無効化可）

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL ジョブ）
  - ETLResult クラス（実行結果の集約）

- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - QualityIssue データクラス

- kabusys.data.news_collector
  - fetch_rss / preprocessing utilities（SSRF対策、URL正規化、記事ID生成）

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize

- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログテーブル・インデックスの作成）

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY (ニュースNLP / レジーム判定時に必要)
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, etc. — 実行監視用

設定はプロジェクトルートの `.env` / `.env.local` に置くか、OS 環境変数で与えます。`.env.local` は `.env` より優先して上書きされます。

---

## 運用上の注意点

- OpenAI / J-Quants 呼び出しは外部 API のため、料金・レート制限・キー管理に注意してください。
- news_nlp / regime_detector は API エラー時にフォールバックする設計ですが、スコアの欠落が発生します。監視ログや品質チェックと組み合わせて運用してください。
- DuckDB に対する executemany の空リスト渡しなど、バージョン依存の注意が各所にあります（pipeline モジュール内にも条件分岐あり）。DuckDB のバージョン相互互換性を考慮してください。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで有用）。

---

## ディレクトリ構成

以下は主要なファイル / モジュールの構成（src/kabusys 内）です。詳細は各モジュールの docstring を参照してください。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースNLP（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント & 保存関数
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - quality.py          — データ品質チェック
    - news_collector.py   — RSS ニュース収集・前処理
    - calendar_management.py — マーケットカレンダー管理・営業日ユーティリティ
    - audit.py            — 監査ログ（トレーサビリティ）スキーマ初期化
    - etl.py              — ETLResult 再エクスポート
    - stats.py            — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー、rank 等

---

## 開発・テスト

- テストはこのドキュメントに含まれていませんが、モジュールは外部依存（ネットワーク・API）を持つため、ユニットテストでは OpenAI / HTTP / jquants_client の呼び出しをモックすることを推奨します。
- config モジュールは自動で .env を読み込むため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するか、モジュールの関数をモックしてください。
- news_nlp や regime_detector では _call_openai_api をモックする設計になっています（unittest.mock.patch で差し替え可能）。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を記載してください — 本テンプレートには含まれていません）

---

以上。README の不足点や、特定の実行例（CI セットアップ、Dockerfile、requirements.txt 追加など）を希望する場合は教えてください。必要に応じて例を追記します。