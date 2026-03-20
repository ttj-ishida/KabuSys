# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
J-Quants や RSS 等から市場データ・ニュースを取り込み、DuckDB に保存し、特徴量計算・シグナル生成・発注監査のための基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL（差分更新対応）
- RSS からニュースを収集・前処理し DB に保存、記事 → 銘柄の紐付け
- リサーチ用途のファクター計算（モメンタム・ボラティリティ・バリュー等）および統計ユーティリティ
- 特徴量の正規化／合成（features テーブルへの UPSERT）
- 戦略の最終スコア計算と売買シグナル生成（signals テーブルへ冪等書き込み）
- マーケットカレンダー管理、監査ログ（オーダー／約定のトレーサビリティ）などのデータ基盤機能

設計上のポイント:
- ルックアヘッドバイアスを避けるために「target_date 時点のデータのみ」を使用
- DuckDB を主たる永続化先とし、冪等な INSERT（ON CONFLICT）を採用
- 外部 API 呼び出しは専門モジュールに集約。execution / 発注層には直接依存しない

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション / レート制御 / リトライ / トークン自動更新）
  - pipeline: 日次 ETL（prices, financials, market calendar）と差分更新ロジック
  - schema: DuckDB スキーマ初期化（Raw/Processed/Feature/Execution 層）
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出（SSRF対策・圧縮対応）
  - calendar_management: 営業日判定・next/prev_trading_day・夜間カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー等
- strategy/
  - feature_engineering: 生ファクターを統合・正規化して features テーブルへ保存
  - signal_generator: features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成
- config: 環境変数読み込みと Settings（J-Quants トークン等の管理）
- audit / execution / monitoring（監査・実行・監視用のスキーマ・基盤ロジック）
- research と data のユーティリティを再エクスポートする API

---

## セットアップ手順

前提:
- Python 3.8+（コードは型ヒントで 3.10 等を想定しています）
- DuckDB を利用（Python パッケージ duckdb）
- defusedxml（RSS パースの安全化）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（例）。
   ```
   pip install duckdb defusedxml
   ```
   - 他に標準ライブラリのみで動作する部分が多いですが、実行や ETL を行う際は上記が最低必要です。

3. 環境変数の設定
   - ルートに .env/.env.local を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知に使う場合
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを抑制する場合 1 を設定
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite などを使う場合のパス（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API とサンプル）

以下の例は Python スクリプト内での呼び出し例です。DuckDB のファイルパスや日付は環境に合わせて変更してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル作成＋テーブル作成（":memory:" でメモリ DB ）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants からデータを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（research モジュールで計算した生ファクターを正規化して features に保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date
import duckdb

conn = get_connection("data/kabusys.duckdb")
n_upserted = build_features(conn, target_date=date.today())
print("features upserted:", n_upserted)
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", total_signals)
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを行います（例: 上場銘柄セット）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

7) research のユーティリティ（IC 計算など）
```python
from kabusys.research import calc_forward_returns, calc_ic

# calc_forward_returns(conn, target_date, horizons=[1,5,21])
# calc_ic(factor_records, forward_records, "mom_1m", "fwd_1d")
```

注意点:
- すべての ETL / 書き込み処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの操作は「target_date を指定してその時点の情報だけを使う」設計です（ルックアヘッド防止）。
- 自動 .env 読み込みが不要なテスト環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境設定 / Settings
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - news_collector.py             — RSS 収集・前処理・保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - schema.py                     — DuckDB スキーマ定義と init_schema
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                   — zscore_normalize の再公開インターフェース
    - calendar_management.py        — カレンダー管理・更新ジョブ
    - audit.py                      — 監査ログ（signal_events / order_requests / executions）
    - audit.py (続きで DDL 定義)    — （監査用の DDL とインデックス）
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value の計算
    - feature_exploration.py        — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features テーブル構築
    - signal_generator.py           — final_score 計算と signals 生成
  - execution/                       — 発注関連（空の __init__ 等）
  - monitoring/                      — 監視/メトリクス（未記載の実装がある可能性あり）

（上記はこのコードベースに含まれているモジュールを抜粋して列挙しています）

---

## 追加メモ・運用上の注意

- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ上限、defusedxml による XML 安全処理を行います。
  - API トークン等は .env や OS 環境変数で管理し、リポジトリにコミットしないでください。
- 冪等性:
  - J-Quants から取得したデータは save_* 関数で ON CONFLICT を使って冪等的に保存されます。
- ロギング:
  - settings.log_level によってログレベルを制御します。運用時は INFO 以上、デバッグ時は DEBUG を推奨します。
- テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の自動 .env ロードを無効化できます（ユニットテストで環境依存を排除する際に便利）。
- 実運用:
  - KABUSYS_ENV を `paper_trading` / `live` に設定して運用フェーズを分けてください（コード内で is_live/is_paper/is_dev が参照されます）。

---

必要であれば README に
- インストール用の requirements.txt / poetry / pyproject.toml の例
- よくあるトラブルシューティング（DuckDB のパーミッション、J-Quants のトークン更新方法）
- より詳細な CLI 化・ systemd / Airflow などでのジョブ化手順
を追記できます。どの情報を追加しますか？