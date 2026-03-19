# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ETL、特徴量生成、ニュース収集、品質チェック、監査ログなどを包括的に提供します。

## プロジェクト概要
このライブラリは以下の目的で設計されています。
- J-Quants API からの株価・財務・カレンダー等のデータ取得（ページネーション・リトライ・レート制御含む）
- 取得データを DuckDB に冪等保存（ON CONFLICT/UPSERT）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け（SSRF 対策・サイズ制限・正規化）
- ファクター／特徴量計算（モメンタム、ボラティリティ、バリュー等）と研究用ユーティリティ（IC・統計サマリー）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ
- マーケットカレンダー管理（営業日判定、next/prev/trading days）

設計上のポイント:
- DuckDB を中心とした 3 層アーキテクチャ（Raw / Processed / Feature / Execution）
- 外部に出さないべき操作（発注等）は別モジュールで抽象化
- Look-ahead bias 回避のため fetched_at を記録
- 冪等性とトランザクション単位での安全な DB 操作

---

## 主な機能一覧
- data.jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
- data.schema: DuckDB スキーマ定義と初期化（init_schema）
- data.pipeline: 日次 ETL（差分取得・保存・品質チェック）と個別 ETL ジョブ
- data.news_collector: RSS 収集、正規化、DB 保存、銘柄抽出
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.calendar_management: カレンダー更新と営業日判定ユーティリティ
- data.audit: 監査ログ（signal / order_request / executions）
- research.factor_research / research.feature_exploration: ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC、統計サマリー
- data.stats: Z スコア正規化ユーティリティ
- 環境変数管理（.env の自動読み込み、必要変数の検証）

---

## 必要要件 (Prerequisites)
- Python 3.10 以上（型注釈の union 表記などに依存）
- 必要パッケージ（主要なもの）:
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime 等

※ 実行環境によっては追加のパッケージが必要になる場合があります。requirements.txt が用意されている場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. 必要パッケージをインストール
（プロジェクトに requirements.txt がない場合は最低限以下を手動でインストールしてください）
```bash
pip install duckdb defusedxml
# 開発用: pip install -e .
```

3. 環境変数設定
- ルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利）。

必須の環境変数（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注実装を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）

例: `.env`
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は Python スクリプトからモジュールを使う例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得／更新）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS → raw_news, news_symbols へ保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4) ファクター計算・研究用ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
value = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

5) 設定参照（settings の利用）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

---

## 主要 API（抜粋）
- kabusys.data.schema.init_schema(db_path) → DuckDB 接続（テーブル作成済み）
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) → ETLResult
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.fetch_rss(url, source) → list[NewsArticle]
- kabusys.data.news_collector.save_raw_news(conn, articles) → list[new_ids]
- kabusys.data.quality.run_all_checks(conn, target_date=None) → list[QualityIssue]
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize(records, columns)

各関数はドキュメンテーション文字列で引数・戻り値・例外を詳述しているので、IDE の補完やソース参照を推奨します。

---

## ディレクトリ構成（主要ファイル）
以下はコードベースの主要ファイル・モジュール一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（version）
  - config.py — 環境変数管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得／保存ユーティリティ）
    - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と初期化（init_schema）
    - pipeline.py — ETL パイプラインと個別 ETL ジョブ（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー更新・営業日判定ユーティリティ
    - audit.py — 監査ログ向けテーブル定義と初期化
    - etl.py — ETLResult 型の再エクスポート
    - features.py — 特徴量ユーティリティ（再エクスポート）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py — 研究用 API の公開（calc_momentum 等）
    - factor_research.py — ファクター計算（Momentum/Volatility/Value）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py — 戦略層（暫定）
  - execution/
    - __init__.py — 発注/約定管理（暫定）
  - monitoring/
    - __init__.py — 監視/通知（暫定）

---

## 運用に関する注意点
- DuckDB ファイルのバックアップを定期的に行ってください（データは運用上重要です）。
- J-Quants の API レートリミット・利用規約を遵守してください。jquants_client は 120 req/min を想定した制御を含みますが、運用環境での急激な並列実行は避けてください。
- news_collector は外部 URL を扱うため SSRF 対策・リダイレクト検査・サイズ制限等を実装していますが、運用ネットワークポリシーに合わせた追加の制約を検討してください。
- 監査ログ（audit）を有効にしておくと発注フローのトレースが容易になります。監査 DB は別ファイルに分けることも可能です（init_audit_db）。

---

## テスト・デバッグ
- 単体テストや CI を用意している場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みをスキップできます（テストで明示的に環境変数を注入したい場合に便利）。
- jquants_client の HTTP 呼び出しはモック化してテストしてください（トークン取得やリトライロジックの検証が必要）。

---

## おわりに
この README はコードベースの概要と主要な使い方、セットアップ手順を簡潔にまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。実運用に移す際は、認証情報や DB のバックアップ、例外監視・再試行ポリシーなどを適切に設定してください。