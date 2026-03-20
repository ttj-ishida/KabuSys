# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータストアに用い、J-Quants API や RSS からのニュース収集、ファクター計算、戦略シグナル生成、発注監査などの機能を提供します。

---

## 概要

このリポジトリは次のレイヤーを持つモジュール群で構成されています。

- データ取得・保存 (J-Quants クライアント、RSS ニュース収集、ETL パイプライン)  
- スキーマ定義 / DuckDB 初期化
- 研究用ファクター計算（research 層）
- 特徴量生成・シグナル生成（strategy 層）
- 発注・実行・監査のためのデータモデル（execution / audit）
- ユーティリティ（統計、カレンダー管理など）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT や idempotent 保存）、API レート制御、堅牢なエラーハンドリングを重視しています。

---

## 主な機能一覧

- J-Quants API クライアント
  - 日足（OHLCV）・財務情報・マーケットカレンダー取得
  - レート制御、リトライ、トークン自動リフレッシュなどを実装
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 各レイヤーのテーブルを定義
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS 取得、前処理、記事保存、銘柄コード抽出・紐付け
  - SSRF・サイズ制限・XML 攻撃対策を実装
- 研究用ファクター計算
  - Momentum / Volatility / Value 等を DuckDB 上で計算（研究用）
- 特徴量エンジニアリング
  - ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの保存
- シグナル生成
  - features / ai_scores / positions を用いた final_score 計算
  - BUY/SELL シグナルの生成・signals テーブルへの保存
- カレンダー管理（営業日判定、next/prev/trading_days）
- 監査ログ（signal_events / order_requests / executions）設計

---

## 必要条件

- Python 3.10 以上（PEP 604 の型注釈などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（実行環境に応じて他パッケージが必要になる場合があります。requirements.txt があればそれを参照してください）

---

## 環境変数

kabusys は .env / 環境変数から設定を読み込みます（自動読み込み機能あり）。必須の環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

その他（任意/デフォルトあり）:

- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / ...（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードの無効化（テスト用）

自動ロード動作:
- プロジェクトルート（.git または pyproject.toml を持つディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install duckdb defusedxml
   - またはプロジェクトに requirements.txt があれば: pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記必須値を設定してください。
   - 例（.env）
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

5. DuckDB スキーマ初期化（例）
   - 下記「使い方」の例を参照して DB を初期化します。

---

## 基本的な使い方（サンプル）

Python スクリプト / REPL から直接利用できます。以下は基本的なワークフロー例です。

1) DuckDB のスキーマ初期化と接続

```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可
```

2) 日次 ETL の実行（J-Quants からの差分取得 → 保存 → 品質チェック）

```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3) 特徴量の生成（features テーブルへ保存）

```
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ保存）

```
from kabusys.strategy import generate_signals
from datetime import date

n_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {n_signals}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → news_symbols 紐付け）

```
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードセット（抽出と紐付けに使用）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

注意:
- J-Quants API はレート制限や認証が必要です。settings.jquants_refresh_token を設定してください。
- ETL 実行中にネットワークエラーや API エラーが起こっても、モジュール内で可能な限り個別にハンドルし続行します。結果オブジェクトで発生エラーを確認できます。

---

## よく使う API / 関数一覧（抜粋）

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)
- kabusys.research
  - calc_momentum(conn, date)
  - calc_volatility(conn, date)
  - calc_value(conn, date)
  - calc_forward_returns(...)
  - calc_ic(...)
- kabusys.strategy
  - build_features(conn, date)
  - generate_signals(conn, date, threshold, weights)

---

## 開発上の注意 / 設計ポイント

- ルックアヘッドバイアスを防ぐため、全ての計算は target_date 時点のデータのみを参照するよう設計されています。
- DB への保存は冪等（ON CONFLICT .. DO UPDATE / DO NOTHING）で行い、再実行可能です。
- J-Quants クライアントはページネーション対応、レート制御、リトライ、401 のトークン自動更新を含みます。
- ニュース収集は SSRF 対策、XML 攻撃対策、サイズ上限など安全面を考慮しています。
- research 層は外部依存を可能な限り排し、標準ライブラリ + duckdb の SQL で完結します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py            — RSS ニュース収集
    - schema.py                    — DuckDB スキーマ定義・init_schema
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - stats.py                     — zscore_normalize 等統計ユーティリティ
    - features.py                  — features インターフェース（再エクスポート）
    - calendar_management.py       — カレンダー管理（営業日判定等）
    - audit.py                     — 監査ログ定義
    - (その他: quality.py 等想定)
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value 計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — features 作成処理
    - signal_generator.py          — final_score / シグナル生成
  - execution/                     — 発注実行層（空の __init__ や実装ファイル）
  - monitoring/                    — 監視・メトリクス（未実装・想定）

---

## ライセンス / 貢献

- ライセンス情報はリポジトリのルートにある LICENSE を参照してください（無い場合はリポジトリ所有者に確認してください）。
- バグ報告や機能提案は Issue を立ててください。プルリクエスト歓迎です。

---

README に書かれていない追加の実行例や内部仕様（StrategyModel.md / DataPlatform.md などの設計文書）がリポジトリ内にある場合、それらも参照して実運用してください。必要があれば README に追記する内容（例：Slack 通知の使い方、kabu API の発注フローなど）を教えてください。