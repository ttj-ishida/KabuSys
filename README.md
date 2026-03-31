# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダ取得）、ニュース収集と LLM によるニュース・センチメント評価、ファクター計算・研究ユーティリティ、監査ログ（発注トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価・財務・カレンダー）と DuckDB への ETL
- RSS によるニュース収集と記事前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別）およびマクロセンチメント合成による市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティなど）とリサーチ用ユーティリティ
- 監査ログ・トレーサビリティ用テーブル定義と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 環境設定読み込み（.env / 環境変数）

設計上のポイントとして、ルックアヘッドバイアス防止（内部で現在日時を直接参照しない等）、冪等性（ON CONFLICT / idempotent 保存）、堅牢なリトライ・フェイルセーフ処理が重視されています。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証、レート制御、リトライ）
  - 市場カレンダー管理（営業日判定・next/prev trading day 等）
  - ニュース収集（RSS パーシング、前処理、SSRF 対策）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースの銘柄別スコアリング（score_news）
  - マクロセンチメント + ETF MA を組み合わせた市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライや JSON 検証を含む安全実装
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC/forward returns/統計サマリー等
- config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings オブジェクト）

---

## 前提条件

- Python >= 3.10（Union 型表記などを使用）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, logging, datetime, pathlib 等

（実際のインストールでは pyproject/requirements に合わせてパッケージをインストールしてください）

---

## セットアップ手順（例）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e .

4. 環境変数を設定する（.env / .env.local をプロジェクトルートに配置することで自動読み込みされます）
   - 以下は最低限必要な環境変数の例（実際の値は各サービスのトークンを使用してください）:

```
# .env の例
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# 任意
KABUSYS_ENV=development     # development | paper_trading | live
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

- 自動読み込みは、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。
- .env.local が .env を上書きする（上書き可）仕組みです。OS 環境変数は保護されます。

---

## 使い方（抜粋）

以下は代表的なユースケースの呼び出し例です。実際は適切なスクリプトやジョブから呼んでください。

- DuckDB に接続し ETL を実行する（Python REPL / スクリプト）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄別 ai_scores へ書き込み）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数で渡す
print("scored:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書込み）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（監査用 DuckDB を新規作成）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC timezone 設定も行われます
```

- 設定値の参照:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
```

---

## 主要な設計方針・注意点

- ルックアヘッドバイアス回避:
  - AI スコアリングやファクター計算では内部で date.today() や datetime.today() を直接参照せず、target_date を外部から渡す設計です。バッチやバックテストでの利用に適しています。
- 冪等性:
  - J-Quants から取得したデータは save_* 関数で ON CONFLICT DO UPDATE により上書きするため、再実行しても安全です。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API の失敗は基本的に例外で全体を止めず、ログに警告を出してフォールバック（例: macro_sentiment=0.0 やスキップ）します。
- セキュリティ対策:
  - news_collector は SSRF を避けるための検証、受信サイズ制限、defusedxml を使用した XML パースなどを行っています。
- レート制御:
  - J-Quants API 用に固定間隔の RateLimiter を実装し、レート制限（120 req/min）に準拠するよう設計されています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env の自動読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースの銘柄別センチメント（score_news）
    - regime_detector.py -- ETF MA とマクロセンチメントを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）と ETLResult
    - jquants_client.py  -- J-Quants API クライアント（fetch / save / get_id_token）
    - news_collector.py  -- RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py -- market_calendar 管理、営業日判定
    - quality.py         -- データ品質チェック
    - audit.py           -- 監査ログスキーマ初期化 / init_audit_db
    - stats.py           -- zscore_normalize 等の統計ユーティリティ
    - etl.py             -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/* その他の研究ユーティリティ
  - (その他) strategy, execution, monitoring などのパッケージ名が __all__ に含まれるが、今回のコードベースでは上記が中心

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — 通知用（必須）
- DUCKDB_PATH / SQLITE_PATH — デフォルト DB ファイルパス
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1）

設定は .env/.env.local または OS 環境変数で行います。.env のパースはシェル形式（export を含む）にも対応し、クォートやコメント処理を考慮しています。

---

## 開発・テストについて（簡潔）

- テスト用に OpenAI 呼び出しや HTTP 呼び出しはモックしやすいように内部呼び出し関数を分離しています（例: kabusys.ai.news_nlp._call_openai_api を patch 可能）。
- DuckDB を用いることで高速な単体テストが行えます（":memory:" を渡してインメモリ DB を使用可）。

---

## 貢献・ライセンス

- この README ではライセンスファイル・コントリビューション方針は未指定です。実運用・公開時は LICENSE と CONTRIBUTING を追加してください。

---

必要に応じて、README の具体的な実行スクリプト例（cron / Airflow / systemd ジョブの例）や .env.example のテンプレート、依存関係のリスト（requirements.txt / pyproject.toml）を追加できます。希望があれば追記します。