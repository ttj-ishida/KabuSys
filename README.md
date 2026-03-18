# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
J-Quants や RSS 等からマーケットデータを収集・ETL し、DuckDB に格納、特徴量計算・リサーチ・発注監査などのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール群から構成されています。

- データ取得（J-Quants API）と DuckDB への冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（JPX）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- ファクター／特徴量計算（モメンタム、バリュー、ボラティリティ等）
- 研究用ユーティリティ（将来リターン、IC 計算、統計サマリー）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 設定管理（.env 自動ロード、環境変数取得ラッパ）

設計上の注意点:
- DuckDB をデータストアとして利用（ファイルまたはインメモリ）
- 本番発注 API には依存しない設計（データ収集 / 研究は外部発注へ影響しない）
- 冪等性を意識した保存ロジック（ON CONFLICT 句など）
- 外部依存は最小限（主に duckdb, defusedxml）

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - fetch / save の組で DuckDB へ冪等保存
- data/schema
  - DuckDB のテーブル定義・初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline
  - 日次 ETL（市場カレンダー・日足・財務データ）と品質チェック
- data/news_collector
  - RSS 取得、記事正規化、raw_news への保存、news_symbols への紐付け
  - SSRF 対策・受信サイズ制限・XML の安全パース
- data/calendar_management
  - 営業日判定、next/prev_trading_day、夜間カレンダー更新ジョブ
- data/quality
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- research
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（正規化ユーティリティ）
- audit
  - 監査ログ用スキーマ、order_requests / executions 等の初期化ユーティリティ
- config
  - .env 自動ロード（.env, .env.local）、必須環境変数チェック（Settings クラス）

---

## 必要環境・依存

- Python 3.10 以上（型ヒントに | を使用）
- 必要パッケージ例:
  - duckdb
  - defusedxml

※パッケージ管理（setup.py / pyproject.toml）はプロジェクト配布側で用意してください。ローカルで使う場合は最低限以下をインストールしてください:

pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（例）:

   pip install -r requirements.txt
   または
   pip install duckdb defusedxml

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードの優先順位は: OS 環境変数 > .env.local > .env

4. DuckDB スキーマ初期化
   - ファイル DB を使用する場合は親ディレクトリを自動作成します。
   - 例:

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

5. 監査ログ専用 DB 初期化（必要に応じて）:

   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡単な例）

以下は代表的な利用例です。すべて Python スクリプトから呼び出します。

- 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化（最初のみ）
conn = schema.init_schema(settings.duckdb_path)

# ETL 実行（本日分）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)

# 既知銘柄コードセットを渡して紐付けを行う（省略可能）
known_codes = {"7203", "6758", "1605"}

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 市場カレンダー更新（夜間バッチ）

```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 研究用（ファクター計算・IC 計算）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect(str("data/kabusys.duckdb"))
target = date(2024, 3, 1)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)

# 例: mom の "mom_1m" と fwd の "fwd_1d" の IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- 品質チェック

```python
from kabusys.data import quality, schema

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（将来的な発注で使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack のチャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（必要に応じて）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

settings オブジェクトは kabusys.config.settings から参照できます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に配置されています。主なファイルと役割は以下の通り。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / .env 管理（Settings）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py               -- J-Quants API クライアント & 保存ユーティリティ
  - news_collector.py               -- RSS 収集・前処理・DB 保存
  - schema.py                       -- DuckDB スキーマ定義 / init_schema
  - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
  - features.py                     -- 特徴量ユーティリティの公開
  - stats.py                        -- zscore_normalize 等の統計ユーティリティ
  - calendar_management.py          -- market_calendar 関連ユーティリティ
  - quality.py                      -- データ品質チェック
  - audit.py                        -- 監査ログ用スキーマ / init_audit_db
  - etl.py                          -- ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - feature_exploration.py          -- 将来リターン、IC、summary、rank
  - factor_research.py              -- momentum/value/volatility 計算
- src/kabusys/strategy/             -- 戦略層（拡張用）
- src/kabusys/execution/            -- 発注/ブローカー連携（拡張用）
- src/kabusys/monitoring/           -- 監視機能（拡張用）

---

## 開発・テスト時の注意

- .env 自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml が基準）。CI・テストで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマ初期化は冪等です。既存 DB に対して再度 init_schema を実行しても安全にスキーマを作成します。
- news_collector は外部ネットワークを使います。テストでは fetch_rss / _urlopen をモックする設計になっています。
- J-Quants API 呼び出しはレート制御とリトライを行いますが、実行には有効なトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 連絡・貢献

README を読んでいただきありがとうございます。バグ報告や機能提案は issue を立ててください。貢献の際はコーディング規約・テストの追加をお願いします。

---

以上が KabuSys の README です。必要であれば、導入手順や具体的な CLI / systemd バッチ化の例、.env.example のテンプレートなどを追記します。どの内容を優先して追加しますか？