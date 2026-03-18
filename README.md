# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
J-Quants から市場データ・財務データ・市場カレンダーを取得して DuckDB に蓄積し、特徴量計算・品質チェック・ETL パイプライン等のユーティリティを提供します。戦略・発注・監査周りのスケルトンも含みます。

---

## 主要な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 株価日足 / 財務データ / JPX マーケットカレンダーのフェッチ
- データ格納
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
  - 冪等な保存（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）
- ETL パイプライン
  - 差分取得（最終取得日からの差分取得、バックフィル）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損・スパイク（急騰/急落）・重複・日付整合性チェック
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成、DuckDB への保存、銘柄抽出（四桁コード）
  - SSRF/サイズ/XML 攻撃対策を考慮した実装
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用スキーマと初期化ユーティリティ

---

## 要件

- Python 3.8 以上（型注釈の Union 演算子や型に合わせて 3.8+ を想定）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib / datetime / logging 等を使用

（用途に応じて追加依存が必要な場合があります。パッケージ化時に requirements.txt を用意してください。）

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . や requirements.txt を使用）

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する

推奨の .env（例）:

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて変更
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

環境変数は `kabusys.config.settings` から参照可能です（必須変数は読み出すと ValueError を投げます）。

---

## データベース初期化

DuckDB スキーマを作成して接続を得るには data.schema.init_schema を使います。例:

Python スクリプト例:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

監査ログ専用 DB を初期化する場合:

```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

init_schema は親ディレクトリが無ければ自動で作成します。既存テーブルがあれば冪等的にスキップされます。

---

## ETL（データ取り込み）使い方

日次 ETL の実行例:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection, init_schema

# DB 初期化（まだの場合）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（target_date を指定しないと今日が対象）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

個別ジョブ（株価・財務・カレンダー）も呼べます:
- run_prices_etl(...)
- run_financials_etl(...)
- run_calendar_etl(...)

ETL は品質チェックをオプションで行います（デフォルトは実行）。

---

## ニュース収集使い方

RSS フェッチと保存の簡単な例:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes に有効な銘柄コードの集合を与えると記事と銘柄の紐付けを行う
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
```

fetch_rss / save_raw_news / save_news_symbols などの細かい API も利用可能です。

---

## 研究（Research）・特徴量計算の使い方

DuckDB 接続を渡してファクターを計算します。例:

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# 例: calc_ic を使った IC 計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

z-score 正規化ユーティリティは `kabusys.data.stats.zscore_normalize` または `kabusys.research` の再エクスポートで利用可能です。

---

## ログ・環境モード

- KABUSYS_ENV = development | paper_trading | live
  - settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
- 自動で .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## ディレクトリ構成（抜粋）

プロジェクトは Python パッケージ `kabusys` で構成されています。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント
    - news_collector.py             # RSS ニュース収集
    - schema.py                     # DuckDB スキーマ定義・初期化
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   # ETL パイプライン / run_daily_etl 等
    - calendar_management.py        # 市場カレンダー管理
    - audit.py                      # 監査ログスキーマ初期化
    - etl.py                        # ETL 関連公開インターフェース
    - features.py                   # 特徴量ユーティリティ公開
    - quality.py                    # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py        # 将来リターン・IC・summary 等
    - factor_research.py            # momentum / volatility / value 計算
  - strategy/                        # 戦略関連（骨組み）
    - __init__.py
  - execution/                       # 発注・執行関連（骨組み）
    - __init__.py
  - monitoring/                      # モニタリング（骨組み）
    - __init__.py

---

## 開発・テストのヒント

- 自動環境読み込みを無効化してテストしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の ":memory:" を利用すればファイルを作らずに単体テストが可能
- ネットワーク依存の機能（J-Quants, RSS）を単体テストする場合は該当関数（例: _urlopen, _request）をモックして差し替える設計になっています
- news_collector は defusedxml を利用して XML 攻撃を防止しています。HTTP レスポンスサイズの上限チェックが組み込まれています

---

## 注意事項 / 免責

- 本ライブラリは実際の発注処理や本番口座への自動売買を直接行う前に十分なテストが必要です。特に live 環境では危険が伴います。
- 環境変数や API トークンは慎重に管理してください（.env ファイルは機密情報を含むためバージョン管理に入れないでください）。
- 本 README はコードベースの現状に基づいた概要です。実際のプロダクト利用や運用時は追加ドキュメントや設定ファイル（.env.example、運用手順書等）を整備してください。

---

必要なら README に含める .env.example の具体例、より詳細な使い方（発注フロー、監査ログ参照方法、モニタリングの設定等）を追加で作成します。どの部分を詳しく説明しましょうか？