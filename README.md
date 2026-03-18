# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

簡潔な説明:
- J-Quants / RSS 等から市場データやニュースを収集し、DuckDB に保存する ETL パイプライン
- 特徴量（momentum / volatility / value 等）の計算、品質チェック、監査ログスキーマ、ニュース収集などを含む
- 発注・実行・監視のためのスキーマ群とユーティリティを提供（実際のブローカー API 呼び出し部分は別途実装）

## 主な機能一覧
- データ収集
  - J-Quants API から株価日足・四半期財務・マーケットカレンダーを取得（jquants_client）
  - RSS からニュース記事を安全に収集・正規化・DB保存（news_collector）
- ETL パイプライン
  - 差分取得（バックフィル考慮）・保存（冪等）・品質チェックをまとめて実行（data.pipeline）
- データ品質検査
  - 欠損・重複・スパイク・日付不整合の検出（data.quality）
- スキーマ管理
  - DuckDB に対するスキーマ初期化・監査ログスキーマ（data.schema, data.audit）
- 研究／特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー（research.feature_exploration）
  - Zスコア正規化など統計ユーティリティ（data.stats）
- ニュースの銘柄抽出とニュース⇄銘柄紐付け（news_collector）
- 環境設定管理
  - .env 自動読み込み、必須環境変数の取得、実行環境フラグ（config.Settings）

## 必要条件（推奨）
- Python 3.10+
- 主要依存パッケージ
  - duckdb
  - defusedxml

（パッケージ化や requirements.txt が無い場合は上記を手動でインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

## 環境変数（主なもの）
以下は Settings クラスから参照される主要な環境変数です。必須項目は README で明示しています。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（default: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` が自動で読み込まれます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

## セットアップ手順（ローカルでの最小手順）
1. リポジトリをクローン
2. 仮想環境を作成し依存パッケージをインストール（上記参照）
3. 必要な環境変数を設定（.env も可）
   - 例 `.env`（プロジェクトルート）
     ```
     JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```
4. DuckDB スキーマの初期化（Python REPL またはスクリプトで実行）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# これで必要なテーブルが作成されます
```
5. 監査ログスキーマを追加する（任意）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

## 使い方（代表的な操作例）

- 日次 ETL の実行（市場カレンダー・株価・財務を差分取得して品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn)
print(res.to_dict())
```

- ニュース収集ジョブ実行（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 抽出対象の有効銘柄コードセット（例: '7203','6758',...）
known_codes = {"7203", "6758"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソース毎の新規保存数
```

- 研究用関数（ファクター計算や IC 計算）
```python
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = get_connection("data/kabusys.duckdb")
from datetime import date
tgt = date(2024, 1, 31)

mom = calc_momentum(conn, tgt)
vol = calc_volatility(conn, tgt)
val = calc_value(conn, tgt)

fwd = calc_forward_returns(conn, tgt, horizons=[1,5,21])
# 例: calc_ic を使って mom_1m と fwd_1d の相関を計算
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)
```

- J-Quants からのデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings の refresh token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

## 開発・運用上の注意点
- J-Quants API に対してはモジュール内で固定間隔のレート制御（120 req/min）とリトライ処理を実装しています。大量取得の際はこの点に留意してください。
- get_id_token はリフレッシュトークンから idToken を取得し、401 時に自動更新するロジックを持ちます。
- news_collector には SSRF 遮断・gzip 解凍上限・XML パースの安全対策（defusedxml）など多数の防御処理が入っています。
- DuckDB の INSERT は ON CONFLICT を使って冪等保存を行います。ETL は失敗しても既存データを破壊しない設計です。
- data.quality のチェックは Fail-Fast せず全件収集し、呼び出し側が重大度に応じて対処する設計になっています。
- 環境設定自動読み込みはプロジェクトルートの .env/.env.local を参照しますが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

## ディレクトリ構成（主要ファイル）
以下は本リポジトリの主要モジュール一覧（サブパッケージを含む）。実際のファイル/行数は省略しています。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント & 保存関数
    - news_collector.py  — RSS ニュース収集・前処理・保存
    - schema.py  — DuckDB スキーマ定義・初期化
    - stats.py   — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - features.py  — 特徴量ユーティリティ公開接口
    - calendar_management.py  — 市場カレンダー管理・判定ユーティリティ
    - audit.py  — 監査ログスキーマ（signal/order/execution の追跡）
    - etl.py  — ETLResult 再エクスポート
    - quality.py  — データ品質チェック
  - research/
    - __init__.py  — 研究用 API の再エクスポート
    - factor_research.py  — momentum/volatility/value 等の計算
    - feature_exploration.py — 将来リターン / IC / summary / rank
  - strategy/  — 戦略関連（空の __init__.py; 実装は追加）
  - execution/ — 発注・実行関連（空の __init__.py; 実装は追加）
  - monitoring/ — 監視関連（空の __init__.py; 実装は追加）

## テスト・デバッグのヒント
- 単体テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境に依存しないようにする。
- DuckDB は ":memory:" を使えばインメモリ DB でテスト可能（init_schema(":memory:")）。
- news_collector._urlopen 等のネットワーク関数はモジュール内で差し替え（モック）可能な設計になっています。

---

この README はコードベースから抽出した機能・使い方の概要です。実稼働に当たっては各 API キー・トークンの管理、実行環境（paper_trading / live）設定、監査用 DB の構築、ログ監視、リスク管理ルールの実装などを必ず行ってください。必要であれば、使い方のサンプルスクリプトや追加のドキュメント（API 利用フロー、運用手順）も作成します。