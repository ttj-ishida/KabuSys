# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、RSS によるニュース収集、ニュースの LLM（OpenAI）によるセンチメント評価、市場レジーム判定、ファクター計算・特徴量探索、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方の例、ディレクトリ構成を日本語でまとめます。

## プロジェクト概要

- 目的: 日本株の自動売買プラットフォームのコアコンポーネント群を提供する。
- 設計方針:
  - ルックアヘッドバイアスを避ける（date/time を直接参照しない設計）。
  - DuckDB を中心としたローカルデータベースで ETL と解析を行う。
  - LLM（OpenAI）呼び出しは堅牢なリトライ・バリデーションを行う。
  - ETL / 品質チェック / 監査ログは冪等（idempotent）で実装。
  - セキュリティ面（SSRF 防止、XML パースの安全化など）に配慮。

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の取得とバリデーション

- データ取得 / ETL
  - J-Quants API クライアント（株価、財務、マーケットカレンダー等）
  - 差分取得（backfill を含む）・冪等保存（DuckDB へ ON CONFLICT DO UPDATE）
  - 日次 ETL の統合処理（run_daily_etl）

- ニュース収集 / NLP
  - RSS からニュースを収集して raw_news テーブルへ保存（SSRF 対策、gzip 上限等）
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（data.quality）

- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル作成・初期化（data.audit）

## 必要条件 / 依存パッケージ

最低要件（コードベースの構文から推定）:
- Python 3.10+

主な外部ライブラリ（インストール必須）:
- duckdb
- openai
- defusedxml

推奨インストール例:
pip install duckdb openai defusedxml

（プロジェクト配布に requirements.txt / pyproject.toml があればそれを使用してください）

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能呼び出し時に参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します（テスト用）

注: パッケージは起動時にプロジェクトルート（.git or pyproject.toml を基準）を探索し、.env → .env.local の順で読み込みます（OS 環境変数が優先されます）。

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. Python 仮想環境を作成 & 有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (または Windows では .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他の開発用パッケージやテストツールを追加）
4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xxxxx
     - SLACK_CHANNEL_ID=xxxxx
     - OPENAI_API_KEY=xxxxx（AI を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
   - テストや CI で自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB 用ディレクトリが必要に応じて作成されます（data/ 等）。init_audit_db が親ディレクトリを自動作成します。

## 使い方（主なユースケースとコード例）

以下は最小限の使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（前日15:00 JST～当日08:30 JST のウィンドウ）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
# OPENAI_API_KEY が環境変数に無い場合は api_key="sk-..." を引数で渡せます
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（モメンタム / ボラティリティ / バリュー）:
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- 監査ログスキーマの初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# または既存の conn に対して init_audit_schema(conn, transactional=True) を呼ぶ
```

- ニュース収集（RSS フィードの取得関数）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意点:
- OpenAI を呼ぶ関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は DuckDB 接続を受け取り、DuckDB 上の所定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を前提とします。
- run_daily_etl 等は内部で例外を捕捉して処理継続する設計です。返却される ETLResult で品質問題やエラーの有無を確認してください。

## テスト / 開発用のヒント

- .env の自動ロードを無効にしたいとき:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 API をモックしてユニットテストを実行することが想定されています（内部の _call_openai_api 等を patch 可能）。
- DuckDB の一時接続は ":memory:" を使えます（init_audit_db も ":memory:" に対応）。

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント解析（OpenAI）
  - regime_detector.py  — マクロ + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（fetch / save）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETL 結果クラスの再エクスポート
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - quality.py          — データ品質チェック
  - calendar_management.py — マーケットカレンダー管理（営業日判定など）
  - news_collector.py   — RSS ニュース収集
  - audit.py            — 監査ログ（テーブル作成・初期化）
- research/
  - __init__.py
  - factor_research.py  — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー

（上記に加え、プロジェクトルートに pyproject.toml / setup.cfg / requirements.txt がある想定です。実際の配布物に従ってください。）

## ライセンス・貢献

この README にはライセンスやコントリビューション手順は含まれていません。実際のリポジトリに LICENSE ファイルや CONTRIBUTING.md がある場合はそちらに従ってください。

---

何か特定機能の詳細ドキュメント（例: ETL のパラメータ詳細、AI プロンプト設計、DB スキーマの完全一覧、.env.example のテンプレートなど）を追加で生成する必要があれば教えてください。