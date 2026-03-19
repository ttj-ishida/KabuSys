# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。J-Quants や RSS などから市場データ・ニュースを収集し、DuckDB 上で加工・特徴量生成・シグナル生成までを行えるよう設計されたモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- API レート制御・リトライ・トークン自動更新など実運用向けの堅牢性
- 外部依存を最小化（主要ロジックは標準ライブラリ＋duckdb／defusedxml）

---

## 機能一覧

- 環境設定管理
  - .env ファイル（.env, .env.local）および環境変数の自動読み込み
  - 必須設定の取得とバリデーション（例: JQUANTS_REFRESH_TOKEN）

- データ取得・保存（J-Quants API クライアント）
  - 株価日足（OHLCV）取得・ページネーション対応
  - 財務データ取得（四半期 BS/PL）
  - 市場カレンダー取得
  - API レートリミッティング、リトライ、401 時のトークン自動リフレッシュ

- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェックフレームワークとの連携
  - 日次 ETL の統合実行（市場カレンダー → 株価 → 財務 → 品質チェック）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、スキーマ初期化 API

- 特徴量エンジニアリング（strategy レイヤ）
  - Momentum / Volatility / Value などのファクター計算（research モジュール）
  - Z スコア正規化、ユニバースフィルタリング
  - features テーブルへの冪等アップサート

- シグナル生成
  - features + ai_scores を統合して final_score を算出
  - Bear レジームフィルタ、BUY/SELL の閾値判定、エグジット判定（ストップロス等）
  - signals テーブルへの日次置換保存（冪等）

- ニュース収集
  - RSS の取得・前処理（URL 正規化、トラッキング除去）
  - SSRF 対策・gzip サイズ制限・XML サニタイズ（defusedxml）
  - raw_news / news_symbols への保存（重複除去、記事ID は URL の SHA-256 先頭 32 文字）

- カレンダー管理
  - JPX カレンダーの更新バッチ、営業日判定ユーティリティ（next/prev/get_trading_days 等）

- ユーティリティ
  - 統計ユーティリティ（zscore_normalize、rank、IC 計算等）
  - 監査ログ（audit テーブル群の DDL が含まれる）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションで | 型を使っているため 3.10 を想定する環境も多いですが、最小はプロジェクト要件に合わせてください）
- duckdb が必要
- defusedxml（RSS パーサ保護用）

1. リポジトリをクローン / 配置
   - ソースは `src/` 配下にパッケージとして構成されています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . で依存と共にインストール）

4. 環境変数 / .env ファイルを用意
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API 用パスワード)
     - SLACK_BOT_TOKEN (Slack 通知用 Bot トークン)
     - SLACK_CHANNEL_ID (Slack チャンネル ID)
   - 任意 / デフォルト:
     - KABUSYS_ENV = development | paper_trading | live  (default: development)
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

例（.env）
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

## 使い方（簡易ガイド）

以下は代表的な操作のサンプルコード例です。実行はプロジェクトの仮想環境内で行ってください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイルを指定（デフォルト例）
conn = init_schema("data/kabusys.duckdb")
# これで全テーブルが作成されます（冪等）
```

2) 日次 ETL を実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の生成（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features 上書き件数: {n}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"シグナル総数: {total}")
```

5) RSS ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は有効な銘柄コード集合（extract_stock_codes に渡す）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

注意点:
- これらの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。初回は init_schema() で DB を作成・初期化してください。
- run_daily_etl などは外部 API 呼び出しを行うため、J-Quants トークンなど適切に設定されている必要があります。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1 をセット）

---

## ディレクトリ構成

主要なソースファイル／パッケージ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント + 保存ロジック
      - news_collector.py       — RSS ニュース収集・保存
      - schema.py               — DuckDB スキーマ定義と初期化
      - stats.py                — 統計ユーティリティ（z-score 等）
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py  — カレンダー更新 / 営業日ユーティリティ
      - features.py             — 公開インターフェース（zscore_normalize 再エクスポート）
      - audit.py                — 監査ログ DDL（order/request/execution の監査）
      - ...（その他 data 層モジュール）
    - research/
      - __init__.py
      - factor_research.py      — Momentum/Value/Volatility の計算
      - feature_exploration.py  — forward return / IC / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py  — features テーブル構築（build_features）
      - signal_generator.py     — シグナル生成（generate_signals）
    - execution/                — 発注・実行関連（将来的な実装）
      - __init__.py
    - monitoring/               —監視・アラート（将来的な実装）
      - __init__.py

（上記はこのリポジトリに含まれる主要モジュールの抜粋です。詳細はソースを参照してください。）

---

## 開発上の注意・ベストプラクティス

- DuckDB ファイルはクラウドや共有ファイルストレージに置く場合のロックや同時接続に注意してください。並列ワークロードがある場合は設計に応じた運用が必要です。
- ETL ジョブは差分取得とバックフィルを組み合わせて設計されています。API の後出し修正を吸収するために backfill_days を適切に設定してください。
- 本コードは発注 API（実際の売買）に直接結びつかない設計ですが、実運用で execution レイヤを実装してブローカー連携を行う際は監査ログ・冪等性・エラー状態遷移に細心の注意を払ってください。
- テストや CI では環境変数自動読み込みを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると便利です。

---

## 貢献・ライセンス

このドキュメントはソースコードに基づく概要説明です。実際の運用や拡張、バグ修正の際は各モジュールの docstring とコードを参照してください。ライセンス情報やコントリビュート手順はリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）があればそちらを参照してください。

---

何か追加で README に記載したい操作（例: テストの実行方法、CI の設定、より詳しい環境変数例など）があれば教えてください。README に追記します。