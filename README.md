# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（部分実装サンプル）

このリポジトリは、日本株のデータ取得（J-Quants）、ETL、ニュース NLP、ファクター計算、監査ログなどを含むシステムコンポーネントの実装を集めたパッケージです。Trading / Research / DataPlatform の各機能群がモジュール化されています。

---

## 概要

KabuSys は以下の目的を想定した内部ライブラリ群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理
- OpenAI を用いたニュースセンチメント分析（銘柄別スコア）
- マクロニュースとETF（1321）の移動平均乖離を用いた市場レジーム判定
- 監査ログ（signal → order_request → execution）のテーブル初期化ユーティリティ
- 研究用途のファクター計算 / 特徴量評価ユーティリティ

設計上、ルックアヘッドバイアスを避ける実装方針やフェイルセーフなリトライ／バックオフ、DuckDB をメインの分析ストアとして使う点が特徴です。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、Settings API）
- J-Quants API クライアント（認証、ページネーション、保存関数）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS -> raw_news、SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント: score_news）
- 市場レジーム判定（ETF + マクロセンチメントの合成: score_regime）
- 研究用ユーティリティ（モメンタム/バリュー/ボラティリティ等のファクター算出）
- 監査ログスキーマ初期化（init_audit_db / init_audit_schema）

---

## 要件

- Python 3.10 以上（PEP 604 の型表記等を使用）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```
python -m pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして開発インストール（任意）
   ```
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```

2. 必要な Python パッケージをインストール
   ```
   python -m pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env を用意する

   このパッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

   主要な環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu ステーション API（必要な場合）
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack 通知（必要な場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   Settings は `kabusys.config.settings` から参照できます。

4. データディレクトリ（DUCKDB の親ディレクトリなど）を作成
   ```
   mkdir -p data
   ```

---

## 使い方（クイックスタート）

以下は主要な機能を Python から呼び出す例です。適宜 `duckdb.connect()` で接続先を指定してください。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（run_daily_etl）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 今日を対象に ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの銘柄別センチメントスコアを生成（score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"{n} 銘柄分スコアを書き込みました")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って監査テーブルにアクセスできます
```

- ファクター計算（研究用）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

---

## 環境変数自動読み込みの挙動

- 自動読み込み対象ファイル: `<project_root>/.env` をまず読み込み、次に `<project_root>/.env.local` を上書き読み込みします。
- OS 環境変数は優先されます（.env の値は既に存在する環境変数を上書きしませんが、.env.local は上書き可）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings を提供
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの銘柄別センチメント解析（score_news）
    - regime_detector.py
      - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数）
    - pipeline.py
      - ETL pipeline（run_daily_etl など）
    - etl.py
      - ETL の公開型（ETLResult）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - quality.py
      - データ品質チェック
    - news_collector.py
      - RSS 収集・前処理
    - calendar_management.py
      - 市場カレンダー管理（営業日判定等）
    - audit.py
      - 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、ランク等の研究ツール

各モジュールは docstring に処理フローや設計方針が記載されているため、詳細実装の理解に役立ちます。

---

## 開発・テスト

- テストは未梱包の場合は pytest 等を追加して実行してください。
- 外部 API（OpenAI, J-Quants）呼び出し部分はモック可能な設計（内部の呼び出し関数を patch）になっており、ユニットテストしやすくなっています。
- ETL や DB 書き込みは DuckDB のインメモリモード（":memory:"）でテスト可能です。

---

## 注意事項 / 運用上のヒント

- OpenAI リクエストはレート・レスポンスの不安定要素があるため、score_news / score_regime は内部でリトライとフェイルセーフ（失敗時はスコア0やスキップ）を行います。
- J-Quants API はレート制限（120 req/min）を遵守するため、jquants_client は内部でスロットリングとリトライを行います。
- 本ライブラリはバックテスト実行時のルックアヘッドバイアスを避ける実装方針（日時の扱い、DB クエリの排他条件など）で設計されています。バックテストで利用する場合は docstring の注意に従ってください。
- 本リポジトリに含まれるコードは「一部実装」に見える箇所があるため、運用で使う前に十分なレビューとテストを行ってください。

---

もし README に追記して欲しい項目（例: CI / デプロイ方法、より具体的な .env.example、ユースケース別のスクリプト例など）があれば教えてください。