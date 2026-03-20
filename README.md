# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリ（研究・データプラットフォーム・戦略生成・実行層の基礎機能群）です。  
本リポジトリは以下を提供します：J-Quants からの市場データ取得・DuckDB スキーマ定義、ETL パイプライン、ファクター計算・特徴量エンジニアリング、シグナル生成、ニュース収集など、戦略開発と本番運用に必要な基盤機能群。

主な設計方針
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DuckDB を用いたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- 冪等性（ON CONFLICT / idempotent 保存）
- ネットワーク安全対策（RSS の SSRF/サイズチェック、API のレート制限・リトライ等）
- 外部依存は最小化（標準ライブラリ中心、必要最小限で duckdb / defusedxml を使用）

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）／必須環境変数取得（settings）
- データ取得・保存（J-Quants API クライアント）
  - 株価日足（OHLCV）取得・保存（ページネーション／トークン自動リフレッシュ／レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
- ETL パイプライン
  - 日次差分 ETL（run_daily_etl）：calendar → prices → financials → 品質チェック
  - 差分取得 / バックフィル / 品質チェック（quality モジュール連携）
- データ処理・統計ユーティリティ
  - Z スコア正規化（クロスセクション）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- ファクター計算（research）
  - Momentum / Volatility / Value 等の定量ファクター計算
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクター統合／ユニバースフィルタ／正規化／features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム検知による BUY 抑制、SELL（エグジット）判定、signals テーブルへ保存
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出（SSRF 対策、サイズ制限、重複排除）
- カレンダー管理（デイリーバッチ／trading day 判定ヘルパ）
- 監査ログ（audit）設計（signal → order → execution のトレーサビリティ用テーブル群）

---

## 必要条件 / 依存パッケージ

- Python 3.9+
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml

（上記以外は標準ライブラリのみを想定しています。プロジェクトをパッケージ化する場合は pyproject.toml 等に依存を記載してください。）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージ化されている場合はプロジェクトルートで:
# pip install -e .
```

---

## 環境変数

本ライブラリは環境変数（または .env/.env.local）で設定を読み込みます。主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

自動 .env ロードを無効化する（テスト等）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の書き方は .env.example を参考にしてください（プロジェクトルートに配置）。

---

## セットアップ手順（最小動作確認）

1. リポジトリをクローン／ソースを配置
2. 仮想環境作成・依存インストール（上記参照）
3. 必要な環境変数を設定（J-Quants トークン等）
   - 簡易：プロジェクトルートに `.env` を作成
4. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

5. 日次 ETL を実行（サンプル）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

---

## 使い方（主要 API 例）

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL（市場カレンダー / 株価 / 財務 の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
print(res.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使用する有効銘柄コードセット
known_codes = {r[0] for r in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 特徴量ビルド（features テーブルへの保存）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの保存）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, date(2024, 1, 31))
print(f"total signals written: {total}")
```

- Z スコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "atr_pct"])
```

注意事項
- 上記関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スクリプトやジョブからは接続を使い回してください。
- run_daily_etl 等はネットワークアクセス（J-Quants）を行います。環境変数に正しいトークンがあることを確認してください。
- 本リポジトリは戦略ロジックやブローカー接続の一部を含みますが、本番運用前に入念な検証を行ってください（特に execution / order 発行周り）。

---

## ディレクトリ構成

リポジトリ（src 配下）のおおまかな構成は以下の通りです：

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py           — J-Quants API クライアント（取得・保存）
      - news_collector.py           — RSS ニュース収集・保存
      - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
      - schema.py                   — DuckDB スキーマ定義 / init_schema
      - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
      - features.py                 — features インターフェース（再エクスポート）
      - calendar_management.py      — 市場カレンダー管理 / 営業日判定
      - audit.py                    — 監査ログ DDL（signal/order/execution トレーサビリティ）
      - (その他: quality.py などが想定される)
    - research/
      - __init__.py
      - factor_research.py          — ファクター計算 (momentum/value/volatility)
      - feature_exploration.py      — 将来リターン / IC / 統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py      — 特徴量構築・features 保存
      - signal_generator.py         — final_score 計算・signals 生成
    - execution/                     — 発注・約定関連（実装はこのリポジトリのバージョンに依存）
    - monitoring/                    — 監視・アラート関連（実装想定）
- pyproject.toml (プロジェクトルートに存在する場合、.env 自動読込でルート検出に使用)

（実際のファイルはリポジトリのバージョンによって変動します。上記は現状ソースコードに基づく主要ファイル一覧です。）

---

## 開発／テストのヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB のインメモリ DB を使って高速にユニットテストを回せます： init_schema(":memory:")
- ネットワーク依存部分（jquants_client.fetch_* / news_collector.fetch_rss）はモック注入が想定されています。テスト時は id_token を外部注入したり、_urlopen / _request をモンキーパッチしてください。

---

以上です。追加で README に含めたい運用手順（CI ジョブ例、cron / Airflow のサンプル、.env.example の雛形など）があれば指示ください。必要に応じて README に追記して Markdown 形式で出力します。