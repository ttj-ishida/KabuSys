# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
J-Quants から市場データを取得して DuckDB に蓄積し、特徴量計算・品質チェック・監査ログ・ニュース収集などを行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような関心事を分離しつつ統合した、小〜中規模の日本株自動売買プラットフォームの基盤ライブラリです。

- データ取得（J-Quants API）／保存（DuckDB）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と記事⇄銘柄紐付け
- 特徴量（ファクター）計算（モメンタム、バリュー、ボラティリティ等）と正規化ユーティリティ
- マーケットカレンダーの管理（営業日判定など）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）

設計上、戦略や実際の発注 API へのアクセスは別モジュールで扱うことを想定しており、Data 層と Research（分析）層は本ライブラリ単体で完結するように実装されています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API からのページネーション対応取得（株価・財務・カレンダー）
  - レートリミット、リトライ、トークンリフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/schema, data/audit
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 初期化ユーティリティ（init_schema / init_audit_db）
- data/pipeline
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック実行（quality モジュール統合）
- data/news_collector
  - RSS 取得（SSRF対策・gzip 上限・トラッキングパラメータ除去）
  - raw_news への冪等保存、記事ID の SHA-256 ベース生成
  - 記事内から銘柄コード抽出して news_symbols に紐付け
- data/quality
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）と IC（calc_ic）
  - 統計・正規化ユーティリティ（zscore_normalize, factor_summary, rank）

---

## 必須・推奨要件

- Python 3.9+
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml

（その他、運用時に Slack 連携や kabuステーション API 等を使う場合は追加依存や認証情報が必要です）

インストール例（開発環境）:
```bash
python -m pip install duckdb defusedxml
# パッケージを編集可能インストールする場合
pip install -e .
```

---

## 環境変数（設定）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化

例 .env（参考）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール
   - duckdb, defusedxml など
4. 必要な環境変数を .env に記載（プロジェクトルート）
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" 可
# 監査ログ用 DB を別ファイルで初期化する場合
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（簡易ガイド）

以下は代表的な利用例（Python スクリプト内での呼び出し例）です。

- 設定値の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から株価を Fetch → DuckDB に保存（個別利用）:
```python
from kabusys.data import jquants_client as jq
import duckdb

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
conn = duckdb.connect("data/kabusys.duckdb")
saved = jq.save_daily_quotes(conn, records)
```

- ニュース収集ジョブを実行:
```python
from kabusys.data import news_collector
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究用ファクター計算:
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2024,2,1))
vol = calc_volatility(conn, target_date=date(2024,2,1))
val = calc_value(conn, target_date=date(2024,2,1))
```

- 特徴量の Z スコア正規化:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

---

## API の主要ポイント（開発者向け）

- jquants_client._request はレートリミットとリトライ、401 リフレッシュを実装。
- fetch_* 関数はページネーションを吸収して全レコードを返す。
- save_* 関数は DuckDB へ冪等的に保存（ON CONFLICT）する。
- ETL は部分失敗を許容し、品質チェック結果を ETLResult に格納する。
- news_collector は SSRF 対策、XML デフューズ、gzip 上限など安全面を重視。
- calendar_management は market_calendar の有無に応じて曜日ベースのフォールバックを行う。
- audit モジュールは監査（signal/order/execution）用スキーマを初期化するユーティリティを提供。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - feature_exploration.py
  - factor_research.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（README 化のため抜粋：実際のリポジトリにはコメント文や他ファイルが含まれます）

---

## ログ・環境設定

- LOG_LEVEL 環境変数でログレベルを指定（デフォルト INFO）。
- KABUSYS_ENV により挙動を切替可能（development / paper_trading / live）。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## テスト・ローカル実行ヒント

- DuckDB は ":memory:" を指定すればインメモリ DB で簡単にテスト可能です。
- jquants_client のネットワーク呼び出しは関数をモックして差し替えるとユニットテストが容易です。
- news_collector._urlopen などはテスト用にモックしやすい設計になっています。

---

## ライセンス / 貢献

この README はコードベースから自動生成的に作成したドキュメントです。実運用向けには README に加えて .env.example、運用手順、CI/CD やロールバック手順などを別途整備してください。

貢献・バグ報告は Pull Request / Issue を通してください。

---

質問や追加で載せたい使用例があれば教えてください。README に追記して整形します。