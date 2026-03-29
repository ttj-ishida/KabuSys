# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
Data ETL、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、データ品質検査、監査（トレーサビリティ）など、アルゴリズム取引に必要な基盤処理群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- J-Quants API と連携した株価・財務・カレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存・集計
- RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄単位）およびマクロセンチメントの評価
- ETF（1321）200日移動平均乖離 + マクロセンチメントの合成による市場レジーム判定
- ファクター（モメンタム/バリュー/ボラティリティ等）計算と探索的解析ツール
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）テーブル初期化ユーティリティ
- 設定の環境変数/`.env` ロード機能（自動ロードはプロジェクトルート検出に基づく）

設計上、バックテストや本番運用で Look‑ahead bias を避けるために日付参照の扱いに注意が払われています（内部で datetime.today()/date.today() を勝手に参照しない関数設計など）。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、自動リフレッシュ、ページネーション、レート制限、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS 取得、前処理、news_symbols との紐付け）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄ごとにニュースをまとめて OpenAI でスコア化）
  - レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
  - Robust な API 呼び出し（リトライ/バックオフ、JSON バリデーション）
- research/
  - ファクター計算（momentum, value, volatility）および特徴量解析（forward returns, IC, summary）
- config.py
  - 環境変数/`.env` 読み込み、必須値チェック、設定のラッパー（settings）

セキュリティ・運用的配慮:
- RSS: SSRF 対策、最大受信バイト制限、gzip 解凍の保護
- J-Quants: レート制限（120 req/min）、401 の自動リフレッシュ、リトライ/バックオフ
- OpenAI 呼び出し: 429/ネットワーク/タイムアウト/5xx に対するリトライ
- ETL/DB 書き込み: 冪等性（ON CONFLICT DO UPDATE）を重視

---

## 必須前提 / 推奨環境

- Python 3.10 以上（typing の | 記法を使用しているため）
- 必要な追加パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）

パッケージはプロジェクトの packaging 構成に依存しますが、手動でインストールする例:

```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt があれば:
# python -m pip install -r requirements.txt
```

---

## 環境変数（設定）

KabuSys は環境変数およびプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB 保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（score_news / score_regime の引数に指定可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (任意) — 自動 .env ロードを無効化（主にテスト用）

例 (.env.example):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 上記は機密情報を含むため、実運用では適切に管理してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを配置
2. Python 環境を用意（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
3. 環境変数を設定（.env をプロジェクトルートに置く）
4. DuckDB の配置ディレクトリ確保（例: data/）
   ```bash
   mkdir -p data
   ```
5. 監査 DB を初期化（任意）
   - Python スクリプト例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```
6. ETL 実行や AI スコア処理を行う

---

## 使い方（例）

以下はライブラリを直接利用する簡単なサンプルです。日付には datetime.date オブジェクトを渡します（内部で現在日時を直接参照しない設計）。

- DuckDB に接続して日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント（ai.news_nlp.score_news）を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
conn.close()
```

- 市場レジーム判定（ai.regime_detector.score_regime）を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
conn.close()
```

- 監査スキーマ初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を監査ログ用途で使用
conn.close()
```

補足:
- score_news / score_regime は OpenAI API キーが必要。api_key 引数を渡すか OPENAI_API_KEY を環境変数でセットしてください。
- run_daily_etl は内部で calendar ETL → prices ETL → financials ETL → 品質チェック を順に実行します。エラーは個別に捕捉され、ETLResult に記録されます。

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定ラッパー
- kabusys.data.pipeline
  - run_daily_etl(...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.jquants_client
  - get_id_token(...)
  - fetch_daily_quotes(...)
  - save_daily_quotes(...)
  - fetch_financial_statements(...)
  - save_financial_statements(...)
  - fetch_market_calendar(...)
  - save_market_calendar(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(...)
- kabusys.data.quality
  - run_all_checks(...)
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
- kabusys.data.audit
  - init_audit_db(path)
  - init_audit_schema(conn, transactional=False)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

各関数の詳細は該当モジュール内の docstring を参照してください。多くの関数は DuckDB 接続オブジェクトを受け取り、prices_daily / raw_prices / raw_financials / raw_news 等のスキーマを前提とします。

---

## ディレクトリ構成（src/kabusys の抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄単位ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py — ETL パイプラインと ETLResult
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 取得・前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定など）
    - quality.py — データ品質チェック群
    - audit.py — 監査ログスキーマ定義・初期化
    - etl.py — ETLResult の再エクスポート
    - stats.py — zscore_normalize など統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai, research, data の他に strategy/, execution/, monitoring/（__all__ に含むが本サマリに含まれる実装は別）

各モジュールは docstring に設計方針や処理フローが丁寧に記載されています。実運用前に該当ドキュメントとコードをよく確認してください。

---

## 運用上の注意点

- 機密情報（API キー等）は安全に保管してください（.env を Git に含めない等）。
- OpenAI 呼び出しはコストが発生します。バッチサイズ・頻度を運用に合わせて調整してください。
- J-Quants API はレート制限に従ってください（モジュール内で制御あり）。
- DuckDB のバージョン依存差（executemany の挙動など）があるため、本番環境での検証を事前に行ってください。
- Look‑ahead bias 回避のため、バックテストではデータの取得日と使用日を正しく分離してください（ライブラリはその方針をサポートしていますが、ユーザー側でも運用ルールを守る必要があります）。

---

README に記載してほしい追加項目（例: CI / テスト方法、具体的なテーブルスキーマ、デプロイ手順など）があれば教えてください。必要に応じて .env.example のテンプレートや SQL スキーマ抜粋も用意します。