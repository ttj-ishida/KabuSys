# KabuSys

日本株向け自動売買システムのコアライブラリ（部分実装）。  
本リポジトリはデータ取得・ETL、データ品質チェック、特徴量生成、ファクタリサーチ、ニュース収集、監査ログなどを含むデータプラットフォーム／戦略基盤の主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は主に次の目的のために設計された Python パッケージです。

- J-Quants API から日本株データ（株価日足、財務データ、マーケットカレンダー）を取得・保存する
- DuckDB を用いたデータスキーマ管理・ETL（差分取得、冪等保存）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング削除等を備えた収集器）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリューなど）と特徴量探索（将来リターン・IC 等）
- 監査ログ（シグナル→発注→約定のトレースを残すテーブル群）
- 発注／実行／モニタリング層の土台（モジュール構造を含む）

設計上の注意点:
- DuckDB を中心に SQL + Python で実装（データ処理はローカル DB で完結）
- 本番発注 API（kabuステーション等）へは直接アクセスしないモジュールと、将来的に接続するための配置がある
- 外部依存は最小化。ただし実行には `duckdb`、`defusedxml` 等が必要

---

## 機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード、必須設定チェック）
- J-Quants API クライアント
  - レート制限（固定間隔スロットリング）
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 日足 / 財務 / マーケットカレンダーのページネーション対応フェッチ
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン（差分取得、バックフィル、品質チェックの一括実行）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ニュース収集
  - RSS フィード取得（gzip 対応）
  - URL 正規化・トラッキング削除・記事 ID 生成（SHA256）
  - SSRF 対策（スキーム/プライベートIPチェック、リダイレクト検証）
  - raw_news / news_symbols への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 研究用ファクター計算
  - calc_momentum, calc_volatility, calc_value
  - forward returns, IC（Spearman）、統計サマリー、rank、Z-score 正規化
- マーケットカレンダー管理（営業日判定・前後営業日算出・夜間更新ジョブ）
- 監査ログスキーマ（signal_events / order_requests / executions）

---

## 前提条件

- Python 3.9+（型アノテーションに | を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

（パッケージ管理や CI 用に requirements.txt / pyproject.toml を用意することを推奨）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows の場合は .venv\Scripts\activate）
3. 依存をインストール
   - pip install duckdb defusedxml
   - （必要ならその他の依存も追加）
4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを探索）
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - SLACK_BOT_TOKEN（必須）
   - SLACK_CHANNEL_ID（必須）
   - 任意: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH 等
6. データベース初期化
   - Python インタプリタやスクリプトから DuckDB スキーマを初期化します（下記参照）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD … kabuステーション API パスワード（必須）
- KABUSYS_ENV … environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL … ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID … 通知用 Slack
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH … 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD … 値が設定されていると .env 自動ロードを無効化

settings は kabusys.config.settings 経由で利用できます（未設定の場合は ValueError が発生します）。

---

## 使い方（代表的な例）

以下は簡単な Python 例です。適宜ログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマ初期化（全テーブル作成）
```
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```
from kabusys.data.pipeline import run_daily_etl
# conn は schema.init_schema の戻り値
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes: 銘柄リスト（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

4) リサーチ（ファクター計算）
```
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

5) J-Quants API を直接使ってデータを取得する例
```
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 取得後に save_* を使って DB に保存できます（save_daily_quotes 等）
```

6) 監査スキーマ初期化（監査テーブルのみ別 DB にセットアップする場合）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動ロード機能、settings オブジェクト（J-Quants トークン等）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（レート制御・リトライ・保存）
    - news_collector.py  — RSS 取得、前処理、DB 保存、銘柄抽出
    - schema.py          — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py        — ETL パイプライン、run_daily_etl 等
    - features.py        — 特徴量ユーティリティの公開インターフェース
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - quality.py         — データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - audit.py           — 監査ログ（signal_events / order_requests / executions）
    - etl.py             — ETLResult の公開（pipeline のラッパ）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — forward returns / calc_ic / factor_summary / rank
  - strategy/            — 戦略層（プレースホルダ）
  - execution/           — 発注実装（プレースホルダ）
  - monitoring/          — 監視・モニタリング（プレースホルダ）

注: 上記は現状の主要なモジュール（コードベースのスナップショット）です。strategy / execution / monitoring パッケージは骨組みが用意されています。

---

## 注意事項・運用上のヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テストや CI で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限（120 req/min）に従う設計ですが、万が一 API の仕様が変わった場合は jquants_client の定数を見直してください。
- DuckDB のバージョンや SQL 方言に依存する箇所があります。特に外部キーや ON DELETE 動作は DuckDB のバージョンにより異なるため注意してください（ソースコード内にも注記あり）。
- ニュース収集は外部入力を扱うため、defusedxml を使って XML 系の脆弱性対策を行っていますが、運用環境ではさらにプロキシや接続制限を検討してください。
- 設計は「本番口座への誤発注を防ぐ」意図で段階的なモジュール分離を行っています。実際に発注を行うには execution 層の実装と十分な検証が必要です。

---

この README は実装済みのモジュールの概要と基本的な使い方を示しています。実運用や拡張を行う際は各モジュール内ドキュメント（関数の docstring）を参照し、テスト環境で十分に検証してください。