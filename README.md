# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ

- バージョン: 0.1.0
- パッケージ: `kabusys`

この README はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（注文→約定のトレーサビリティ）、および市場レジーム判定などを目的としたモジュール群を提供する Python ライブラリです。

設計上のポイント：
- DuckDB をデータストアとして利用
- J‑Quants API からの差分取得・ページネーション対応・レート制御・リトライ実装
- ニュースの前処理・SSRF 対策・OpenAI（gpt-4o-mini）を用いた NLP（JSON Mode）でのスコアリング
- バックテストにおけるルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない等）
- ETL / 品質チェックはフェイルセーフ設計（個別ステップの失敗で全体が停止しない）

---

## 主な機能一覧

- 環境設定管理（`.env` 自動読み込み、必須環境変数チェック）
- J‑Quants クライアント
  - 日次株価（OHLCV）取得・保存
  - 財務データ取得・保存
  - 市場カレンダー取得・保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - `run_daily_etl` による日次一括処理
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント -> `ai_scores` 書込）
  - `score_news(conn, target_date, api_key=None)`
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメント合成）
  - `score_regime(conn, target_date, api_key=None)`
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions テーブルの初期化・管理）
  - `init_audit_db(path)` / `init_audit_schema(conn)`

---

## 必須環境変数

主に以下が使用されます（`.env` に設定しておくことを推奨）：

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: `INFO`）

設定の自動読み込み：
- プロジェクトルート（`.git` または `pyproject.toml` を基準）に `.env` / `.env.local` がある場合、`kabusys.config` が自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の例（必要に応じて追記してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_api_key
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

前提: Python 3.9+ を想定（実装は typing の新仕様を一部使用しています）。

1. リポジトリをクローン／取得

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   - 例（プロジェクトルートに requirements.txt があればそれを使う）:
     ```
     pip install -r requirements.txt
     ```
   - 最低限必要なパッケージ（参考）:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージを編集可能インストール:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - `.env` / `.env.local` をプロジェクトルートに作成（上の必須環境変数を設定）

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は主要な API の使用例です。すべての操作は DuckDB 接続（`duckdb.connect(...)`）を渡して呼び出します。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニュースのセンチメントをスコア化し `ai_scores` に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 ベース）を実行する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化する（監査テーブルを作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って audit 用テーブルが存在することを確認できます
```

- 研究用ファクター計算の一例（モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

注意点:
- OpenAI 呼び出しや外部 API はネットワーク依存かつ料金が発生するため、本番／テスト環境での取り扱いに注意してください。
- 各関数はルックアヘッドバイアスを避ける設計（内部で現在時刻を参照しない等）です。バックテスト用途には特に配慮されています。

---

## よく使うモジュール / 関数（抜粋）

- kabusys.config.settings — 環境設定アクセス（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.data.news_collector
  - fetch_rss(url, source)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_db(path)
  - init_audit_schema(conn)

---

## ディレクトリ構成

主要なファイル・モジュールの構成（抜粋）:

- src/
  - kabusys/
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
      - quality.py
      - stats.py
      - audit.py
      - news_collector.py
      - calendar_management.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他研究ユーティリティ)
    - ai/
      - news_nlp.py
      - regime_detector.py
    - research/
      - factor_research.py
      - feature_exploration.py

（注）上記は主要ファイルの抜粋です。実際のリポジトリにはさらに補助モジュールやテスト等が含まれる可能性があります。

---

## テスト・開発メモ

- 外部 API 呼び出し部分は差し替え可能に設計されています（例: `kabusys.ai.news_nlp._call_openai_api` や `kabusys.data.news_collector._urlopen` をモックする）。
- 環境変数自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を探索して `.env` / `.env.local` を読み込みます。ユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

## ライセンス・貢献

この README はコードベースから推測した利用方法と設計意図をまとめたものです。実際のライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---

ご要望があれば、README に CI 実行手順、より具体的なサンプルスクリプト、.env.example の完全テンプレート、または各モジュールの API リファレンス（関数引数と戻り値の詳細）を追加します。どれを優先しますか？