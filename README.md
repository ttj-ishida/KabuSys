# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ・スキーマなど、戦略開発から運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資／自動売買を想定したモジュール群です。主な設計指針は以下の通りです。

- データの取得・保存は冪等（idempotent）に実行（DuckDB へ ON CONFLICT/UPSERT を使用）。
- ルックアヘッドバイアスを防ぐため、常に target_date 時点またはそれ以前のデータのみを利用。
- J-Quants API のレート制限・リトライ・トークンリフレッシュを考慮したクライアント実装。
- RSS からのニュース収集は SSRF や XML 攻撃対策（defusedxml 等）を実装。
- 戦略層は特徴量（features）を利用して最終スコアを計算し、BUY/SELL シグナルを生成（冪等処理）。

---

## 主な機能一覧

- データ取得 / クライアント
  - J-Quants API クライアント（株価/財務/カレンダー取得、トークン更新、レート制御、リトライ）
- データモデル / スキーマ
  - DuckDB 用のスキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS 収集、前処理、raw_news 保存、銘柄抽出（run_news_collection）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量・シグナル生成
  - クロスセクション Z スコア正規化（zscore_normalize）
  - features テーブル作成（build_features）
  - final_score 計算および BUY/SELL シグナル生成（generate_signals）
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- 監査ログ（audit）
  - シグナル → 発注 → 約定までのトレース可能な監査テーブル群

---

## 必要要件

- Python 3.10 以上（型注釈に `X | None` を使用）
- 主要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS 等）

（実運用では kabuステーション API への接続や Slack 連携も行うため、各種クレデンシャルが必要です）

---

## セットアップ手順

1. リポジトリをクローン／配置（プロジェクトルートに `pyproject.toml` や `.git` がある想定）。
2. Python 仮想環境の作成と有効化（例: venv / poetry 等）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
3. 依存パッケージをインストール
   - 例（最小）:
     - pip install duckdb defusedxml
   - 開発・追加パッケージがある場合は requirements.txt / pyproject.toml を参照してインストールしてください。
4. パッケージをインストール（任意）
   - pip install -e .
5. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` から自動読み込みされます（優先順位: OS環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（アプリ起動時に参照されるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

例: `.env` の最小例
```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

> セキュリティ: トークン類は漏洩しないように管理してください。バージョン管理には絶対に含めないでください。

---

## 使い方

以下は基本的な利用例です。実行は Python スクリプトまたは対話シェルから行えます。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー、株価、財務の差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効なコード集合（例: データベースから取得した価格テーブルのコード一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ向け）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各関数は DuckDB の接続オブジェクトを受け取ります。初回は schema.init_schema() で DB を作成してください。
- run_daily_etl は内部で J-Quants クライアントを呼び出します。適切な JQUANTS_REFRESH_TOKEN が必要です。
- 本ライブラリは発注実行（ブローカー接続）と直接結合しない設計ですが、execution 層や監査テーブルを持つため、ブローカー連携コードを別途実装して統合できます。

---

## 環境変数一覧（要約）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- オプション（デフォルトあり）
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- 自動 .env 読み込みを無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（概観）

以下は主要モジュールとその役割の一覧です（パッケージルートは `src/kabusys`）：

- kabusys/
  - __init__.py (パッケージエクスポート)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存関数付き)
    - news_collector.py (RSS収集・保存・銘柄抽出)
    - schema.py (DuckDB スキーマ定義・初期化)
    - stats.py (zscore_normalize 等統計ユーティリティ)
    - pipeline.py (ETL パイプライン：run_daily_etl 等)
    - calendar_management.py (市場カレンダー管理)
    - audit.py (監査ログ用スキーマ)
    - features.py (インターフェース再エクスポート)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility の計算)
    - feature_exploration.py (forward returns, IC, summary 等)
  - strategy/
    - __init__.py (build_features, generate_signals をエクスポート)
    - feature_engineering.py (features テーブル作成処理)
    - signal_generator.py (final_score 計算・signals 生成)
  - execution/
    - __init__.py (発注処理は別実装を想定)
  - monitoring/ (README の冒頭 __all__ に含まれているが、実装は別途)
  - その他ドキュメント（DataPlatform.md, StrategyModel.md 等を参照する設計になっています）

---

## 開発・テスト

- 単体関数は DuckDB のインメモリ接続 (`:memory:`) を使ってテストできます（schema.get_connection / init_schema を活用）。
- ネットワークを伴う J-Quants 周りは ID トークンをモックしたり、jquants_client._request をテスト用に差し替えることを推奨します。
- news_collector._urlopen 等はユニットテストでモックできる設計になっています。

---

## 注意事項 / 運用上のポイント

- 実運用で「live」モードを使う場合は十分な保守・監視（Slack 通知／ログ収集）を行ってください。
- トークンやシークレットは安全な Vault に保存し、環境変数は CI/CD・デプロイ時に注入してください。
- DuckDB のファイル配置、バックアップ、権限管理を適切に行ってください（データは資産です）。
- 発注・約定処理は証券会社 API と結合する実装が別途必要です（本パッケージは主にデータ処理・シグナル生成を担います）。

---

必要に応じて、サンプルスクリプトや CI 用のワークフロー、さらに詳しい API リファレンス（各関数の引数説明／戻り値）を別途作成できます。どの部分を優先して追加ドキュメント化するか指示をください。