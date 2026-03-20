# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の基盤機能を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「小さな外部依存」「DuckDB を中心とした軽量DB設計」です。

---

## 機能一覧（概要）

- 環境設定管理
  - .env / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（J-Quants トークン等）
- データ取得・保存（J-Quants）
  - 日次株価（OHLCV）
  - 四半期財務データ
  - JPX マーケットカレンダー
  - リトライ・レート制御・トークン自動リフレッシュ対応
- DuckDB スキーマの定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス定義
- ETL パイプライン
  - 差分取得（バックフィル付き）・保存（冪等）
  - 市場カレンダー調整、品質チェックフック
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - 記事 ID の正規化（URL 正規化 → SHA256）
  - raw_news / news_symbols への冪等保存
- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量生成（feature_engineering）
  - 生ファクターの統合、ユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT
- シグナル生成（signal_generator）
  - features と ai_scores を統合して最終スコアを計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの置換保存
- マーケットカレンダー管理（calendar_management）
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティテーブル群設計

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントに | None 等を使用）
- Git リポジトリ（自動 .env ロードは .git または pyproject.toml をプロジェクトルートの検出に利用）

1. リポジトリをクローン／配置
   - 例: git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （他にテストや lint を用いる場合はそれらをインストール）

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用（必須）
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル（必須）
   - 任意: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
   - システム: KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL (DEBUG/INFO/...)

   ※ config.Settings クラスがこれらを取得します。未設定の場合は ValueError を投げます（必須項目）。

---

## 使い方（簡易例）

以下は最小限の操作例です。用途に応じてスクリプト化してください。

1) DuckDB スキーマ初期化
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

2) 日次 ETL（J-Quants から差分取得して保存）
```python
# run_daily_etl を呼び出す例
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへの書き込み）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect('data/kabusys.duckdb')
count = build_features(conn, target_date=date(2024,1,1))
print('upserted features:', count)
```

4) シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect('data/kabusys.duckdb')
n = generate_signals(conn, target_date=date(2024,1,1))
print('generated signals:', n)
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
# sources を None にするとデフォルト RSS ソースを使う
res = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
saved = calendar_update_job(conn)
print('calendar saved:', saved)
```

注意点:
- J-Quants API 呼び出しは rate-limit（120 req/min）やリトライが入っています。
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ります。init_schema で初期化済みの DB を使うことを推奨します。
- 本ライブラリは発注（execution）層への直接呼び出しを行わない設計が多いです。execution 層は別プロセス・ジョブとして実装する想定です。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト有り）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を読み込みます。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとした概観）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - news_collector.py         — RSS 取得・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義 & init_schema
    - stats.py                  — zscore_normalize 等統計ユーティリティ
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — カレンダー更新 / 営業日判定
    - audit.py                  — 監査ログテーブル DDL（signal/events/orders/executions）
    - features.py               — data.stats の再エクスポート
    - execution/                — 発注関連（空パッケージ／拡張箇所）
  - research/
    - __init__.py
    - factor_research.py        — momentum/volatility/value の計算
    - feature_exploration.py    — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築（Z スコア正規化等）
    - signal_generator.py       — final_score 計算、BUY/SELL シグナル生成
  - monitoring/                 — 監視・メトリクス（拡張箇所）
  - execution/                  — 実行・ブローカー連携（拡張箇所）

---

## 開発・拡張のヒント

- DuckDB の接続は軽量なのでユニットテストでは ":memory:" を使えます（schema.init_schema(":memory:")）。
- ネットワーク呼び出し（jquants_client.fetch_* / news_collector.fetch_rss）はモックしやすい設計です（例: _urlopen を差し替え）。
- config._find_project_root は __file__ を基点に親ディレクトリを探索するため、開発時に .env を読み込ませるにはワークツリーの位置に注意してください。自動ロードが不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 多くの DB 書き込みはトランザクション＋バルク挿入で原子性を確保しています。エラー時の挙動は各モジュールのログに従います。

---

## ライセンス / コントリビューション

（ここにライセンスと貢献ルールを追記してください）

---

問題報告・改善提案があれば README を更新いただくか、Issue を作成してください。