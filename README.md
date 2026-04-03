# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群（KabuSys）。データの取得・ETL、品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検知）
  - 必須環境変数の明示的エラー

- データETL（J-Quants）
  - J-Quants API から株価（日次OHLCV）、財務、上場・カレンダー情報を差分取得
  - ページネーション・レート制御・リトライ実装
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質管理
  - 欠損検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで問題点を集約

- マーケットカレンダー管理
  - JPX カレンダーの差分取得 / 保存
  - 営業日判定、前後営業日取得、期間内営業日リスト取得 等

- ニュース収集（RSS）
  - RSS フィード取得、前処理、SSRF/プライベートIP対策、トラッキングパラメータ除去
  - raw_news / news_symbols へ冪等保存（設計に基づいた保存処理）

- ニュースNLP（OpenAI）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント評価（score_news）
  - LLM 呼び出しのリトライ・レスポンス検証・スコアクリッピング

- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュースセンチメントを合成してレジーム判定（bull/neutral/bear）
  - OpenAI 呼び出し・フェイルセーフを含む（score_regime）

- 研究用モジュール（Research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（Audit）
  - signal → order_request → executions をトレースする監査テーブル定義・初期化機能（init_audit_schema / init_audit_db）
  - 全 TIMESTAMP は UTC、冪等性・インデックスあり

---

## 前提条件（推奨環境）

- Python 3.10+
  - （| 型注釈や typing の記法を利用しているため Python 3.10 以上を想定）
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加は pyproject/requirements に従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml や requirements.txt があればそれを利用してください）
   - 開発インストール（パッケージとして利用する場合）
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` が自動読み込みされます（デフォルト）。
   - 自動読み込みを無効化する： KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必要な変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーションAPI用のパスワード（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 等）
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH
     - KABUSYS_ENV（development | paper_trading | live）
     - LOG_LEVEL（DEBUG|INFO|...）
   - 例（.env）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な利用例）

以下はライブラリの代表的な利用例です。詳細は各モジュールの docstring を参照してください。

1) 設定と DB 接続
```python
from kabusys.config import settings
import duckdb

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

2) 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコア（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 設定: OPENAI_API_KEY を環境変数でセットするか、api_key 引数を渡す
num_written = score_news(conn, target_date=date(2026,3,20))
print(f"score_news wrote {num_written} codes")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

5) 監査DB 初期化（監査ログ用独立 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルに書き込める
```

6) ニュース RSS 取得（事前処理のみ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 取得した記事は raw_news に保存するロジック（モジュール内の保存関数）を使って保存できます。
```

7) ファクター計算（研究用途）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に必要）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite DB パス（data/monitoring.db）
- KABUSYS_ENV — 動作モード（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

設定は .env / .env.local から自動的に読み込まれます（ただしプロジェクトルートが検出できない場合はスキップ）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - news_collector.py      — RSS ニュース収集・前処理
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - monitoring/ (実装想定) — 監視・実行制御（pid/killflag 等）※モジュール群の一部が参照
  - execution/, strategy/ 等（プロジェクト全体設計に沿った別モジュールが存在想定）

※ 上記はリポジトリ内の主要モジュール構成を抜粋したものです。

---

## 開発・テスト・デバッグ

- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを抑制できます（テストや CI で有用）。
- OpenAI 呼び出し部分や外部ネットワークリクエストはテスト時にモック可能な設計（内部関数を patch して差し替えられる）。
- DuckDB を使った関数は ":memory:" によるインメモリ DB を使ってユニットテストしやすくなっています。

---

## 貢献・コードスタイル

- コード内に設計方針や注意事項が詳細に記載されています。新機能追加や修正を行う場合は docstring に従い Look-ahead bias 等の金融特有の注意点を順守してください。
- PR の際は関連する単体テスト・統合テストを追加してください。

---

## ライセンス

- リポジトリにライセンスファイルがない場合、使用条件はプロジェクト管理者に確認してください。

---

README は主要な利用方法と内部設計を要約したものです。各モジュールの docstring を参照すると詳しい挙動・設計意図・エラーハンドリング方針が記載されています。必要であれば特定モジュールの使い方サンプルや API リファレンスを別途作成します。