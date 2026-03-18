# KabuSys

日本株向けのデータプラットフォームと自動売買基盤のライブラリ群です。  
DuckDB を中心としたデータレイク、J-Quants API クライアント、ニュース収集、ETL パイプライン、品質チェック、特徴量計算、監査（オーディット）スキーマなどを含みます。研究（Research）用途と本番（Execution）用途の双方を想定した設計です。

---

## 主な特徴 / 機能一覧

- 環境設定管理
  - .env ファイルまたは環境変数から設定を自動ロード（自動ロードは無効化可能）
- データ取得 / 保存
  - J-Quants API クライアント（株価・財務・市場カレンダー）
  - レート制限／リトライ／トークン自動リフレッシュ対応
  - DuckDB へ冪等（idempotent）保存（ON CONFLICT を使用）
- ETL パイプライン
  - 差分更新（バックフィル対応）
  - 市場カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合実行
- ニュース収集
  - RSS フィード取得、前処理（URL 除去・正規化）、記事IDは正規化 URL の SHA-256（先頭 32 文字）
  - SSRF / XML Bom 対策（defusedxml、リダイレクト検査、プライベートIP検査、サイズ上限）
  - DuckDB へ冪等保存（raw_news / news_symbols）
- データスキーマ管理
  - Raw / Processed / Feature / Execution 層を備えた DuckDB スキーマ定義と初期化ユーティリティ
  - 監査用スキーマ（signal_events / order_requests / executions 等）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Spearman）計算・ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査・トレーサビリティ設計
  - 発注から約定まで UUID による追跡を想定した監査テーブル

---

## 必要条件

- Python 3.8+（型ヒントや新しい構文が使用されています。プロジェクトに合わせて適宜調整してください）
- 依存パッケージ（例）
  - duckdb
  - defusedxml

インストール時に正確な依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください（このリポジトリ内にない場合は上のパッケージを入れてください）。

例:
```
pip install duckdb defusedxml
```

---

## 環境変数 / .env

このパッケージは .env ファイルまたは OS 環境変数から設定を読み込みます（プロジェクトルートに `.git` または `pyproject.toml` がある場合に自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client の認証に使用。
- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（Execution 層で使用）。
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使う Bot トークン（必要に応じて）。
- SLACK_CHANNEL_ID (必須)  
  Slack 送信先チャンネル ID（必要に応じて）。
- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

サンプル .env（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成し依存パッケージをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```
3. 必要な環境変数を .env に設定（上記参照）
4. DuckDB スキーマ初期化
   - メインデータベースを初期化:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - 監査ログ専用 DB（任意）:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     audit_conn.close()
     ```

---

## 使い方（基本例）

以下はライブラリの主要な使い方の抜粋例です。

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- J-Quants から株価を直接取得して保存する（テスト時）
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect(":memory:")
# スキーマをあらかじめ作成しておくこと
# records = jq.fetch_daily_quotes(date_from=..., date_to=...)
# saved = jq.save_daily_quotes(conn, records)
```

- RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # あらかじめ保持する銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# zscore 正規化例
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 将来リターンと IC（Spearman）の計算
```python
from kabusys.research import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, target_date=date(2024, 1, 31), horizons=[1,5,21])
# factor_records は calc_momentum 等の出力
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 開発 / テスト時の便利な設定

- 自動 .env ロードを無効化（ユニットテスト等）:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- jquants_client のネットワーク呼び出しをモックすることでテスト可能（get_id_token / _request 等をモック）

---

## ディレクトリ構成（主要ファイル）

```
src/kabusys/
├─ __init__.py            (パッケージ定義 / version)
├─ config.py              (環境変数・設定管理)
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py   (J-Quants API クライアント、保存ユーティリティ)
│  ├─ news_collector.py   (RSS 取得・記事保存・銘柄抽出)
│  ├─ schema.py           (DuckDB スキーマ定義と init_schema)
│  ├─ stats.py            (zscore_normalize 等の統計ユーティリティ)
│  ├─ pipeline.py         (ETL パイプライン、run_daily_etl 等)
│  ├─ features.py         (特徴量インターフェース)
│  ├─ calendar_management.py (市場カレンダー管理 / 営業日ロジック)
│  ├─ audit.py            (監査ログスキーマ初期化)
│  ├─ etl.py              (ETL 結果クラス再エクスポート)
│  └─ quality.py          (データ品質チェック)
├─ research/
│  ├─ __init__.py
│  ├─ feature_exploration.py (将来リターン / IC / サマリー)
│  └─ factor_research.py     (momentum / volatility / value 計算)
├─ strategy/
│  └─ __init__.py  (戦略層のプレースホルダ)
├─ execution/
│  └─ __init__.py  (発注/ブローカー連携のプレースホルダ)
└─ monitoring/
   └─ __init__.py  (監視用プレースホルダ)
```

各ファイルはモジュール化され、DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計が多く、外部サービス（証券会社/発注）への直接アクセスは Execution 層に集約する想定です。研究用モジュールは本番発注にはアクセスしません（安全設計）。

---

## 補足・設計上の注意点

- DuckDB に対する DDL は冪等であり、init_schema は既存テーブルを上書きしません（存在チェック済み）。
- J-Quants API クライアントは API レート制限（120 req/min）を守るための簡易レートリミッタとリトライを実装しています。
- News Collector は SSRF / XML 攻撃 / Gzip Bomb などへの対策を含みます。
- 監査（audit）スキーマはトレーサビリティを重視しており、一度記録した監査ログを削除しない運用を前提としています（FK 制約は DuckDB のサポート差によりアプリ側での整合性対応が必要な場合があります）。
- 本 README はコードベースの現在の実装に基づいて作成しています。実際の運用では pyproject.toml / requirements の確認、及び環境固有の設定（Kabu API の接続設定や Slack 設定）を行ってください。

---

もし README のサンプル .env.example、起動スクリプト（CLI）, または具体的な使用例（ETL を cron で回す設定、監視・アラートの例）を追加したい場合は要件を教えてください。必要に応じてテンプレートを作成します。