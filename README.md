# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（リサーチ／データ基盤／戦略／実行層のユーティリティ群）。  
このリポジトリはデータ収集（J-Quants）、DuckDB スキーマ、特徴量生成、シグナル生成、ニュース収集、カレンダー管理などの主要コンポーネントを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定したモジュール群を提供します。

- Data（取得・ETL）
  - J-Quants API クライアント（差分取得・ページネーション・トークン管理・保存）
  - DuckDB スキーマ定義と初期化
  - ETL パイプライン（差分取得、保存、品質チェック）
  - RSS ニュース収集・前処理・銘柄抽出
  - マーケットカレンダー（営業日管理）
- Research（ファクター計算 / 特徴量解析）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC・統計サマリー等の探索ツール
- Strategy（特徴量の正規化・シグナル生成）
  - feature_engineering: 生ファクターを正規化して features テーブルへ保存
  - signal_generator: features / ai_scores を統合して BUY/SELL シグナルを生成
- Execution / Monitoring（発注・モニタリング）用の土台（スキーマ・型定義など）

設計上の注力点:
- ETL/収集は冪等（ON CONFLICT / トランザクション）で実装
- Look-ahead bias を防ぐため日付単位で過去データのみを使用
- ネットワーク堅牢性（レート制限・リトライ・トークン自動更新）
- SSRF・XML攻撃対策（ニュース収集）

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足・財務データ・マーケットカレンダー取得（ページネーション対応）
  - レートリミット遵守・リトライ・401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar など）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数
- ETL パイプライン
  - run_daily_etl によるカレンダー・株価・財務の差分取得 + 品質チェック
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Spearman）・統計サマリー
- 特徴量エンジニアリング
  - Zスコア正規化・ユニバースフィルタ（最低株価・平均売買代金）・features テーブルへのアップサート
- シグナル生成
  - 複数コンポーネント（momentum/value/volatility/liquidity/news）を重み付き統合
  - Bear レジーム検出による BUY 抑制、エグジット判定（ストップロス等）
  - signals テーブルへの冪等書き込み
- ニュース収集
  - RSS フィードの取得・XML 安全パース・URL 正規化・記事ID生成・銘柄抽出・raw_news への保存
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、期間内営業日列挙、夜間カレンダー更新ジョブ

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションに一部 Union 表現等を使用。ご利用の環境に合わせて調整してください）
- DuckDB を使います（Python パッケージとして duckdb をインストール）

推奨パッケージ（最低限）:
- duckdb
- defusedxml

例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# プロジェクトを editable install する場合（setup 配下がある想定）
python -m pip install -e .
```

環境変数（必須 / 任意）:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD: kabu ステーション API のパスワード（execution 層で使用）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- 任意 / デフォルトあり
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動読み込みします。
  - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: `.env` の構文パーサはクォート・コメント・export 形式に対応しています。

---

## 使い方（主要ユースケース）

以下は最小限の利用例です。DuckDB を初期化し、ETL → 特徴量 → シグナル生成の流れを示します。

1) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema

# ファイル DB を利用
conn = init_schema("data/kabusys.duckdb")
# あるいはインメモリ
# conn = init_schema(":memory:")
```

2) 日次 ETL を実行する（J-Quants のトークンは環境変数から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

3) 特徴量（features）を構築する
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date.today())
print(f"features upserted: {n}")
```

4) シグナルを生成する
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: 全上場銘柄）
saved = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(saved)
```

6) マーケットカレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

補足:
- J-Quants API 呼び出しは内部でレート制限とリトライを行います。
- ETL / 保存処理は基本的に冪等（ON CONFLICT / トランザクション）です。
- 実行環境（paper_trading / live）に応じた安全ガードは呼び出し側で管理してください。

---

## 環境変数の例（.env）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxx

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイルとモジュール）

以下は src/kabusys 以下の主要ファイル群です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得/保存）
    - schema.py                      # DuckDB スキーマ定義と init_schema()
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - stats.py                       # zscore_normalize 等の統計ユーティリティ
    - features.py                    # zscore_normalize の公開再エクスポート
    - news_collector.py              # RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py         # マーケットカレンダー管理／更新ジョブ
    - audit.py                       # 監査ログ用スキーマ（signal_events 等）
    - pipeline.py                    # （ETL のメインロジック）
  - research/
    - __init__.py
    - factor_research.py             # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py         # 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         # features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py            # final_score 計算・BUY/SELL 生成
  - execution/                        # 実行層（発注）用の名前空間（今後拡張）
  - monitoring/                       # モニタリング関連（今後拡張）

ドキュメント参照:
- 各モジュールの docstring に設計方針・フロー・参照仕様（StrategyModel.md, DataPlatform.md 等）があります。

---

## 開発／テスト時のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を呼ぶだけで必要なテーブル・インデックスを作成します。テストでは ":memory:" を使うと便利です。
- news_collector は外部ネットワークに依存するため、ユニットテストでは fetch_rss / _urlopen をモックしてください。
- jquants_client のネットワーク呼び出しは rate limiter とトークンキャッシュを利用します。統合テストで大量リクエストを投げないようご注意ください。

---

## ライセンス / 貢献

（このテンプレートではライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。）

貢献については pull request / issue を通じてお願いします。コード内の docstring に設計意図が多く記載されていますので、変更の際は関連する設計ドキュメント（StrategyModel.md / DataPlatform.md 等）と整合性を保ってください。

---

以上。必要であれば README に具体的な CLI 実行例、CI 設定例、より詳細なテーブルスキーマの説明、サンプル .env.example を追加できます。どの情報を追加しますか？