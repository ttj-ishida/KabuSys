# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（ミニマム実装）

このリポジトリは、J-Quants などから市場データを取得して DuckDB に蓄積し、
ファクター計算 → 特徴量正規化 → シグナル生成 → 実行（発注）に繋げるための
データプラットフォーム＋戦略モジュール群を提供します。
（発注ブリッジや外部サービス連携の一部は別モジュール／実装を想定）

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を中心に冪等操作（ON CONFLICT 等）で安全にデータ保存
- ネットワークや API に対して堅牢なリトライ・レート制御・SSRF対策を実装
- research（因子探索）と production（ETL/戦略）を分離

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
    - レート制限・再試行・トークン自動更新を備えた HTTP 層
  - raw データの DuckDB への冪等保存（save_* 関数）
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義と初期化（init_schema）
  - テーブル層: Raw / Processed / Feature / Execution
- ニュース収集（data.news_collector）
  - RSS フィードの取得・前処理・重複排除・記事→銘柄紐付け（SSRF / XML 脆弱性対策あり）
- 研究用（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）やファクターサマリー
- 戦略層（strategy）
  - 特徴量構築（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
    - 複数コンポーネント（momentum/value/volatility/liquidity/news）を統合
    - Bear レジーム抑制、売り（exit）ロジック含む
- ユーティリティ
  - 統計ユーティリティ（data.stats: zscore_normalize）
  - 環境設定ロード（config.Settings、.env 自動ロード機能）

---

## 前提 / 必要環境

- Python 3.10 以上（パイプライン内で `X | None` 型注釈を使用）
- pip（パッケージ管理）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）

必要パッケージのインストール例:
```
python -m pip install duckdb defusedxml
```

（本リポジトリに pyproject.toml / requirements.txt がない場合は適宜管理してください）

---

## 環境変数／設定

設定は環境変数またはルートの `.env` / `.env.local` から自動読み込みされます。
自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション等の発注 API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

任意／デフォルト:
- KABUSYS_ENV           : `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視 DB）パス（デフォルト: data/monitoring.db）

.env の記述例（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル実行の最小手順）

1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   - 追加で必要なパッケージがあれば適宜インストールしてください（logging は標準）。
4. 必要な環境変数を `.env` に設定（上記参照）
5. DuckDB スキーマを初期化
   - Python REPL / スクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - これにより `data/` ディレクトリがなければ作成され、必要なテーブルがすべて作成されます。

---

## 使い方（主要ワークフロー例）

以下は基本的なバッチワークフローのサンプルコード例です。

1) 日次 ETL（市場カレンダー / 株価 / 財務 の差分取得）
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（feature テーブル作成）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

3) シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {total_signals}")
```

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes: 銘柄リスト（set of "7203", ...）があれば紐付けが行われる
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

5) カレンダー更新ジョブ（夜間）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- jquants_client は内部でトークン取得（get_id_token）を行います。`JQUANTS_REFRESH_TOKEN` を環境変数に設定してください。
- generate_signals / build_features は target_date を基準に過去データのみ参照します（ルックアヘッド回避）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント（fetch/save）
    - news_collector.py                 -- RSS 収集・保存・紐付け
    - schema.py                         -- DuckDB スキーマ定義・init_schema
    - stats.py                          -- zscore_normalize 等統計ユーティリティ
    - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
    - features.py                       -- zscore_normalize を再エクスポート
    - calendar_management.py            -- market_calendar 管理 / 営業日判定
    - audit.py                          -- 監査ログ DDL（signal_events / order_requests / executions）
    - audit.py (続き...)                -- （監査用 DDL/インデックス）
  - research/
    - __init__.py
    - factor_research.py                -- momentum/volatility/value の計算
    - feature_exploration.py            -- 将来リターン / IC / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py            -- features の構築（build_features）
    - signal_generator.py               -- signals の生成（generate_signals）
  - execution/                          -- 発注関連（空パッケージ／実装位置）
  - monitoring/                         -- 監視系（空パッケージ／実装位置）

（実際のソースは src/kabusys 以下に分割されています。上記は概要です）

---

## 主要 API（参照用）

- data.schema.init_schema(db_path)
  - DuckDB を初期化し接続を返す
- data.schema.get_connection(db_path)
  - 既存 DB へ接続
- data.pipeline.run_daily_etl(conn, target_date=..., id_token=..., run_quality_checks=True)
  - 日次 ETL を実行（ETLResult を返す）
- data.jquants_client.fetch_* / save_*（fetch_daily_quotes 等）
  - API 取得及び保存
- data.news_collector.fetch_rss(url, source) / save_raw_news(conn, articles)
  - RSS 取得・保存
- strategy.build_features(conn, target_date)
  - features テーブルを構築（Z スコア正規化・ユニバースフィルタ含む）
- strategy.generate_signals(conn, target_date, threshold=..., weights=...)
  - signals テーブルへ BUY/SELL を生成

---

## 運用上の注意

- 環境変数（トークン等）は厳重に管理してください。リフレッシュトークンは長期間有効な機密情報です。
- DuckDB ファイルは定期的にバックアップしてください。
- API レート制限（J-Quants: 120 req/min）に注意してください。jquants_client は内部で簡易レート制御を行いますが、大量バッチ実行では注意が必要です。
- production（ライブ運用）時は KABUSYS_ENV=live に設定し、紙トレード/本番の分離を行ってください（is_live / is_paper プロパティを利用）。

---

## ライセンス / 貢献

本リポジトリにライセンス情報や貢献ガイドがない場合は、運用チームで方針を決定してください。Pull Request や Issue を通じて改善・拡張を歓迎します。

---

README は以上です。必要であれば、セットアップスクリプト例・CI 設定・より詳細な運用手順（バックテスト手順、Slack 通知フロー、kabu API 発注実装ガイド等）を追加します。どの情報を優先して追加しましょうか？