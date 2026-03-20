# KabuSys

日本株向けの自動売買フレームワーク（ライブラリ）です。  
データ収集（J-Quants/API）、DuckDB を用いたデータプラットフォーム、ファクター計算、特徴量生成、シグナル生成、ニュース収集、ETL パイプライン、監査ログ等の主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の層を備えた日本株自動売買の基盤ライブラリです。

- データ取得（J-Quants API を通じた株価・財務・市場カレンダー）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコアの統合・BUY/SELL 判定）
- ニュース収集（RSS の取得・前処理・銘柄紐付け）
- 監査・トレーサビリティ（発注 → 約定の追跡ログ）

設計方針は「ルックアヘッドバイアス防止」「冪等性（idempotent）」「外部 API への過度な依存回避」「テスト容易性」を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次差分 ETL（prices / financials / calendar）および総合 run_daily_etl
  - schema: DuckDB スキーマ初期化（init_schema）
  - news_collector: RSS 取得・記事保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: zscore_normalize（クロスセクション標準化）
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: forward returns / IC / factor summary
- strategy
  - feature_engineering.build_features: ファクター正規化・features テーブルへの保存
  - signal_generator.generate_signals: features + ai_scores 統合 → BUY/SELL シグナル作成
- execution / monitoring / audit
  - スキーマ内に Execution / Audit 関連テーブルを定義（orders, trades, executions, signal_events 等）
- config
  - 環境変数ベースの設定管理（.env 自動ロード、必須チェック）

---

## 必要条件 / 依存ライブラリ

最小限で以下を想定しています（プロジェクトに requirements.txt がある場合はそちらを利用してください）。

- Python 3.9+
- duckdb
- defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または
pip install -e .
```

---

## 環境変数（設定）

settings（kabusys.config.Settings）で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）に置かれた `.env` と `.env.local` を自動で読み込みます。ただしテストなどで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. 環境変数を設定（.env を作成）
   - 例: `.env` に必須トークン等を保存
5. DuckDB スキーマ初期化

例:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

これで必要なテーブルがすべて作成されます（冪等）。

---

## 使い方（主要な操作のサンプル）

以下はライブラリ呼び出しの基本例です。実際の運用ではロガー設定や例外ハンドリングを追加してください。

- DuckDB 初期化 / 接続

```python
from kabusys.data.schema import init_schema, get_connection

# 初期化（ファイル DB）
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続（スキーマ初期化は行わない）
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ保存）

```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2024, 1, 31))
print(f"upserted features: {n}")
```

- シグナル生成（signals テーブルへ保存）

```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2024, 1, 31))
print(f"generated signals: {count}")
```

- ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使う有効なコードの集合
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

- 研究用ユーティリティ（IC 計算など）

```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
# 各関数は DuckDB 接続やレコードリストを受け取って統計量を返します
```

---

## 実運用向け注意点

- J-Quants API 利用にはレート制限（120 req/min）や認証トークンの管理が必要です。本クライアントはレートリミットとリトライを考慮していますが、運用時には API 利用規約に従ってください。
- DuckDB ファイルはバックアップを検討してください。監査ログは削除しないことが想定されています。
- 本ライブラリは look-ahead bias を防ぐため、各処理は target_date 時点での利用可能データのみを参照する設計になっています。外部からの呼び出しでも同原則を守るよう注意してください。
- news_collector は外部 URL を取得します。SSRF 等の対策は実装されていますが、運用上のセキュリティ設定は環境に応じて行ってください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の概略ツリー（src/kabusys）です。実際のリポジトリに合わせて補完してください。

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント（fetch/save）
      - news_collector.py        — RSS 取得・記事保存・銘柄抽出
      - schema.py                — DuckDB スキーマ定義 / init_schema
      - pipeline.py              — ETL パイプライン（run_daily_etl 等）
      - stats.py                 — zscore_normalize 等統計ユーティリティ
      - calendar_management.py   — 営業日ロジック・calendar_update_job
      - features.py              — 公開インターフェース（zscore_normalize）
      - audit.py                 — 監査ログテーブル DDL（signal_events / order_requests 等）
      - execution/               — （発注関連モジュール置場、空 __init__あり）
    - research/
      - __init__.py
      - factor_research.py       — calc_momentum / calc_volatility / calc_value
      - feature_exploration.py   — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py   — build_features
      - signal_generator.py      — generate_signals
    - execution/                  — 実行層（発注ラッパー等、将来的な実装）
    - monitoring/                 — 監視・通知用コード（Slack 連携など、場所あり）

---

## ライセンス・貢献

この README はコードベースに合わせた概要ドキュメントです。実運用・商用利用・APIキー管理等は各自の責任で行ってください。貢献やバグ報告はリポジトリの ISSUE / PR フローに従ってください。

---

もし README に追加してほしい具体的な情報（例: CI / テスト手順、詳細な環境変数の例、.env.example、実行スクリプト CLI 例、サンプルデータの初期ロード手順 等）があれば教えてください。必要に応じて追記・テンプレート化します。