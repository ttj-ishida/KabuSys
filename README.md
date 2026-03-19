# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義などを含むモジュール群です。

主な目的は「研究（research）で得たファクターを生産環境で再現可能に処理し、戦略シグナルを生成して発注層に受け渡す」ことです。ルックアヘッドバイアス防止・冪等性・トレーサビリティを重視して設計されています。

---

## 機能一覧

- 環境変数設定の自動読み込み（`.env`, `.env.local`、優先順位: OS > .env.local > .env）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション・レートリミット・リトライ・トークン自動更新対応）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックフレームワーク）
- 特徴量計算（momentum / volatility / value など）
- 特徴量の正規化（Zスコア）
- シグナル生成（ファクター + AI スコアの統合、Buy/Sell 判定、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS、SSRF/サイズ制限/トラッキング除去/記事IDのハッシュ化、銘柄抽出）
- マーケットカレンダー管理（営業日判定、前後営業日、期間内営業日リスト）
- 監査（audit）スキーマ — シグナルから約定までのトレーサビリティ用テーブル群
- 汎用統計ユーティリティ（z-score 正規化、IC 計算など）
- 開発・運用サポート機能（ログレベル切替、環境切替: development/paper_trading/live）

---

## 必要条件

- Python 3.10 以上（型ヒントの union 演算子 `X | Y` を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用には J-Quants のリフレッシュトークン

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# 開発環境ならプロジェクト配下で
python -m pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数 / 設定

`kabusys.config.Settings` で参照する主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (省略時: data/kabusys.duckdb)
  - SQLITE_PATH (省略時: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (development / paper_trading / live) デフォルト: development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO

自動 `.env` ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の読み込み優先順位:
- OS 環境変数 > .env.local > .env

---

## セットアップ手順（最小手順）

1. Python 3.10+ を用意する
2. 必要な Python パッケージをインストール
   ```bash
   python -m pip install duckdb defusedxml
   # 任意でプロジェクトを editable install
   python -m pip install -e .
   ```
3. 環境変数を設定（例: .env ファイルをプロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
4. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（主要なユースケース例）

以下は簡単な Python スニペット例です。実行はプロジェクトルートで行ってください。

- DuckDB 初期化（上記と同じ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals written: {count}")
conn.close()
```

- RSS ニュース収集（既知銘柄セットを使って銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- カレンダー夜間ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
conn.close()
```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。`init_schema()` はスキーマ作成済みの接続を返し、`get_connection()` は既存 DB への接続を返します。
- ETL / データ保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識した実装です。

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys/` 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / retry / rate limit）
    - schema.py
      - DuckDB スキーマ定義と init_schema, get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - calendar_management.py
      - market_calendar 管理、営業日ロジック
    - features.py
      - zscore_normalize の公開ラッパ
    - stats.py
      - zscore_normalize 実装など統計ユーティリティ
    - audit.py
      - 監査ログ用スキーマ（signal_events, order_requests, executions）
    - pipeline.py, audit など
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（ユニバースフィルタ、正規化、features テーブルへの upsert）
    - signal_generator.py
      - generate_signals（final_score 計算、BUY/SELL 生産、signals テーブルへの upsert）
  - execution/
    - __init__.py
    - （発注・注文管理・ブローカー連携はここに実装）
  - monitoring/
    - （モニタリング / Slack 通知などのモジュールを想定）
  - research/（上記）
  - その他モジュール群（quality チェック等は pipeline と連携）

---

## 設計上の注意点・運用上の注意

- ルックアヘッドバイアス回避:
  - ファクター計算・シグナル生成は target_date 時点のデータのみを使用するよう設計されています。
  - J-Quants データは fetched_at を UTC で保存し、いつデータを取得したかトレース可能です。
- 冪等性:
  - DB への保存は ON CONFLICT を使用することで再実行可能な設計です。
- セキュリティ:
  - News Collector は SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）を行っています。
- テスト:
  - 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- 本番切替:
  - KABUSYS_ENV を `paper_trading` / `live` に変更することで挙動を切り替えます（運用ルールに従ってください）。

---

## 参考・今後の拡張案

- execution 層のブローカー接続（kabuステーションやその他ブローカーAPI）実装
- リスク管理 / ポートフォリオ最適化モジュール
- AI スコアリングを実行する外部サービスとの連携
- 監視ダッシュボード・アラート連携（Slack 通知実装）

---

以上が KabuSys コードベースの README.md（日本語）です。  
必要であれば、導入手順の自動化スクリプト例やより詳細な API リファレンス（関数ごとの引数/戻り値・例）も作成できます。どの情報を追加しますか？