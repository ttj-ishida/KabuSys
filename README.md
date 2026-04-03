# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / RSS / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ（トレーサビリティ）を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API を用いた株価・財務・市場カレンダーなどの差分取得（ETL）
- DuckDB を使ったデータ保存・クエリ基盤
- ニュース記事収集と OpenAI によるニュースセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- ファクター（モメンタム／ボラティリティ／バリュー）計算と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- kabuステーション（取引実行レイヤ）やモニタリング等の接続点（インターフェース提供）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() 等を不用意に参照しない）
- DuckDB による局所 DB（ファイルまたはメモリ）で高速に集計可能
- API 呼び出しに対するリトライ・レート制御・フェイルセーフ処理を考慮

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 収集・前処理・DB 保存）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースNLP（score_news: 銘柄別センチメント取得 → ai_scores テーブルへ保存）
  - 市場レジーム判定（score_regime: MA200 乖離とマクロニュース LLMを合成）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理（kabusys.config: .env 自動ロード、Settings クラス）
- 監視・実行・戦略モジュール等（パッケージの public API を経由して連携可能）

---

## 動作要件

- Python 3.10 以上（タイプヒントに `X | None` などの構文を使用）
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース等）

実際の導入では requirements.txt を用意して `pip install -r requirements.txt` してください。最低限の依存例：

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリを取得
   - git clone するか、プロジェクトソースを配置します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（autoload はデフォルト有効）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY : OpenAI の API キー（score_news / score_regime 実行時に必要）
   - KABU_API_BASE_URL : kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite のパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : environment (development / paper_trading / live)（デフォルト development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/...、デフォルト INFO）

   任意の設定は `kabusys.config.Settings` からプロパティとしてアクセスできます。

---

## 使い方（よく使う API / コマンド例）

以下は Python インタプリタやスクリプトから利用する例です。DuckDB 接続は `duckdb.connect(path)` で取得して渡します。

- 日次 ETL の実行（データ収集 → 品質チェック）

```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）スコアリング

```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} codes")
```

- 市場レジーム判定

```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB を作る）

```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルへ書き込みが可能
```

- 市場カレンダー判定 / 取得ヘルパー

```py
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点：
- OpenAI を使う関数は api_key を引数で明示的に渡せます（環境変数 OPENAI_API_KEY が未設定だと ValueError が出ます）。
- ETL は内部で J-Quants API の認証に `JQUANTS_REFRESH_TOKEN` を使います。
- DuckDB に対する大きな書き込みはトランザクションで保護されていますが、外部接続やスキーマ変更時は注意してください。

---

## 環境変数（要約）

自動読み込み対象はプロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます。上書きルールや保護キーなどの詳細は `kabusys.config` を参照してください。

主なキー（例）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (score_news / regime_detector 用)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化（バージョン等）
- config.py — 環境変数と Settings クラス、.env 自動読み込み
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLU / スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS 取得・前処理・保存
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ初期化・DB 作成
- research/
  - __init__.py
  - factor_research.py — モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py — forward returns / IC / summary 等
- ai, research, data の下にさらに補助モジュールが存在します。

---

## 開発・テスト時の注意

- .env 自動ロードは便利ですが、ユニットテストなどでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に環境を制御すると安定します。
- OpenAI / J-Quants の外部通信をテストで行う際は、モック（unittest.mock）を利用して API 呼び出し関数を差し替えてください。コード内でもテストしやすいように `_call_openai_api` の差し替えを想定しています。
- DuckDB のバージョン差による `executemany` の挙動などに注意（pipeline/news_nlp などで互換性対策済みの箇所あり）。

---

## 貢献・ライセンス

本 README はコードベースの概要説明です。実運用に投入する場合は十分な安全性・試験・モニタリングを実施してください。ライセンス・コントリビュート方法はプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（無ければ管理者に問い合わせてください）。

---

必要であれば、README にサンプル .env.example、requirements.txt、簡単な CLI スクリプト例（ETL を定期実行する systemd / cron の例）、および典型的なワークフロー（ETL → 品質チェック → ニューススコア → ファクター計算 → シグナル生成 → 発注）を追加できます。希望があれば追記します。