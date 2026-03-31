# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォーム・研究・自動売買のためのライブラリ群です。J-Quants API を中心とした ETL、ニュース収集・NLP（OpenAI）によるセンチメント分析、ファクター計算や市場レジーム判定、監査ログ（トレーサビリティ）などを含みます。

この README ではプロジェクト概要、主な機能、セットアップ方法、簡単な使い方、ディレクトリ構成を日本語でまとめています。

---

目次
- プロジェクト概要
- 機能一覧
- 環境変数（主要な設定項目）
- セットアップ手順
- 使い方（簡単なコード例）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニュース NLP スコアリング
  - 市場レジーム判定
  - 監査DB 初期化
- 自動 .env 読み込みについて
- ディレクトリ構成（主要ファイルの説明）
- ライセンス・注意事項

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API からのデータ取得（株価／財務／マーケットカレンダー）
- DuckDB を用いたデータ保存・品質チェック（ETL パイプライン）
- RSS ニュース収集と前処理（SSRF 回避等の安全対策を含む）
- OpenAI を使ったニュースセンチメント分析（銘柄別）と市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（シグナル→発注→約定）用スキーマの初期化と操作ユーティリティ

設計方針として、ルックアヘッドバイアス回避（過去データのみ参照）、冪等性（ON CONFLICT 等）、外部 API の堅牢なリトライやフェイルセーフを重視しています。

---

## 機能一覧

主要な機能（モジュール）:

- kabusys.config
  - 環境変数の読み取り・自動ロード（.env / .env.local）
  - settings オブジェクトでアプリ設定にアクセス

- kabusys.data
  - jquants_client: J-Quants API 呼び出し／保存ユーティリティ（レート制限・リトライ・認証リフレッシュ対応）
  - pipeline / etl: 差分ETL 実行（prices, financials, calendar）と ETLResult
  - news_collector: RSS 収集、前処理、raw_news への保存ロジック（SSRF対策、安全な XML パース）
  - calendar_management: JPX カレンダーの管理（営業日判定、next/prev）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: zscore 正規化ユーティリティ
  - audit: 監査ログテーブル定義・初期化（signal_events, order_requests, executions）

- kabusys.ai
  - news_nlp.score_news: OpenAI を用いた銘柄別ニュースセンチメント計算 → ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースの LLM センチメントを合成して market_regime を作成

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 環境変数（主要）

以下は主要な環境変数です。必須のものは README 内で明記します。

必須（実行に必要な場合）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API を使用する機能（news_nlp, regime_detector）で使用（関数は api_key 引数で上書き可能）
- SLACK_BOT_TOKEN: Slack 連携がある場合
- SLACK_CHANNEL_ID: Slack 連携対象チャンネル
- KABU_API_PASSWORD: kabuステーション API 用パスワード（売買実行モジュール使用時）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）

注意:
- .env.example を参考に .env を作成してください。
- 自動 .env 読み込みはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順

1. Python 3.9+（typing の Union | などを使用）を準備

2. 仮想環境の作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール（例）
必要な依存はプロジェクトに合わせて変わりますが、少なくとも以下が必要です:
- duckdb
- openai
- defusedxml

例:
```bash
pip install duckdb openai defusedxml
```

プロジェクトに setup.py / pyproject.toml がある場合はソースを編集可能インストール:
```bash
pip install -e .
```

4. 環境変数を設定
プロジェクトルートに .env ファイルを作成するか、シェルで直接 export / set してください。
例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB の初期スキーマ（必要に応じて）を作成します（監査用 schema の初期化は下記参照）。

---

## 使い方 - 簡単なコード例

以下は代表的な利用例です。各関数は duckdb の接続オブジェクト（kabusys では DuckDBPyConnection）を引数に取ります。

準備: DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

# ファイルベース DB の例:
conn = duckdb.connect(str(settings.duckdb_path))

# インメモリ DB:
# conn = duckdb.connect(":memory:")
```

1) 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日を基準に実行
print(result.to_dict())
```

2) ニュース NLP（ai スコア算出）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 明示的に API キーを渡すことも可能
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査DB 初期化（監査ログ専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn 上で追加の操作やクエリが可能
```

5) 研究用ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

注意:
- OpenAI を使う機能は api_key を引数で上書き可能。引数を None にすると環境変数 OPENAI_API_KEY を参照します。
- ほとんどの関数はデータの存在（prices_daily, raw_news, raw_financials 等）を前提とするため、事前に ETL を実行してデータを投入してください。

---

## 自動 .env 読み込みについて

- kabusys.config モジュールはパッケージのインポート時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のキーのみ）
- 自動読み込みを無効化するには環境変数を設定:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## ディレクトリ構成（主要ファイルの説明）

プロジェクトの主要なソース配置（src/kabusys 以下）:

- __init__.py
  - __version__ = "0.1.0"
  - パッケージの公開 API を定義

- config.py
  - 環境変数 / .env 読み込みと Settings クラス（settings オブジェクト）

- ai/
  - news_nlp.py : ニュースの銘柄別センチメント算出と ai_scores への保存（OpenAI 使用）
  - regime_detector.py : ETF ma200 乖離とマクロニュース LLM を合成した市場レジーム判定

- data/
  - jquants_client.py : J-Quants API クライアント（フェッチ・保存関数含む）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py : ETLResult の再エクスポートインターフェース
  - news_collector.py : RSS 収集、記事前処理、安全対策
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - quality.py : データ品質チェック（欠損・スパイク等）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログテーブル DDL と初期化関数

- research/
  - factor_research.py : モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

上記以外にも strategy / execution / monitoring 等を public API として想定しています（__all__ に定義あり）。

---

## ライセンス・注意事項

- 本 README はコードベースの抜粋に基づく簡易ドキュメントです。実運用前に以下に注意してください:
  - OpenAI や J-Quants API の利用は各サービスの利用規約に従ってください。
  - 実際の売買を行う場合は十分なテストとリスク管理を行ってください（本コードはデモ目的のロジックを含みます）。
  - シークレット（API キー、トークン）はソース管理に含めないでください（.env を利用し、 .gitignore を設定）。

---

もし README に追加したいサンプル、CI / テスト手順、あるいは各テーブルのスキーマ一覧（raw_prices / raw_news / ai_scores / market_regime など）を盛り込みたい場合は教えてください。必要に応じて README を拡張します。