# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
DuckDB をストレージに用い、J-Quants API や RSS からデータを取得して ETL → 品質チェック → 特徴量算出 → 監査ログ／発注ワークフローへつなげるためのユーティリティ群を提供します。

主な設計方針は「データの冪等性」「Look‑ahead バイアス回避」「テスト容易性」「DB中心の監査トレーサビリティ」です。

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）自動ロード（無効化可）
  - 必須環境変数取得時のバリデーション
- Data（データ収集 / ETL / スキーマ）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - DuckDB スキーマ定義・初期化ユーティリティ
  - 差分更新型の ETL パイプライン（株価 / 財務 / カレンダー）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース（RSS）収集・前処理・DB保存・銘柄マッチング
  - 市場カレンダー管理（営業日判定・next/prev/trading days）
  - 監査ログ（signal/order/execution）用スキーマと初期化
- Research（研究用の特徴量・統計）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算（forward returns）
  - IC（Spearman rank）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- Execution / Strategy / Monitoring
  - パッケージ構造上の名前空間を準備（実際の戦略ロジックや発注実装は拡張可能）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションに | を使っているため）
- ネットワーク接続（J-Quants / RSS）

推奨手順（例）

1. リポジトリをチェックアウト / クローン
   git clone <repo-url>
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb defusedxml
   # またはプロジェクトで requirements.txt があればそれを使う
   # pip install -r requirements.txt
4. パッケージを editable インストール（任意）
   pip install -e .

環境変数（.env）について:
- プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携などで使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

その他の環境変数（デフォルトあり）:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（代表的な例）

以下は代表的なユースケースの簡単なサンプルコードです。実行前に上記の環境変数をセットしておいてください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からの差分取得 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS を取得して raw_news / news_symbols に保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(":memory:")  # メモリ DB でテスト
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄リストを用意
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算（例: モメンタム）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
results = calc_momentum(conn, target_date=date(2024, 1, 31))
# results は [{"date": date, "code": "7203", "mom_1m": 0.05, ...}, ...]
```

5) 将来リターン・IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
# factor_records は別途 calc_momentum 等で得たファクター配列
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6) J-Quants 生データ取得 & 保存（低レベル）
```python
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect(":memory:")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

---

## 主要モジュール説明

- kabusys.config
  - .env のロード、環境変数取得、設定オブジェクト（settings）
- kabusys.data.jquants_client
  - J-Quants API の取得 / 保存機能
  - rate limiter、リトライ、トークン自動更新などを実装
- kabusys.data.schema
  - DuckDB 上のスキーマ定義（Raw/Processed/Feature/Execution 層）
  - init_schema(), get_connection()
- kabusys.data.pipeline / etl
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETLResult による実行結果管理
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェック
- kabusys.data.news_collector
  - RSS 取得（SSRF対策 / gzipチェック / トラッキング除去）
  - raw_news, news_symbols 保存
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize（クロスセクション正規化）
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）初期化ユーティリティ

---

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/         # 発注・実行関連（名前空間）
    - strategy/          # 戦略実装（名前空間）
    - monitoring/        # 監視関連（名前空間）
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py

各モジュールは docstring に設計方針や前提（DuckDB のどのテーブルのみ参照するか等）が記載されています。研究用モジュールは本番口座／発注 API にアクセスしない設計になっています（安全な分析環境を想定）。

---

## 運用上の注意点

- 環境変数に秘密情報（J-Quants トークン、kabu API パスワード等）を含めるため、リポジトリにコミットしないでください。
- DuckDB のファイルはバックアップを取りつつ管理してください（特に監査ログ・発注履歴）。
- J-Quants のレート制限（120 req/min）を守る実装になっていますが、大規模なバッチは時間を分散してください。
- ニュース RSS の取得は外部 HTTP に対するセキュリティリスク（SSRF）を考慮して実装済みですが、追加フィードの登録は注意して行ってください。
- 本パッケージは戦略ロジックや発注連携の実装雛形を提供します。実際の発注を行う際は paper_trading / live モードの動作を十分に検証してください。

---

## 開発 / 貢献

- コードは各モジュールに詳細な docstring と設計コメントがあります。ユニットテストやモックによる検証が容易になるように、外部依存（HTTP 呼び出し、_urlopen、id token 取得等）を注入可能に設計されています。
- バグや改善提案があれば Issue / PR を送ってください。

---

この README はコードベースの主要機能を簡潔にまとめたものです。詳細は各モジュールの docstring を参照してください。必要であれば、サンプルスクリプトや運用手順（CI / Cron / コンテナ化）に関する追加ドキュメントを作成します。