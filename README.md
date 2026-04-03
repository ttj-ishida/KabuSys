# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants からの時系列データ取り込み（ETL）、ニュースの収集と LLM ベースのニュースセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（注文→約定のトレーサビリティ）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の要素を持つ内部ライブラリ（ライブラリ形式でインポートして使用）です。

- データ取得・ETL（J-Quants API 経由、DuckDB 保存）
- ニュース収集（RSS）と NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算 / 研究ユーティリティ（モメンタム、バリュー、ボラティリティ、IC 等）
- マーケットカレンダー管理（JPX カレンダー）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定読み込み（.env / 環境変数）

設計方針として、バックテストでのルックアヘッドバイアスを避けるため日付操作やデータ取得に注意した実装になっています。また、API 呼び出しのリトライ・レート制御、各種フォールバックやフェイルセーフ（API 失敗時のゼロフォールバック等）を備えています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（DuckDB に差分保存）
  - J-Quants API クライアント（認証トークン自動リフレッシュ・レート制御・リトライ）
- データ品質
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
- ニュース & NLP
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 を組合せた市場レジーム判定（score_regime）
- 研究（research）
  - モメンタム / バリュー / ボラティリティ計算
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリ
  - zscore 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを初期化・管理
  - init_audit_db / init_audit_schema（冪等）
- コンフィグ管理
  - .env 自動読み込み（プロジェクトルート判定、.env.local を優先する）
  - 必須環境変数に対するヘルパ（settings オブジェクト）

---

## セットアップ手順

前提: Python 3.10+（typing | None の表記などを使用）を推奨。

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 代表的な依存例（プロジェクトで使うパッケージ）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject があればそちらを利用してください）

3. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   推奨の主要環境変数（最低限必要になるケース）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行で必須）
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（score_news / score_regime 等）
   - KABU_API_PASSWORD: kabu ステーション API を使う場合
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   データベース配置のデフォルト:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db

   例: .env
   - JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   - OPENAI_API_KEY="sk-xxxx..."
   - DUCKDB_PATH="data/kabusys.duckdb"
   - LOG_LEVEL=DEBUG

4. データディレクトリの作成（必要なら）
   - mkdir -p data

---

## 使い方（代表的な例）

Python スクリプト / REPL から直接関数を呼び出して利用します。以下は代表的なサンプル。

- ETL を実行（DuckDB 接続を作って実行）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込件数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 等を使う、OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブルが初期化される。
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

- 設定値取得（settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)
```

注意点:
- OpenAI を使う関数は api_key 引数を受け取ります。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存関数は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が前提です。初期スキーマ化処理を行うコード／DDL が必要な場合は既存のスキーマ初期化関数を利用してください（本リポジトリにスキーマ管理用のユーティリティがある想定）。

---

## 設定（.env）ローディングの挙動

- 自動読み込み対象ファイル: プロジェクトルート（.git または pyproject.toml があるディレクトリを探索）にある `.env` および `.env.local`
  - 読み込み優先: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` の値を上書きします
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- .env のパーサはシェルスタイル（export KEY=val, 引用符・エスケープ、# コメント扱い）に対応
- Settings クラス（kabusys.config.settings）を通じてアプリ設定にアクセスできます（必須項目が未設定だと ValueError を投げます）

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要モジュールと役割の一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news: 銘柄別ニュースセンチメントを ai_scores に書込
    - regime_detector.py
      - score_regime: ETF MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存関数）
    - pipeline.py
      - ETL（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策等）
    - calendar_management.py
      - market_calendar 管理・営業日判定・calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査テーブル DDL / 初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

（上記は主要なファイルを抜粋しています。細かいユーティリティや追加モジュールは同階層にあります。）

---

## セキュリティ・設計上の注記

- news_collector.fetch_rss は SSRF 対策（リダイレクト検査、プライベートIP 拒否）、受信サイズ制限、defusedxml による XML パース保護を行います。
- J-Quants クライアントはレート制御（120 req/min）とリトライ、401 時のトークン自動リフレッシュを備えています。
- OpenAI 呼び出しはリトライ、JSON レスポンスの厳密検証（JSON mode を想定）を行い、失敗時はフェイルセーフ（スコア 0.0）で継続するよう設計されています。
- データの書き込みは冪等（ON CONFLICT / DO UPDATE）を基本とし、部分失敗時に既存データを保護する工夫がなされています。

---

## 開発 / テスト

- 自動ロードをテストで無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用
- OpenAI 呼び出しなど外部 API は unittest.mock 等で _call_openai_api / _urlopen を差し替えてテスト可能
- DuckDB はインメモリ(":memory:") 接続でユニットテストを行えます（init_audit_db も :memory: をサポート）

---

## ライセンス / 貢献

この README はコードベースからのドキュメント生成物です。実際のリポジトリに LICENSE や貢献ガイドがある場合はそちらに従ってください。

---

何か以下の点で追加の情報が必要であれば教えてください:
- 実行可能なサンプルスクリプト（ETL ジョブやニュース収集ジョブのエントリポイント）
- .env.example の具体的なテンプレート
- DuckDB スキーマ（DDL）の完全一覧