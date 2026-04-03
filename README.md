# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、リサーチ、ニュース NLP、監査ログ、ならびに市場レジーム判定を含む自動売買基盤のライブラリ群です。バックテストや運用バッチの基盤コードを提供し、J-Quants / OpenAI / kabuステーション 等との連携を想定しています。

目次
- プロジェクト概要
- 主な機能一覧
- 前提（Prerequisites）
- セットアップ手順
- 環境変数（主な設定項目）
- 基本的な使い方（サンプル）
  - DuckDB 初期化（監査DB）
  - 日次 ETL 実行
  - ニュース NLP スコアリング
  - 市場レジーム判定
- ディレクトリ構成
- 補足・設計上の注意点

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージ群です。

- J-Quants API を用いたデータ ETL（株価日足 / 財務 / 市場カレンダー）
- raw データの品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントスコアリング
- 市場レジーム判定（ETF 指標 + マクロニュースの LLM スコア合成）
- 監査ログ（シグナル → 発注 → 約定のトレース）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- DuckDB を中心としたローカル DB 保存・冪等化機構

設計上、バックテスト時のルックアヘッドバイアスを避ける実装や、外部 API の堅牢なリトライ／フェイルセーフ処理を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save の一貫実装、レートリミット・リトライ・トークン管理）
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（データ品質チェック）
  - calendar_management（JPX カレンダー管理、営業日判定ユーティリティ）
  - audit（監査テーブル定義・初期化）
  - stats（zscore 正規化等の共通統計関数）
- ai/
  - news_nlp（news を集計して OpenAI で銘柄別スコアを作成）
  - regime_detector（ETF の MA とマクロニュース LLM を合成して市場レジーム判定）
- research/
  - factor_research（モメンタム、バリュー、ボラティリティなど）
  - feature_exploration（将来リターン計算、IC、統計サマリー）
- config.py
  - .env 自動読み込みロジック（プロジェクトルートの .env / .env.local を優先）
  - settings オブジェクトで環境変数にアクセス

---

## 前提（Prerequisites）

- Python 3.10+（型ヒントに Union 演算子などを使用）
- 推奨ライブラリ（少なくとも以下をインストールしてください）
  - duckdb
  - openai (OpenAI の新しい SDK を想定しているためバージョン互換に注意)
  - defusedxml
  - そのほか標準ライブラリで賄われる部分が多いですが、ネットワーク関連で urllib を利用します

依存関係はプロジェクト側で requirements.txt / pyproject.toml にまとめてください（このリポジトリの抜粋では記載されていません）。

---

## セットアップ手順

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. パッケージをインストール
   - 開発中の場合（編集を即座に反映したい場合）
     ```bash
     pip install -e .
     ```
   - もしくは requirements.txt / pyproject.toml から依存をインストールしてください:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成します。config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に自動読み込みします。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 主要な環境変数は次節参照。

---

## 環境変数（主な設定項目）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しに必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系で使用）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（既定: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live （既定: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

設定できる項目は config.Settings クラスのプロパティで確認できます。

---

## 使い方

以下は典型的なワークフローの一例です。Python REPL やスクリプトで利用できます。

前提: .env に必要な値（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定済み、パッケージがインストール済みであること。

1) 設定と DB 接続
```python
from kabusys.config import settings
import duckdb

# 設定例
db_path = str(settings.duckdb_path)  # data/kabusys.duckdb 等

# DuckDB 接続
conn = duckdb.connect(db_path)
```

2) 監査ログ用 DB 初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(db_path)  # :memory: も可
# 既存 conn に対してテーブルだけ追加したい場合は init_audit_schema を使用できます
```

3) 日次 ETL の実行（株価・財務・カレンダーの取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
# res は ETLResult オブジェクト（取得数・保存数・品質問題リストなど）
print(res.to_dict())
```

4) ニュース NLP スコアリング（OpenAI を用いて銘柄別スコアを生成）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続（raw_news, news_symbols, ai_scores テーブルが前提）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

5) 市場レジーム判定（ETF 1321 の MA とマクロニュース LLM を合成）
```python
from kabusys.ai.regime_detector import score_regime

# conn は DuckDB 接続（prices_daily, raw_news, market_regime が前提）
score_regime(conn, target_date=date(2026,3,20))
```

6) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

rows = calc_momentum(conn, target_date=date(2026,3,20))
# rows は各銘柄の辞書リスト（mom_1m, mom_3m, mom_6m, ma200_dev 等）
```

---

## ディレクトリ構成（主要ファイル）

（この README はコードベースに基づき生成しています。抜粋により一部ファイルを省略しています）

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割:
- config.py: .env 自動読み込み・Settings（環境変数の取得と検証）
- data/jquants_client.py: J-Quants API 通信、保存関数（raw_prices, raw_financials, market_calendar）
- data/pipeline.py: 日次 ETL の統合エントリポイント（run_daily_etl）
- data/news_collector.py: RSS 取得・前処理・raw_news への保存（SSRF 対策あり）
- data/quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）
- data/audit.py: 監査テーブルの DDL と初期化ユーティリティ
- ai/news_nlp.py: 銘柄別ニュース統合 → OpenAI でセンチメント → ai_scores へ書込み
- ai/regime_detector.py: ETF 指標とマクロ LLM スコアを合成して market_regime へ書込み
- research/*: ファクター計算と統計解析ユーティリティ

---

## 補足・設計上の注意点

- Look-ahead bias 対策:
  - ai モジュールや ETL は内部で date 引数を受け取り、datetime.today() や date.today() を直接参照しないよう設計されています。バックテストや日次バッチ実行時は明示的な target_date を渡してください。
- 環境変数の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。テストなどで無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の失敗時に処理を継続する設計（多くの箇所で失敗時はログ出力してフォールバック値を使用）になっています。運用時はログと品質チェックの結果を監視してください。
- DuckDB 互換性:
  - 一部実装において DuckDB の executemany の挙動（空リスト不可等）や SQL 機能への依存を考慮しています。DuckDB のバージョン差異に注意してください。

---

もし README をリポジトリのルート向けの形式（例: .env.example のテンプレートや依存関係ファイルの内容、実行スクリプト例）に合わせてさらに整備したい場合は、目的（開発者向け / 運用手順 / デプロイ手順）を教えてください。必要に応じて具体的な .env.example や systemd サービス例、監視手順なども追加で作成します。