# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants など外部データソースからデータを取得して DuckDB に保存し、特徴量計算・戦略研究・ETL・監査ログを行えるようにすることを目的としています。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- データ取得（J-Quants API クライアント）
- ETL / データパイプライン（差分取得、保存、品質チェック）
- DuckDB スキーマ定義・初期化
- ニュース収集（RSS → raw_news）
- ファクター計算（Momentum / Volatility / Value 等）
- 研究用ユーティリティ（Forward returns / IC / 統計サマリ）
- 監査ログ（シグナル → 発注 → 約定のトレース）
- 環境変数 / 設定管理
- マーケットカレンダー管理、監視・品質チェック

設計方針の特徴：
- DuckDB を中心にローカルで効率的にデータ処理
- J-Quants API のレート制御・リトライ・トークン自動更新を内蔵
- 各保存処理は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を意識
- 本番発注 API へのアクセスは実装境界で分離（安全対策）

---

## 機能一覧

主要機能（抜粋）

- 環境設定
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - Settings クラスで設定値を取得

- データ取得・保存
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB へ保存（save_daily_quotes, save_financial_statements, save_market_calendar）

- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック

- データ品質チェック
  - 欠損値 / 重複 / スパイク / 日付整合性チェック
  - QualityIssue 型で結果を返す（error / warning）

- ニュース収集
  - RSS フィード取得と前処理（リンク正規化、トラッキング除去、SSRF対策）
  - raw_news / news_symbols への保存（冪等）

- 研究用ファクター
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore 正規化ユーティリティ

- スキーマと監査
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_db による初期化

---

## 前提 / 依存パッケージ

（本リポジトリの requirements.txt は含まれていない想定なので、主要な依存は手動で入れてください）

必須（想定）:
- Python 3.9+
- duckdb
- defusedxml

推奨:
- その他標準ライブラリのみで多くを実装していますが、実行環境に合わせて logging 等を設定してください。

インストール（例）:
```bash
python -m pip install duckdb defusedxml
# パッケージ化されている場合:
# python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 必要な環境変数を用意する（下記参照）。プロジェクトルートに `.env` を作成すると自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. DuckDB スキーマ初期化（下記「初期化例」参照）

---

## 環境変数（主なもの）

注: Settings クラス（kabusys.config.Settings）から参照します。必須のキーは get 時にエラーになります。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化

.env の読み込み優先順:
- OS 環境変数 > .env.local > .env

---

## 初期化・使い方（簡単な例）

以下は基本的なワークフローのコード例です。Python REPL やスクリプトで実行してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# デフォルト path は settings.duckdb_path（例: data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data import pipeline

result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: テキストから抽出する銘柄コードの集合（例: prices_daily から取得）
known_codes = set([row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()])

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

4) ファクター計算（研究用）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

target = date(2025, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) 監査ログ用 DB 初期化（監査専用 DB を別にしたい場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## よく使う API / モジュールまとめ

- kabusys.config
  - settings: 環境設定 (jquants_refresh_token, kabu_api_password, ...)

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize (re-exported from data.stats)

---

## ディレクトリ構成

主要ファイル/モジュール配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py     — RSS ベースのニュース収集
    - schema.py             — DuckDB スキーマ定義と init_schema
    - stats.py              — zscore_normalize 等統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — 特徴量関連の公開インターフェース
    - calendar_management.py— 市場カレンダー管理・バッチジョブ
    - audit.py              — 監査ログテーブルの定義・初期化
    - etl.py                — ETL 公開 API（ETLResult 再エクスポート）
    - quality.py            — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — forward returns / IC / summary
    - factor_research.py     — momentum / value / volatility 計算
  - strategy/                — 戦略層（未実装スケルトン）
  - execution/               — 発注実行層（未実装スケルトン）
  - monitoring/              — 監視関連（未実装スケルトン）

（実際のリポジトリにより多少差分がある可能性がありますが、上記が主要構成です）

---

## 運用上の注意・補足

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を目印）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- J-Quants API はレート制限あり（120 req/min）。クライアントは内部で RateLimiter を使って規制しています。
- save_* 関数は基本的に冪等（ON CONFLICT）を想定していますが、DB スキーマやバージョン依存に注意してください。
- DuckDB のバージョン差異や制約（ON DELETE CASCADE のサポート等）により設計上のコメントがあるため、実運用前に使用する DuckDB バージョンの互換性を確認してください。
- セキュリティ: news_collector では SSRF 対策や XML の安全パースを組み込んでいますが、外部 URL を扱う際はさらに運用ルールを設けてください。

---

貢献・拡張案
- strategy / execution 層の具体実装（ブローカー連携）
- モニタリング / アラート送信（Slack 連携）
- テスト用の fixtures / モック（外部APIやネットワークのモック化）
- Docker コンテナ化・Cron ジョブ化による定期実行

---

以上。必要であれば README に含めるサンプルコードや導入スクリプト（Makefile / example .env.example）を追加しますか？