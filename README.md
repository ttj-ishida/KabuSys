# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（LLMベース）、ファクター計算、マーケットカレンダー管理、監査ログ（発注→約定トレース）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の用途を想定した Python モジュール群です。

- J-Quants API からの株価・財務・上場情報・マーケットカレンダー取得（ETL）
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）および市場レジーム判定
- 研究用のファクター計算・特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）向けのスキーマ初期化ユーティリティ

設計上の特徴:
- Look-ahead bias を避けるため日付参照を明示的に行う（date.today() 等に依存しない実装）
- DuckDB を主要な分析DBとして利用
- 冪等性・リトライ・レート制御等の実運用に耐える実装
- OpenAI への呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）となる

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch_* / save_*）
- ニュース
  - RSS フィード取得（SSRF 対策、gzip 制御、トラッキング削除）
  - preprocess_text、記事ID生成（SHA-256）など
- NLP（LLM）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - score_regime: ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成し market_regime に書き込み
- リサーチ / ファクター
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants から差分取得）
- 品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（DuckDB に監査用テーブルを初期化）

---

## 必要条件（主な依存）

- Python >= 3.10（コード中の型表記に | 演算子等を使用）
- duckdb
- openai (OpenAI の最新 SDK を想定)
- defusedxml

お使いのプロジェクトでは適宜 requirements.txt や pyproject.toml を用意してください。参考（例）:

requirements.txt の例:
- duckdb
- openai
- defusedxml

インストール例:
```
python -m pip install -r requirements.txt
# または 開発時
python -m pip install -e .
```

---

## 環境変数 / 設定

自動的にプロジェクトルート（.git または pyproject.toml を持つディレクトリ）から `.env` / `.env.local` を読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を組み込む場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID

任意・デフォルトあり:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite path（デフォルト: data/monitoring.db）

OpenAI:
- OPENAI_API_KEY: score_news / score_regime で使用。関数呼び出し時に引数で渡すことも可能。

`.env` の簡易テンプレート（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパース挙動:
- export KEY=val 形式を許容
- シングル/ダブルクォートのエスケープを考慮
- inline コメントの扱い（クォートなしで # の直前にスペースがある場合はコメントとみなす）
- .env.local は .env を上書きする

---

## セットアップ手順（概略）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - python -m pip install -r requirements.txt
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB 用ディレクトリを作成（例: data/）
6. 必要に応じて監査DBを初期化（下記参照）

---

## 使い方（基本例）

以下は Python REPL / スクリプト内からの簡単な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- DuckDB 接続の作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次バッチ）を実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または引数で指定）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB の初期化（独立した監査用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は内部で実行済み
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

ログや例外:
- 各処理はロギングを行います。実行環境の LOG_LEVEL を変更してデバッグ情報を得られます。
- OpenAI や外部 API 呼び出しで失敗した場合、フェイルセーフで継続する設計（スコア0やスキップ）ですが、DB 書込失敗などは例外が伝播します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（ai_scores）処理、OpenAI バッチ呼び出し、検証
    - regime_detector.py   — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアントと DuckDB 保存ロジック
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポートインターフェース
    - news_collector.py    — RSS 取得・前処理・保存ロジック
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py           — データ品質チェック
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログ（監査テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai, data, research パッケージの公開 API は各 __init__.py で整備されています

---

## 実運用上の注意点

- OpenAI と J-Quants の API キー/トークンは適切に管理してください。テスト環境では低コストなモードやモックを使うことを推奨します。
- score_news / score_regime は外部 LLM を利用します。API 料金・レート・レスポンス形式の変化に注意してください（本実装は JSON mode を期待）。
- DuckDB に対して executemany で空のパラメータを渡すとエラーになるケースがあるため、実装側で保護されています。直接 SQL を実行する場合は注意してください。
- calendar / ETL 周りは market_calendar の有無で挙動が変わる（DB がない場合は曜日ベースのフォールバック）点に留意してください。
- 監査スキーマの初期化は transactional オプションがありますが、DuckDB のトランザクション制約（ネスト不可）に注意してください。

---

## テスト・開発

- 各 OpenAI 呼び出しは内部的にラッパー関数（_call_openai_api）を用いており、テスト時には unittest.mock.patch で差し替え可能です。
- news_collector の外部ネットワーク呼び出しもモック可能です（_urlopen の差し替えなど）。
- ETL や品質チェックは DuckDB のインメモリ接続（":memory:"）で単体テストできます。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細な API 使用法・パラメータや実運用手順（CI/CD、監視、ロールアウト）は別途運用ドキュメントにまとめることを推奨します。