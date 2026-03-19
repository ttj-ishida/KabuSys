# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群（データ取得／ETL／研究／監査／実行基盤のユーティリティ群）。

本リポジトリは、J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB スキーマ定義・初期化、ETL パイプライン、データ品質チェック、ファクター計算（研究用）、監査ログスキーマなどを提供します。発注・モニタリング機能の骨格（モジュール）は含まれますが、ブローカー固有の実装はアダプタ側で用意します。

バージョン: 0.1.0

---

## 主な機能

- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検査（settings オブジェクト）
  - 環境（development / paper_trading / live）とログレベル検証

- データ取得（J-Quants クライアント）
  - 株価日足（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レートリミッタ、リトライ、トークン自動リフレッシュ、取得時刻（fetched_at）記録

- データ保存（DuckDB 向け）
  - raw / processed / feature / execution / audit レイヤーのテーブル定義と初期化
  - 冪等保存（ON CONFLICT で上書き）ユーティリティ

- ETL パイプライン
  - 差分取得（最終取得日を元に必要分のみ取得）
  - backfill（後出し修正の吸収）
  - 日次 ETL 実行エントリポイント（run_daily_etl）

- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトによる報告（severity: error / warning）

- ニュース収集
  - RSS フィード取得・前処理・ID 生成（URL 正規化→SHA-256）
  - SSRF / gzip bomb / コンテンツ長上限等の安全対策
  - raw_news / news_symbols への一括保存

- 研究用モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算（forward returns）
  - IC（Spearman rank correlation）計算、Zスコア正規化、統計サマリー

- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブルとインデックス
  - トレーサビリティ設計（order_request_id を冪等キー等）

---

## 要件

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで HTTP は urllib を使用（requests は不要）

（本 README はパッケージ化の有無に依らず利用できるようにコマンド例を記載しています）

---

## セットアップ手順

1. リポジトリをクローン（既にある場合は省略）

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell 等)

3. 依存関係をインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   ※ プロジェクトで requirements.txt / pyproject.toml があればそちらを使ってください:
   pip install -e .

4. 環境変数の設定 (.env)

   プロジェクトルート（.git または pyproject.toml を検出）に `.env` / `.env.local` を置くと自動で読み込まれます。
   テスト等で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

   オプション（デフォルト値あり）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 監視 DB のパス（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ作成）

DuckDB にスキーマを作成して接続を得る簡単な例:

python コード例:
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を元にした Path を返します
conn = init_schema(settings.duckdb_path)
```

監査ログ専用 DB 初期化:
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

注意: init_schema はファイルパスの親ディレクトリがなければ自動で作成します。":memory:" を渡すとインメモリ DB が使えます。

---

## 使い方（主要ユースケース）

- 日次 ETL を実行して市場データを取り込む:

```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行する:

```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes に銘柄コードセットを渡すと記事→銘柄紐付けが行われます
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- 研究用ファクター計算（例: モメンタム）:

```
from kabusys.research.factor_research import calc_momentum
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
records = calc_momentum(conn, target_date=date(2025, 1, 31))
# records は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict リスト
```

- 将来リターンと IC 計算:

```
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
# forward_records = calc_forward_returns(conn, date)
# factor_records = ... (例えば calc_momentum の結果)
ic = calc_ic(factor_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
```

- 設定値利用:

```
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

---

## 主要 API（短い説明）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token (トークン取得)

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(conn, target_date, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source) → NewsArticle list
  - save_raw_news(conn, articles) → saved IDs
  - run_news_collection(conn, sources, known_codes)

- kabusys.data.quality
  - run_all_checks(conn, target_date, ...) → list[QualityIssue]

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize (re-exported from data.stats)

- kabusys.data.audit
  - init_audit_db / init_audit_schema

---

## 実行上の注意点・ベストプラクティス

- J-Quants API のレート制限（120req/min）を守る設計になっています。大量のパラレル実行は避けてください。
- データの整合性を保つため、ETL を定期実行する際は run_daily_etl を推奨します（市場カレンダーを先に取得し、営業日に調整します）。
- 本番環境での発注・実行は慎重に。settings.is_live / is_paper を利用して環境スイッチを行ってください。
- ニュース収集では SSRF 等のセキュリティ対策を施していますが、外部ソースの追加時は信頼性を確認してください。
- テスト時に .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下はパッケージの主要ファイル群（src/kabusys 配下）の概要です：

- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py           - J-Quants API クライアント（取得 & 保存）
    - news_collector.py           - RSS ニュース収集・前処理・DB 保存
    - schema.py                   - DuckDB スキーマ定義・初期化
    - stats.py                    - 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                 - ETL パイプライン（run_daily_etl 等）
    - features.py                 - 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py      - 市場カレンダー管理（営業日判定等）
    - audit.py                    - 監査ログスキーマ初期化
    - etl.py                      - ETLResult の公開インターフェース
    - quality.py                  - データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py      - forward returns, IC, factor_summary, rank
    - factor_research.py          - momentum / volatility / value の計算
  - strategy/
    - __init__.py                 -（戦略実装用のパッケージ）  
  - execution/
    - __init__.py                 -（発注/実行連携用のパッケージ）
  - monitoring/
    - __init__.py                 -（監視/メトリクス用のパッケージ）

---

## ライセンスと貢献

- 本プロジェクトのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください。
- バグ報告や機能提案は Issue を作成してください。プルリクエスト歓迎です。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。具体的な利用フロー（スケジューラ設定、ブローカーアダプタ実装、Slack 通知設定等）は運用要件に応じて別途ドキュメント化してください。