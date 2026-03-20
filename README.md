# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・実行レイヤー向けスキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ／財務データ取得と DuckDB への永続化（冪等性対応）
- Price / Financial / News の ETL（差分更新・バックフィル）
- 研究（research）で計算した生ファクターを正規化して特徴量テーブルを作る機能
- 特徴量 + AI スコアを統合したシグナル生成ロジック（BUY/SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・XML脆弱性対策）
- データスキーマ（DuckDB）と監査テーブルの初期化ユーティリティ

設計方針として、ルックアヘッドバイアス回避、冪等性、外部依存の最小化（標準ライブラリ + 最小限のパッケージ）、ネットワークリスク対策（レート制御・SSRF対策・XML 安全パーサ）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からのデータ取得（ページネーション・リトライ・トークン自動更新）
  - pipeline: 差分ETL（prices, financials, calendar）、日次 ETL 統合 run_daily_etl
  - schema: DuckDB スキーマ定義と init_schema（テーブル作成）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - calendar_management: 営業日判定・next/prev_trading_day 等の補助
  - stats: zscore_normalize 等の共通統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）やファクター統計
- strategy/
  - feature_engineering.build_features: 生ファクターの統合・正規化・features テーブルへのアップサート
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL を生成・signals テーブルへ保存
- execution / monitoring / audit: 実行・監視・監査用のスキーマ・プレースホルダ（実装の補助）

---

## セットアップ手順

前提: Python 3.9+ を想定（typing 機能を多用）。DuckDB を使用します。

1. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell/cmd により異なる)
   ```

3. 必要パッケージをインストール
   最低限の依存:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクト配布用に setup.py/pyproject.toml があれば `pip install -e .` を推奨）

4. 環境変数 (.env) を用意
   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただしテスト時などに無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（実行層を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル
   （その他オプション）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: 監視 DB のパス
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ作成）

DuckDB のスキーマを作成するには `kabusys.data.schema.init_schema` を使います。

例: ファイルベース DB を初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH に依存（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

テストや一時実行ではインメモリ DB を使えます:
```python
conn = init_schema(":memory:")
```

---

## 使い方（代表的なワークフロー）

以下はライブラリの主要な関数を使った典型的な流れの例です。

1) 日次 ETL を実行してデータを取得・保存する
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量を構築（研究モジュールで算出した生ファクターを正規化・features テーブルへ保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"upserted features: {n}")
```

3) シグナル生成（features と ai_scores を基に signals テーブルを更新）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

4) ニュース収集ジョブ（RSS から記事取得・保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# known_codes に有効な銘柄コード集合を渡すと本文から銘柄抽出して紐付けを行います
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) research 用ユーティリティ
- calc_forward_returns, calc_ic, factor_summary, rank などは研究用途に便利です。
- zscore_normalize は data.stats に実装済みで再利用可能。

---

## 環境設定の自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## 注意事項 / 運用上のポイント

- J-Quants API はレート制限があります（デフォルト: 120 req/min）。jquants_client は内部でスロットリングと指数バックオフ retry を実装しています。
- token（J-Quants のリフレッシュトークン）は機密情報です。`.env` をバージョン管理に含めないでください。
- KABUSYS_ENV によって開発/ペーパー/本番（live）の挙動を変えられる設計になっています。live 実行時は特に注意してログ・監査を有効にしてください。
- features / signals の処理はルックアヘッドバイアスを避けるため target_date 時点のデータのみで計算する方針です。
- DuckDB のバージョン差や SQL の制限により一部機能（ON DELETE CASCADE 等）はアプリ側で補償する設計になっています。データ削除時の依存関係に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数と settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得/保存ユーティリティ）
  - pipeline.py               — ETL（run_daily_etl 等）
  - schema.py                 — DuckDB スキーマ定義と init_schema/get_connection
  - news_collector.py         — RSS 収集・前処理・保存・銘柄抽出
  - calendar_management.py    — 営業日判定・カレンダー更新ジョブ
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - features.py               — zscore_normalize の再エクスポート
  - audit.py                  — 監査ログ用スキーマ
- research/
  - __init__.py
  - factor_research.py        — momentum/value/volatility 等のファクター計算
  - feature_exploration.py    — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py    — build_features
  - signal_generator.py       — generate_signals
- execution/
  - (発注/約定/ポジション管理用のモジュール群 — 現状プレースホルダ)
- monitoring/
  - (監視・メトリクス収集用のモジュール群 — プレースホルダ)

---

## 追加のヒント / トラブルシューティング

- DuckDB のファイルパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）で管理されます。初回実行時にディレクトリが自動作成されます。
- RSS 取得時はリダイレクト先のスキーム / ホスト検査（SSRF 対策）を行います。社内ネットワークのプライベートアドレスを参照する RSS を利用する場合は注意してください。
- ETL のバックフィルはデフォルト3日です（backfill_days）。API の後出し修正を吸収するためです。
- ログは LOG_LEVEL で制御できます（settings.log_level）。デバッグ時は `LOG_LEVEL=DEBUG` を設定してください。

---

必要であれば以下も追加できます：
- 具体的な SQL スキーマ（完全版）
- サンプル .env.example ファイル
- CI 用のテスト手順・ユニットテスト例
- 実運用での監視・アラート設計ガイド

必要な追加情報を教えてください。README を目的（開発者向け / 運用マニュアル / 簡易チュートリアル）に合わせてさらに調整します。