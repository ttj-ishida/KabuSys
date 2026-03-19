# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に冪等に保存、ETL（差分取得）・品質チェック・特徴量計算・ニュース収集・監査ログなどを提供します。研究用途のファクター探索やストラテジ開発にも使えるユーティリティ群を含みます。

主な設計方針：
- DuckDB を中心にしたローカルデータレイク（Raw / Processed / Feature / Execution 層）
- J-Quants API のレート制御・リトライ・トークン自動更新を実装
- ETL は差分更新・バックフィル対応。品質チェックで問題を検出して通知可能
- ニュース収集は SSRF 対策・サイズ制限・トラッキングパラメータ除去などを実装
- 発注／監査周りは冪等・トレーサビリティ重視のスキーマ設計

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足・財務・取引カレンダー）
  - Idempotent（ON CONFLICT）で DuckDB に保存するユーティリティ
  - API レート制御（120 req/min）・リトライ・トークン自動リフレッシュ
- ETL
  - 差分取得（最終取得日からの差分）／バックフィル対応
  - 日次ETL エントリポイント（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損データ、スパイク（前日比大幅変動）、重複、日付不整合の検出
- マーケットカレンダー管理
  - JPX カレンダー取得・営業日判定（next/prev/get_trading_days）
  - DB の有無に応じた曜日フォールバック
- ニュース収集
  - RSS フィード取得（gzip対応）、記事正規化、トラッキングパラメータ除去
  - SSRF 対策（リダイレクト検査・プライベートIP拒否）
  - raw_news / news_symbols への冪等保存
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value など）
  - 将来リターン計算、IC（Spearman）の算出、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- スキーマ / 監査
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution）
  - 監査用テーブル（signal_events / order_requests / executions 等）と初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（Path | None 等の構文を使用しています）
- DuckDB を利用（ローカルファイルまたはインメモリ）

インストール（最小）
1. 仮想環境を作成して有効化：
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール：
   pip install duckdb defusedxml

（パッケージ化されている場合）
   pip install -e .

環境変数
- プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- 必須変数
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD      : kabuステーション API のパスワード（発注系を使う場合）
  - SLACK_BOT_TOKEN       : Slack 通知を行う場合の Bot トークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
- 任意 / デフォルト
  - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）

.env の例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

Python REPL / スクリプトからの利用例を示します。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査データベースの初期化（独立DBにしたい場合）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た DuckDB 接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュース収集を実行（既知の銘柄コードセットがある場合は紐付け可能）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードのセット（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

5) 研究用ファクター計算例
```python
from datetime import date
from kabusys.research import calc_momentum, zscore_normalize, calc_forward_returns, calc_ic

momentum = calc_momentum(conn, date(2025, 3, 1))
# Zスコア正規化
normed = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m","ma200_dev"])

# 将来リターンを取得して IC を計算
fwd = calc_forward_returns(conn, date(2025, 3, 1), horizons=[1,5,21])
ic = calc_ic(normed, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

ログレベルや環境切替は環境変数 `LOG_LEVEL`, `KABUSYS_ENV` で制御できます。`settings` オブジェクトから各種設定を参照できます：
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)
```

---

## 注意点 / 実装上の特徴

- J-Quants API クライアントは内部で固定間隔スロットリング（120 req/min）を実装しています。大量取得時はこの制限に従ってください。
- HTTP エラー時はリトライ（指数バックオフ）を行い、401 ではトークン自動リフレッシュを試みます。
- ニュース収集は SSRF 対策（リダイレクト先の検査・プライベートIP拒否）、受信サイズ制限（10MB）など安全対策を備えています。
- DuckDB への挿入は基本的に ON CONFLICT で冪等性を保証します。
- research モジュールや data.stats は外部ライブラリに依存しない実装を目指しています（pandas 等を使用していません）。
- テーブルの外部キーや ON DELETE 制約は DuckDB のバージョン制限によりアプリ側での整合維持を前提にしている箇所があります（README 内のスキーマコメント参照）。

---

## ディレクトリ構成

以下は本リポジトリの主要ファイル/モジュールの一覧（抜粋）です。

- src/kabusys/
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

（上記はソースツリーのうち README に関連する主要モジュールのみ抜粋しています。）

---

## 開発・貢献

- コードの拡張やバグ修正は Pull Request を歓迎します。  
- 新機能追加時は DuckDB スキーマの互換性に注意してください（DDLの変更は既存データへの影響を考慮）。

---

この README はコードベースの表層的な利用方法と主要な注意点をまとめたものです。詳細は各モジュールのドキュメンテーション文字列（docstring）を参照してください。必要であればサンプルスクリプトや運用手順（Cron ジョブ例、監視・アラート設定等）を追記できます。