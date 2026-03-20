# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査用スキーマ等を提供）。

このリポジトリはモジュール化された内部ライブラリ群で構成されており、DuckDB を用いたデータレイヤー、J-Quants API からのデータ取得、戦略側の特徴量生成・シグナル化ロジック、ニュース収集や監査ログのためのスキーマが含まれます。

## 主な特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得
  - API レート制御（固定間隔スロットリング）、再試行（指数バックオフ）、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT / upsert）を実装
- データスキーマ
  - Raw / Processed / Feature / Execution 層を分離した DuckDB スキーマ定義（init_schema）
  - 監査用テーブル群（signal_events / order_requests / executions 等）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを順次実行
  - 差分更新・バックフィル機能
- 研究（research）
  - ファクター算出（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）やファクターサマリ等の統計ユーティリティ
- 特徴量エンジニアリング・戦略
  - features テーブルへの Z スコア正規化・クリップ（build_features）
  - 正規化済みファクターと AI スコアを統合して final_score を計算、BUY/SELL シグナルを生成（generate_signals）
  - Bear レジーム抑制、エグジット（ストップロス / スコア低下）判定
- ニュース収集
  - RSS フィード取得（gzip 対応）、URL 正規化、記事ID 生成、raw_news への冪等保存
  - SSRF 対策、受信サイズ上限、XML の安全パース（defusedxml）
  - 記事から銘柄コード抽出（known_codes を用いたフィルタ）
- カレンダー管理
  - market_calendar 更新ジョブ、営業日判定・次/前営業日取得、期間内営業日リスト取得
- 共通ユーティリティ
  - 環境変数管理（.env の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 設定ラッパー（settings）で必須トークン等を一元管理

---

## 必要条件（Prerequisites）
- Python 3.10 以上（型注釈に `X | None` などの構文を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）
- 標準ライブラリ（urllib, logging, datetime, etc.）

（パッケージ管理が整っている場合は pyproject.toml / requirements.txt を参照してください。無ければ下記のように個別にインストールします）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ配布用設定があれば:
# pip install -e .
```

---

## 環境変数（必須 / 主要）
以下はコード内で参照される主な環境変数です。プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（読み込み順: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（execution 層利用時）
- SLACK_BOT_TOKEN       : Slack へ通知する場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV : 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL   : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : SQLite（監視用途等）パス（デフォルト `data/monitoring.db`）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要なパッケージをインストール（例: duckdb, defusedxml）
4. `.env` を作成して必須環境変数を設定
5. DuckDB スキーマを初期化

サンプルコマンド:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 環境変数を .env に設定 (上記参照)

# Python REPL やスクリプトで DB スキーマを初期化
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("initialized:", conn)
PY
```

---

## 使い方（主要 API のサンプル）

- DuckDB 接続とスキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
# 初回: init_schema でテーブル作成
conn = init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date.today())
print("features upserted:", n)
```

- シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", count)
```

- ニュース収集ジョブ（RSS → raw_news, news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は有効な銘柄コードのセット（例: DB から取得）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 設計上の注意・ポイント
- ルックアヘッドバイアス対策: 戻り値やテーブル更新のタイミングで「target_date 時点で入手可能なデータのみ」を使う設計に配慮しています（ETL / features / signals の各処理を参照）。
- 冪等性: API 取得 → DB 保存は ON CONFLICT / upsert を使い冪等に保存します。ETL は差分取得を基本とします。
- セキュリティ・堅牢性:
  - ニュース収集で SSRF 対策、受信サイズ上限、XML の安全パースを実施
  - J-Quants クライアントはレート制御とリトライ（401 の場合はトークン自動更新）を実装
- テスト容易性:
  - config の自動 .env 読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - jquants_client の _urlopen や _get_cached_token はテスト時に差し替え可能に設計

---

## ディレクトリ構成（主要ファイル）
（実際のツリーは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py       — RSS ニュース収集・前処理・DB 保存
    - schema.py               — DuckDB スキーマ定義と初期化（init_schema）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — データ統計ユーティリティの公開インターフェース
    - calendar_management.py  — マーケットカレンダーの管理 / 更新ジョブ
    - audit.py                — 監査ログ（signal_events / order_requests / executions）
    - stats.py                — z-score など統計ユーティリティ
    - quality.py?             — （品質チェックモジュール。pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py  — 将来リターン、IC、サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成処理（正規化・フィルタ）
    - signal_generator.py     — final_score 計算、BUY/SELL シグナル生成
  - execution/                — 発注 / ブローカー連携（パッケージ化済）
  - monitoring/               — 監視・メトリクス（別モジュールで実装想定）

（上記は主要モジュールの抜粋です。細かな補助モジュールやユーティリティが他にも含まれます。）

---

## よくある操作例 / ワークフロー
1. 初回セットアップ
   - .env を設定、依存パッケージをインストール
   - init_schema() で DuckDB スキーマを作成
2. 日次バッチ（夜間）
   - run_daily_etl() を cron / scheduler で実行してデータを更新
   - calendar_update_job() をスケジュールして market_calendar を最新化
3. 特徴量・シグナル生成（戦略バッチ）
   - build_features() → generate_signals() を実行
   - 生成された signals を execution 層へ渡して注文作成（別プロセス / サービス）
4. ニュース収集
   - run_news_collection() を定期実行、raw_news に保存して銘柄紐付け

---

## ライセンス / 責任範囲
このライブラリは日本株の自動売買システム構築のための基盤を提供しますが、実際の資金運用やブローカー API との接続（注文送信・リスク管理・運用監視）は運用者が十分に検証した上で実装・運用してください。取引に伴うリスク・法令順守は利用者の責任です。

---

README の内容やサンプルは開発中のコードを基に作成しています。実際の導入時は pyproject.toml / requirements.txt、.env.example、DataSchema.md / StrategyModel.md などの設計ドキュメントを併せて参照してください。質問があれば、特定のモジュールや API の使い方、サンプルコード（より詳しい実行例）を追加で出力します。