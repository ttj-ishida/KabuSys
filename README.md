# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ収集（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル作成、ニュース収集、カレンダー管理、監査ログなど、戦略開発から発注レイヤーに渡すまでの主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存する（差分更新・冪等保存）
- 研究環境で計算した生ファクターを正規化・合成して戦略用の特徴量を生成
- 正規化済み特徴量と AI スコアを統合して売買シグナル（BUY / SELL）を作成
- RSS ベースのニュース収集と銘柄抽出（raw_news / news_symbols）
- JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注・約定・ポジションの監査ログを保持するスキーマを提供

設計上の特徴として、ルックアヘッドバイアスを避けるため「target_date 時点で利用可能なデータのみ」を使うこと、外部発注 API への直接依存を薄くしてテスト可能にしている点が挙げられます。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（自動トークン更新、レート制限、リトライ）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）
  - news_collector: RSS 収集、テキスト前処理、記事保存、銘柄抽出
  - calendar_management: JPX カレンダー更新・営業日判定ユーティリティ
  - stats: Z スコア正規化などの統計ユーティリティ
  - audit: 発注→約定までの監査ログ定義
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- strategy/
  - feature_engineering.build_features: 生ファクターを統合・正規化して features テーブルへ書き込み
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを作成
- config: 環境変数を読み込む Settings（.env 自動ロード機能付き）
- news 収集時の SSRF 対策、XML パースの安全対策（defusedxml）などセキュリティ考慮あり

---

## 前提条件

- Python 3.9+
- パッケージ依存（代表例）
  - duckdb
  - defusedxml
- J-Quants API のリフレッシュトークン（運用時）
- （運用時）kabu API、Slack など外部サービスのトークン

必要に応じて仮想環境を作成してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
```

プロジェクト配布に requirements.txt / pyproject.toml がある場合はそちらを使ってください。

---

## 環境変数 / .env

config.Settings は環境変数から設定を読み込みます。デフォルトではプロジェクトルート（.git または pyproject.toml を検索）にある `.env` と `.env.local` を自動読み込みします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（コード内で _require により必須化されている主なキー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン（通知等に使用）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（default: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（default: data/monitoring.db）

.env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. 仮想環境の作成（任意）
2. 依存パッケージのインストール
   - 最低限: duckdb, defusedxml
   - 例: pip install duckdb defusedxml
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB のスキーマを作成
   - Python REPL やスクリプトから init_schema を呼ぶ

例:
```
python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"
```

---

## クイックスタート（使い方の例）

以下は Python スクリプトから主要な処理を行う例です。実行前に `.env` を用意し、依存パッケージをインストールしてください。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（J-Quants から差分取得して保存）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量ビルド（戦略用 features を生成）
```
from kabusys.strategy import build_features
from datetime import date

cnt = build_features(conn, target_date=date.today())
print(f"features upserted: {cnt}")
```

4) シグナル生成（features と ai_scores を基に signals を作る）
```
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total_signals}")
```

5) ニュース収集（RSS から raw_news / news_symbols へ保存）
```
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", ...}  # 既知の有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

6) カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 主要モジュールの説明（短く）

- kabusys.config
  - .env 自動ロード、必須環境変数取得、ランタイム設定（env, log_level 等）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、リトライ、トークン管理、DuckDB への冪等保存関数（save_daily_quotes 等）
- kabusys.data.schema
  - DuckDB のスキーマ DDL を定義。init_schema() でテーブル作成。
- kabusys.data.pipeline
  - run_daily_etl による差分 ETL（calendar → prices → financials → 品質チェック）
- kabusys.data.news_collector
  - RSS 取得、前処理、記事と銘柄紐付けを安全に実行（SSRF 対策、XML パース防御、受信サイズ制限）
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- kabusys.research.factor_research
  - momentum / volatility / value ファクター計算（prices_daily / raw_financials に依存）
- kabusys.strategy.feature_engineering
  - calc_* ファクターを統合・正規化して features に UPSERT
- kabusys.strategy.signal_generator
  - features と ai_scores を統合し final_score を算出、BUY/SELL を決定して signals テーブルへ保存
- kabusys.data.audit
  - 発注〜約定〜埋め合わせのトレーサビリティ用テーブル定義

注意: execution パッケージは空の初期化ファイルのみで、発注層との連携は別実装を想定しています。

---

## ディレクトリ構成

（プロジェクトの src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - calendar_management.py
      - audit.py
      - features.py
      - pipeline.py
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

README のこのセクションは実際のリポジトリを基に更新してください。上は提供コードの抜粋に基づく構成です。

---

## 開発時のヒント / 注意事項

- DuckDB の初期化は一度実行すれば OK（init_schema は冪等）。
- production（live）モードに切り替える場合は KABUSYS_ENV=live を設定し、実際の kabu 発注ロジックを組み込む際の安全確認（テスト、マンデート）を徹底してください。
- ニュース収集では外部 URL を扱うため SSRF 対策・受信サイズ制限が組み込まれています。fetch_rss/_urlopen をテストでモックして利用してください。
- J-Quants へのリクエストはレート制限（120 req/min）を守るよう設計されていますが、運用時は実際の API 規約を確認してください。
- env 読み込みの自動化は開発時便利ですが、CI/CD やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御してください。

---

以上が README の概要です。リポジトリに合わせて .env.example、requirements.txt、pyproject.toml、pytest 等の追加ファイルを用意することを推奨します。必要であれば README の英語版や導入手順の詳細（Docker / systemd / cron での定期実行例、Slack 通知の設定例など）も作成します。リクエストがあれば追記します。