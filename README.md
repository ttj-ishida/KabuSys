# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。市場データの取得・保管（DuckDB）、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤーのためのスキーマとユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下のレイヤーを持つデータ処理・戦略実行基盤の核となる機能を実装しています。

- Data（データ取得 / ETL）
  - J-Quants API クライアント（ページネーション・リトライ・レート制限対応）
  - RSS ニュース収集（SSRF 対策・正規化・銘柄抽出）
  - DuckDB スキーマ定義と初期化、データ保存ユーティリティ
  - 日次 ETL パイプライン（差分取得 / 品質チェック）
- Research（リサーチ用ファクター計算 / 探索）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Spearman）・統計サマリー
- Strategy（特徴量エンジニアリング / シグナル生成）
  - クロスセクションでの Z スコア正規化やユニバースフィルタ
  - 複数コンポーネントを重み付けして最終スコアを算出し BUY/SELL シグナルを生成
- Execution / Audit（スキーマ・型安全な監査ログ）
  - 発注・約定・ポジション・監査用テーブル定義（DuckDB）
- 設定管理（環境変数 / .env 自動読み込み）

設計方針としては「ルックアヘッドバイアスの排除」「冪等性（idempotency）」「外部依存を局所化」「テストしやすさ」を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env または環境変数から設定を読み込む（プロジェクトルート探索、.env/.env.local の優先読み込み）
  - 必須環境変数チェック（_require）
  - settings オブジェクト経由で各種設定を取得

- kabusys.data.jquants_client
  - J-Quants API から日足・財務・カレンダー取得（ページネーション対応）
  - レート制限の遵守（固定間隔スロットリング）、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT を利用した save_* 関数）

- kabusys.data.schema
  - DuckDB のスキーマ（raw / processed / feature / execution）を定義
  - init_schema(db_path) による初期化

- kabusys.data.pipeline
  - run_daily_etl: 市場カレンダー・株価・財務の差分 ETL を実行、品質チェックを実施
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- kabusys.data.news_collector
  - RSS フィード取得、XML パース、テキスト前処理、記事ID生成（正規化 URL の SHA-256）
  - raw_news, news_symbols への冪等保存
  - SSRF 回避・受信サイズ制限・gzip 対応

- kabusys.research.factor_research / feature_exploration
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）解析、統計サマリー

- kabusys.strategy.feature_engineering / signal_generator
  - ファクターの統合・Z スコア正規化・ユニバースフィルタ → features テーブルへ保存
  - features と ai_scores を組み合わせて final_score を算出し signals を生成（BUY / SELL）
  - SELL はストップロス等のエグジット条件を判定

- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

※プロジェクトには外部依存パッケージ（duckdb, defusedxml 等）が必要です。以下は一般的なセットアップ例です。

1. Python (推奨: 3.9+) を用意する

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください）

4. パッケージをローカルにインストール（開発モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定してください。
   - 主要な環境変数は次節参照。

6. DuckDB スキーマの初期化（例）
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 必要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。get_id_token のために使用されます。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（execution 層向け）。

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - kabu API のベース URL。

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン（必要な場合）。

- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID。

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルのパス。

- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
  - 監視用途に使う SQLite のパス（プロジェクト内の用途に応じて）。

- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development / paper_trading / live
  - is_live / is_paper / is_dev の切り替えに使用されます。

- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - 1 をセットすると .env 自動ロードを無効化（テスト用途など）。

.env 例（.env.example として保存）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡易ガイド）

以下は主要な操作のサンプルです。実行は Python スクリプト内で行うことを想定しています。

1) DuckDB スキーマ初期化

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants からデータを取得して保存）

from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) 特徴量（features）作成

from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

4) シグナル生成

from datetime import date
from kabusys.strategy import generate_signals
total = generate_signals(conn, target_date=date.today())
print(f"signals written: {total}")

5) RSS ニュース収集

from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードのセット（例: {"7203", "6758", ...}）
results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(results)

6) J-Quants から直接日足を取得して保存（テスト用）

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)

注意点:
- ETL 実行時にネットワークアクセスが必要です。J-Quants トークンと API アクセスを用意してください。
- 本番 (KABUSYS_ENV=live) では外部 API の使用や発注処理の扱いに十分注意してください。

---

## ディレクトリ構成

主なファイル／パッケージ構成（src/kabusys 以下）

- kabusys/
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
    - (その他 ETL/品質チェック関連モジュール)
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
    - (発注・ブローカー連携関連の実装を追加)
  - monitoring/
    - (監視関連モジュール: README の __all__ に含まれるが実装は別途)
  - その他ドキュメント（DataSchema.md, StrategyModel.md 等を参照する想定）

（上記はコードベースに含まれる代表的なファイルを抜粋しています）

---

## 開発・テスト時のヒント

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を親階層で探索）で行われます。テスト時に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を使うと安全にスキーマを作成できます（冪等）。
- ネットワーク依存の関数（jquants_client.fetch_* や news_collector.fetch_rss）はユニットテストではモックすることを推奨します。jquants_client は id_token キャッシュを内部保持しており、get_id_token のモック化が容易です。
- news_collector は SSRF 対策やレスポンスサイズ上限を持っています。外部フィードを追加する際は既存の DEFAULT_RSS_SOURCES を参照してください。

---

## ライセンス / 貢献

本 README では省略します。実運用や外部公開を行う際は別途 LICENSE を追加してください。

---

README は以上です。プロジェクト特有の細かい仕様（StrategyModel.md、DataPlatform.md、DataSchema.md など）がリポジトリに存在する想定です。実際の運用ガイドやデプロイ手順（コンテナ化、CI、監視設定等）は別ドキュメントにまとめることを推奨します。