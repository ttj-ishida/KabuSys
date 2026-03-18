# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

---

## 概要

KabuSys は日本株のデータ収集（J-Quants 等）、DuckDB によるデータ格納、品質チェック、特徴量生成、戦略研究用ユーティリティ、ならびに発注や監査ログのためのスキーマを提供する Python パッケージです。  
設計方針として「Look-ahead bias を避ける」「冪等（idempotent）な保存」「外部 API 呼び出しのレート制御」「品質チェックの非破壊実行（Fail-Fast しない）」を重視しています。

主な用途:
- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存
- RSS からニュース収集してニュースと銘柄紐付けを実行
- 研究用にモメンタム／ボラティリティ／バリュー等のファクター計算と IC / 統計要約の提供
- ETL パイプラインの実行・品質チェック
- 実行（発注）・監査向けスキーマの初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要で無効化可能）
  - 必須環境変数取得ヘルパー（未設定時に明示的エラー）

- データ取得・保存（data/jquants_client.py）
  - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ対応）
  - 株価日足 / 財務データ / 市場カレンダーの取得・DuckDB への冪等保存

- ETL パイプライン（data/pipeline.py）
  - 差分取得（最終取得日からの差分 + backfill）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 結果を ETLResult オブジェクトで返却

- データ品質チェック（data/quality.py）
  - 欠損、主キー重複、スパイク（前日比急変）、日付整合性（未来日・非営業日）検出
  - QualityIssue のリストで詳細を返す

- ニュース収集（data/news_collector.py）
  - RSS フィード取得（SSRF対策、gzip上限、XML安全パース）
  - URL 正規化／トラッキングパラメータ除去、記事ID = SHA-256(正規化URL)[:32]
  - raw_news / news_symbols への冪等保存

- スキーマ管理（data/schema.py / data/audit.py）
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の初期化
  - 監査ログ（signal_events, order_requests, executions）初期化ユーティリティ

- 研究系ユーティリティ（research/）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic（Spearman）、factor_summary、rank
  - zscore_normalize（data.stats）を再エクスポート

---

## 動作要件（目安）

- Python 3.9+（typing の Union などを使っているため新しめの Python を推奨）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS 等）および適切な API トークン

pip インストール例（仮）:
pip install duckdb defusedxml

プロジェクトをパッケージとして利用する場合は pyproject.toml / setup に従ってください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e .

4. 環境変数設定（プロジェクトルートに .env を配置）
   - 自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 必須環境変数（例 .env）
   以下は最低限の例です（実運用では実際の値を設定してください）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（主要ユースケースとサンプル）

以下は Python スクリプト／REPL から利用する際の代表的な呼び出し例です。

1) DuckDB スキーマ初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

- init_schema は親ディレクトリを自動作成し、全テーブルを冪等で作成します。

2) 日次 ETL 実行

from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ETL はカレンダー → 株価 → 財務 → 品質チェックの順に実行します。
- 品質チェックの結果は result.quality_issues に格納されます。

3) ニュース収集ジョブ実行

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count}

4) 研究・ファクター計算

from datetime import date
import duckdb
from kabusys.research import (
    calc_momentum,
    calc_volatility,
    calc_value,
    calc_forward_returns,
    calc_ic,
    factor_summary,
    zscore_normalize,
)

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンを算出して IC を計算
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

5) 監査スキーマ初期化（監査専用 DB を使う場合）

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数・設定について

- 自動ロード優先順位:
  OS 環境変数 > .env.local > .env
- 自動ロードを無効化:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings（kabusys.config.Settings）で取得される代表的な設定:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH, SQLITE_PATH (デフォルト値あり)
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

---

## ディレクトリ構成

プロジェクト内の主なファイル／ディレクトリ（抜粋）:

src/kabusys/
- __init__.py
- config.py                # 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
  - news_collector.py      # RSS ニュース収集・保存
  - schema.py              # DuckDB スキーマ定義・初期化
  - stats.py               # 統計ユーティリティ（zscore_normalize）
  - pipeline.py            # ETL パイプライン
  - quality.py             # 品質チェック
  - calendar_management.py # 市場カレンダー管理
  - audit.py               # 監査ログ（signal/order/execution）スキーマ
  - features.py            # 特徴量ユーティリティ公開
  - etl.py                 # ETL 公開インターフェース
- research/
  - __init__.py
  - feature_exploration.py # 将来リターン / IC / summary
  - factor_research.py     # momentum / volatility / value 計算
- strategy/                 # 戦略関連（骨組み）
- execution/                # 発注・執行関連（骨組み）
- monitoring/               # モニタリング（骨組み）

README.md（本ファイル）

---

## 開発上の注意点 / 設計上のポイント

- DuckDB へは冪等に保存（ON CONFLICT DO UPDATE / DO NOTHING）することを基本としているため、ETL を何度実行してもデータの上書きや重複が最小化される設計です。
- J-Quants クライアントはレートリミット（120 req/min）に合わせたスロットリングと再試行ロジックを実装しています。大規模取得を行う場合は遅延や API 制限に注意してください。
- ニュース収集では SSRF、XML Bomb、gzip 解凍の上限などを意識した堅牢な実装になっています。ただし、外部 RSS のバラつきには注意してください。
- 実運用で「live」環境を使う場合は KABUSYS_ENV を正しく設定し、Kabuステーションなど実際の発注インターフェース実装を慎重に行ってください（本リポジトリ内の execution／strategy は骨組みとして提供されています）。

---

## サポート / 貢献

バグ修正や改善提案は Issue / Pull Request を通じてお願いします。README の内容やドキュメントを拡張する PR も歓迎します。

---

以上。必要であれば README に実行例のスクリプト（CLI の雛形）や .env.example のファイルを追加します。どの部分をより詳しく書くか指示してください。