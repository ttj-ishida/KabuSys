# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ群（ライブラリ）。  
データ取得・ETL、リサーチ用ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理など、自動売買システムのデータプラットフォームと戦略層の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株（JPX）を対象とした半構造化された自動売買基盤ライブラリです。主要な責務は以下の通りです。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB によるデータ保管（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- 戦略層の特徴量正規化・シグナル生成ロジック
- RSS ベースのニュース収集と記事⇄銘柄紐付け
- カレンダー管理、監査ログ（オーダー/約定トレーサビリティ）用DDL

設計上の特徴：
- ルックアヘッドバイアス回避のため、target_date 時点のデータのみを使用
- DuckDB を用いたローカル永続化（冪等な保存）
- 外部ライブラリへの依存を最小化（ただし DuckDB / defusedxml 等は使用）
- API レート制限やリトライ、SSRF 等のセキュリティ考慮を実装

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークン自動更新・レート制御・保存）
  - schema: DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution 層のDDL）
  - pipeline: 日次差分 ETL（株価・財務・カレンダー）と品質チェック
  - news_collector: RSS 取得・正規化・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー管理、営業日ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
  - features: features 用インターフェース（zscore の再エクスポート）
  - audit: 監査ログ DDL（signal_events / order_requests / executions 等）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターのフィルタ・正規化・features テーブルへの保存
  - signal_generator: features / ai_scores を統合して final_score を計算し signals を生成
- config: .env 自動ロード、環境変数ラッパー（必須キーの検証、デフォルト値）
- execution/, monitoring/: 発注・監視周りの拡張ポイント（モジュール入口あり）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部機能を利用）
- DuckDB を利用できる環境
- J-Quants API のリフレッシュトークン等の環境変数

推奨手順（pip を利用）:

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 開発インストール
   - python -m pip install -e .
   - 必要な依存パッケージ（ピン留めはプロジェクト側で管理すること）
     - duckdb
     - defusedxml
   例:
     - python -m pip install duckdb defusedxml

環境変数:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- 任意／デフォルト
  - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / ... （デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を基点）にある `.env`、`.env.local` が自動で読み込まれます。
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定の参照例（コード内）:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.is_live, ...

サンプル .env（例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本例）

以下は代表的なユースケースと最小限のコード例です。すべて Python スクリプト内で実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ親フォルダを作成しテーブルを作る
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) 特徴量ビルド（features テーブルの更新）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date.today())
print(f"build_features: {n} 銘柄を upsert")
```

4) シグナル生成（signals テーブルの作成）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date.today())
print(f"generate_signals: {count} シグナル作成")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes はテキスト中の4桁コード抽出に使う有効銘柄コードセット
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

ログ設定:
- settings.log_level を参照してロガーのレベルを設定してください（例: logging.basicConfig(level=settings.log_level)）。

注意点:
- 各処理は DuckDB 上のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とします。init_schema を使ってスキーマを作成してください。
- J-Quants API 呼び出しはレート制限／リトライを内包しますが、API キーの権限や quota は別途確認してください。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なファイル構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モジュール入口、今後の実装領域)

各モジュールの役割は「機能一覧」と「概要」を参照してください。

---

## 追加・開発ノート

- 冪等性：DB への保存は多くが ON CONFLICT を使っており再実行に耐えます。
- セキュリティ：news_collector は SSRF 対策、defusedxml による XML 保護、応答サイズチェック等を実装しています。
- テスト：環境変数自動読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- 拡張：execution / monitoring 層は拡張ポイントとして用意されています。ブローカ連携や実取引ロジックはここを実装してください。
- ロギングと監査：audit モジュールに監査用 DDL を含み、シグナル→注文→約定までの追跡をサポートします。

---

## お問い合わせ／貢献

バグ報告・改善提案・プルリクエストはリポジトリの Issue または PR で受け付けてください。ドキュメントの改善も歓迎します。

---

以上。README に不足している具体的な運用手順や環境（CI/CD、運用スクリプト、pyproject・依存管理など）を追加したい場合は、利用方法や運用フローに合わせた情報を提供してください。