# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ層として用い、J-Quants API や RSS ニュース等からデータを収集・整形し、研究（factor/research）や戦略／発注基盤につなげることを目的としています。

主な設計方針：
- DuckDB を中心に「Raw / Processed / Feature / Execution」のレイヤで構成
- J-Quants API からの取得は冪等・レート制限・リトライ・トークン自動更新を実装
- News 収集は SSRF / XML Bomb 等の攻撃対策を実装
- 研究用モジュールは外部依存を最小化（標準ライブラリ中心）
- ETL / 品質チェックは失敗時でも他処理は継続する（Fail-Fast しない設計）

---

## 機能一覧

- 環境設定管理
  - .env（プロジェクトルート）または環境変数から自動ロード（必要時に無効化可能）
  - 必須・デフォルト値の管理、KABUSYS_ENV / LOG_LEVEL 検証

- データ取得 / 保存（data/*）
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - 日足・財務データ・マーケットカレンダーの取得・DuckDB への冪等保存
  - RSS ニュース収集（正規化、トラッキングパラメータ除去、SSRF対策、DuckDB 保存）
  - DuckDB のスキーマ定義・初期化（raw / processed / feature / execution レイヤ）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新）
  - 監査ログ（signal → order → execution のトレーサビリティスキーマ）

- 研究・特徴量（research/*）
  - momentum / value / volatility 等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ（data.stats から提供）

- その他
  - ETL 結果／監査用のデータ構造、ログ出力・トレーサビリティ考慮

---

## セットアップ手順

前提
- Python 3.9+（コード中で型ヒントに | を多用しているため 3.10 以上が推奨されることがあります）
- DuckDB（Python パッケージ duckdb）
- ネットワーク接続（J-Quants API / RSS フィードへアクセス）

必須 Python パッケージ（最小）
- duckdb
- defusedxml

インストール例（pip）
```bash
pip install duckdb defusedxml
```

プロジェクトの配置例
- パッケージは src/kabusys 配下に収められています。プロジェクトルートに `pyproject.toml` または `.git` があると、kabusys.config が自動で .env を読み込みます。

環境変数 / .env
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード（発注層を使う場合）
  - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（通知を使う場合）
  - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID
- 任意（デフォルトあり）:
  - KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動ロードを無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると、config モジュールによる .env 自動読み込みを抑止できます
  - KABUS_API_BASE_URL    : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は最小限の利用例です。Python REPL やスクリプトから呼べます。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# または ':memory:' を指定してメモリ DB を使用
```

2) 日次 ETL を実行（J-Quants 認証トークンは settings から自動取得されます）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を呼ぶこと
result = run_daily_etl(conn)  # 引数に target_date や id_token を与えられます
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出時に利用する有効な銘柄コード集合
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算
```python
from datetime import date
import kabusys.research as research
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
t = date(2025, 1, 10)
mom = research.calc_momentum(conn, t)
fwd = research.calc_forward_returns(conn, t, horizons=[1,5,21])
ic = research.calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

5) J-Quants 生データ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))
# DuckDB に保存
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, rows)
```

6) 監査ログ（audit）を初期化
```python
from kabusys.data import audit
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
# または audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- settings（kabusys.config.settings）は環境変数未設定の必須キーを参照すると ValueError を投げます。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env の自動読み込みを抑止できます。
- J-Quants API はレート制限（120 req/min）に従います。jquants_client 内でスロットリングとリトライを行います。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys として想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py        : RSS 収集・正規化・DuckDB 保存
    - schema.py                : DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   : 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                 : 監査ログ用スキーマ（signal/order/execution）
    - etl.py                   : ETLResult の公開インタフェース
    - features.py              : 特徴量ユーティリティの再エクスポート
    - stats.py                 : zscore_normalize 等の統計ユーティリティ
    - quality.py               : 品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py
    - feature_exploration.py   : 将来リターン、IC、summary、rank
    - factor_research.py       : momentum/value/volatility ファクター計算
  - strategy/
    - __init__.py              : 戦略モデル用プレースホルダ（拡張想定）
  - execution/
    - __init__.py              : 発注ロジック・ブローカー統合のプレースホルダ
  - monitoring/
    - __init__.py              : 監視 / メトリクス関連（拡張想定）

---

## 開発・貢献

- コードはドメインを分離（data / research / strategy / execution）しており、各モジュールごとにユニットテストを追加してください。
- 外部 API を叩く箇所（jquants_client.fetch_* / news_collector._urlopen 等）はモック可能な設計になっています。ユニットテストではネットワークアクセスを行わないようモックしてください。
- DB に関するテストでは DuckDB の ':memory:' を活用すると高速に検証できます。

---

## 参考・運用上の注意

- 本ライブラリは実際の売買システムに接続する可能性があるため、live 環境では API トークン・パスワードの管理、発注ロジックの二重チェック・リスク管理を厳格に行ってください。
- ETL と品質チェックは失敗を局所化するように設計されていますが、品質チェックで error レベルが検出された場合は運用側で ETL の停止やアラートを検討してください。
- News 収集は外部 RSS を解析するため、XML 例外や想定外フォーマットに対する堅牢性（defusedxml 等）を維持していますが、未知のフィードはログ監視を行ってください。

---

この README はコードベース（src/kabusys）から抽出した設計意図・ API をまとめたものです。実際の利用時は各モジュールの docstring（関数・クラスの説明）を参照し、設定値／依存関係を適宜追加してください。