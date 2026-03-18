# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）です。  
DuckDB をバックエンドとしたデータレイク、J-Quants からのデータ取得、ETL パイプライン、特徴量計算、ニュース収集、品質チェック、監査ログなどを提供します。

---

## 概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API から株価日足、財務データ、JPX カレンダーを取得して DuckDB に永続化する（差分更新・冪等保存）。
- ETL（日次パイプライン）を実行して Processed / Feature レイヤを生成する。
- ニュース RSS の収集と記事→銘柄紐付け（SSRF 対策・トラッキング除去・メモリ上限などの堅牢化実装あり）。
- ファクター（モメンタム・バリュー・ボラティリティ等）とリサーチ用ユーティリティ（IC 計算、Z スコア正規化等）。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 発注/監査用スキーマ（監査ログ、発注要求、約定ログ）をサポート。

設計方針として、本番の取引 API への直接アクセスを避け、DuckDB / SQL と純粋な Python ロジックで解析・保存を行うことを重視しています。

---

## 主な機能一覧

- データ取得
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制限・リトライ・トークン自動更新対応
- データ保存
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
  - スキーマ初期化（raw / processed / feature / execution / audit）
- ETL
  - 差分取得（最終日からの差分・バックフィル対応）
  - 日次 ETL 実行関数（run_daily_etl）
- ニュース収集
  - RSS 取得（SSRF 対策・gzip 上限・XML 安全パーサ）
  - 記事正規化・トラッキング除去・ID 生成・DB 保存と銘柄抽出
- リサーチ / 特徴量
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算（calc_forward_returns）
  - IC（スピアマン順位相関）計算（calc_ic）、統計サマリー（factor_summary）
  - Zスコア正規化（zscore_normalize）
- 品質チェック
  - 欠損データ、スパイク、重複、日付不整合チェック（run_all_checks）
- 監査ログ
  - 信号 / 発注要求 / 約定 の監査テーブルと初期化ユーティリティ

---

## 要件

- Python 3.9+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

（その他は標準ライブラリのみで実装されています。HTTP は urllib 標準モジュールを使用します。）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発中でローカルパッケージとして扱う場合:
# pip install -e .
```

---

## セットアップ手順

1. Python 仮想環境を作成して有効化
2. 必須パッケージをインストール（上記参照）
3. 環境変数を設定（後述）
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化の例:
```python
from kabusys.data import schema

# ファイル DB を作る場合
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB を使う場合
# conn = schema.init_schema(":memory:")
```

監査ログ用の初期化（監査専用 DB を使う場合）:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 環境変数

KabuSys は .env または OS 環境変数から設定を読み込みます（プロジェクトルートに .env/.env.local があれば自動読み込み）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション（発注用、このコードベースでは参照のみ）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

必須変数が未設定の場合、Settings プロパティから参照すると ValueError が発生します。

---

## 使い方（代表的なワークフロー）

以下は代表的な利用例です。モジュールの公開 API を使って簡単に処理を実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは環境変数経由で自動使用）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

3) ニュース収集ジョブを実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # など
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: saved_count}
```

4) ファクター計算 / リサーチ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.stats import zscore_normalize
from datetime import date

target = date(2025, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターン取得（翌日・翌週・翌月）
fwd = calc_forward_returns(conn, target)

# IC 計算の例
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

5) 品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

6) J-Quants から直接データ取得（詳細な制御が必要な場合）
```python
from kabusys.data import jquants_client as jq

daily = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存:
jq.save_daily_quotes(conn, daily)
```

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル/モジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存関数
    - news_collector.py            — RSS 収集・正規化・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                  — ETL パイプライン、差分更新ロジック
    - calendar_management.py       — 市場カレンダー管理
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ（signal/order/execution）
    - etl.py                       — ETL 結果型公開
    - features.py                  — 特徴量ユーティリティ公開
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py       — 将来リターン / IC / summary
  - strategy/                       — （戦略層: 骨組み用）
  - execution/                      — （発注/ブローカー連携: 勘案）
  - monitoring/                     — （監視用モジュール）

上記はコードベースの主要なモジュールで、さらに細かなユーティリティ関数や内部設計上のファイルが含まれます。

---

## 開発メモ / 注意点

- 環境変数の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml のある親）を探索して .env と .env.local を自動読み込みします。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- J-Quants クライアントは内部で固定間隔の RateLimiter を使い、最大 120 req/min を遵守する設計です。429/408/5xx に対する指数バックオフリトライと、401 を受けた場合の ID トークン自動リフレッシュを備えています。
- News collector は SSRF・XML Bomb 等に対する防御を行っています（defusedxml、リダイレクト検査、受信サイズ上限、プライベートホスト排除など）。
- DuckDB のバージョン特性（例: 一部 FK の ON DELETE 制約未サポート）を考慮した設計になっています。運用時は DuckDB のバージョン互換性に注意してください。
- このライブラリはデータ収集・解析・監査を主目的とし、本番口座への自動発注を行う際は別途厳格な検証・安全対策が必要です（例: リスク管理・二重チェック・機密管理・証券会社 API の挙動確認）。

---

もし README に追加したい実行例、CI 用ハウスキーピング、サンプル .env.example、あるいはパッケージ公開用の pyproject.toml/requirements.txt のテンプレートが必要であれば教えてください。