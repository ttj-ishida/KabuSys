# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
特徴量計算・シグナル生成・ポートフォリオ構築・バックテスト・データ収集（J-Quants / RSS）等の主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の量的運用ワークフローを構成するモジュール群です。  
主な用途は研究環境でのファクター計算・シグナル生成、及び DuckDB を使ったバックテストです。  
また J-Quants からのデータ取得、ニュース収集（RSS）や簡易のポートフォリオシミュレータなど運用に必要なコンポーネントを含みます。

設計方針の例:
- ルックアヘッドバイアスに配慮したデータ取扱い
- DuckDB を中心としたローカルデータストア
- 冪等性を意識した DB 書き込み
- バックテストと運用ロジックの分離（execution 層は別実装想定）

---

## 機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（無効化可能）
- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - 日足・財務・上場銘柄情報取得、DuckDB への保存ユーティリティ
  - ニュース収集（RSS）＋記事保存・銘柄抽出
- 研究用ファクター計算（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算、IC 計算ユーティリティ
- 特徴量エンジニアリング（kabusys.strategy.build_features）
  - ファクターの正規化・クリッピング・features テーブルへの UPSERT
- シグナル生成（kabusys.strategy.generate_signals）
  - ファクター + AI スコア統合による final_score 計算、BUY/SELL シグナル生成
  - Bear レジーム抑制、売買ロジックは StrategyModel に準拠
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイジング（リスクベース等）
  - セクター集中制限、レジーム乗数
- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(): インメモリ DuckDB コピーを用いた日次ループ型バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）とメトリクス算出
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他ユーティリティ
  - データ正規化、統計サマリ、RSS 前処理、URL 正規化、銘柄コード抽出 等

---

## 要件

- Python 3.10+
- 推奨パッケージ（最低限）
  - duckdb
  - defusedxml
- （実行環境により追加）
  - ネットワーク接続（J-Quants API / RSS）
  - DuckDB ファイル（バックテスト実行時）

※ 実際の運用では依存バージョン管理（requirements.txt / pyproject.toml）を使用してください。

---

## インストール

リポジトリのルートにて（パッケージ化されている前提）:

1. 仮想環境を作成・有効化
2. ビルド / 開発インストール（プロジェクトに pyproject.toml / setup がある想定）:

pip install -e . あるいは requirements を手動インストール:
pip install duckdb defusedxml

---

## 環境変数（設定）

kabusys.config.Settings が参照する主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（default: data/monitoring.db）
- KABUSYS_ENV — env タグ (development | paper_trading | live)、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）

プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

サンプル .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（データベース等）

1. DuckDB スキーマ初期化
   - 本コードベースでは `kabusys.data.schema.init_schema` がスキーマ初期化関数として参照されています（スキーマ定義ファイルを用意してください）。
   - 既存の DB を使う場合は prices_daily / features / ai_scores / market_regime / market_calendar 等のテーブルが必要です（バックテスト CLI の注意参照）。

2. J-Quants データ取得（例）
   - ID トークン取得:
     from kabusys.data.jquants_client import get_id_token
     token = get_id_token()
   - 日足取得・保存:
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     save_daily_quotes(conn, records)

3. RSS ニュース収集
   - run_news_collection(conn, sources=..., known_codes=set_of_codes)

---

## 使い方（代表例）

### バックテスト（CLI）

事前条件: 指定する DuckDB ファイルに必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が存在していること。

実行例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-29 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb

主要オプション:
- --start / --end: バックテスト期間（YYYY-MM-DD）
- --cash: 初期資金
- --allocation-method: equal | score | risk_based
- --slippage / --commission: コストパラメータ
- --max-positions / --lot-size 等

### プログラムからバックテストを呼ぶ

from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history / result.trades / result.metrics を利用
conn.close()

### 特徴量構築（build_features）

from kabusys.strategy import build_features
# conn: DuckDB 接続、target_date: datetime.date
count = build_features(conn, target_date)

- features テーブルに target_date の値を置換（冪等）で書き込みます。

### シグナル生成（generate_signals）

from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date)

- features, ai_scores, positions を参照し signals テーブルに BUY/SELL を書き込みます。

### ニュース収集（run_news_collection）

from kabusys.data.news_collector import run_news_collection
res = run_news_collection(conn, sources=None, known_codes=set_of_codes)
# res は {source_name: saved_count}

### J-Quants クライアント（データ取得 & 保存）

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
save_daily_quotes(conn, records)

---

## ディレクトリ構成

（主なファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- data/
  - jquants_client.py            — J-Quants API クライアント（取得 & 保存）
  - news_collector.py            — RSS 収集・保存・銘柄抽出
  - ...（schema, calendar_management 等想定）
- research/
  - factor_research.py           — Momentum/Value/Volatility 等
  - feature_exploration.py       — IC/forward returns 等
- strategy/
  - feature_engineering.py       — features の構築
  - signal_generator.py          — final_score 計算と signals 生成
- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 株数決定（risk_based / equal / score）
  - risk_adjustment.py           — セクターキャップ・レジーム乗数
- backtest/
  - engine.py                    — run_backtest メイン実装
  - simulator.py                 — ポートフォリオシミュレータ（約定ロジック）
  - metrics.py                   — バックテスト指標計算
  - run.py                       — CLI エントリポイント
  - clock.py
- execution/                      — 発注 / 実行層（空のパッケージ、実装次第）
- monitoring/                     — 監視・通知関連（SQLite 利用など、実装想定）

---

## 注意事項 / 運用上のポイント

- Look-ahead バイアス防止:
  - 各処理は target_date 時点で利用可能なデータのみを参照する設計を意識していますが、実データ投入・ETL 時に取得日時（fetched_at）を適切に管理してください。
- Backtest 実行前に DuckDB のテーブルが正しく準備されていることを確認してください（prices_daily 等）。
- J-Quants の API レート制限とトークン管理に注意（モジュール内に RateLimiter / 自動リフレッシュ実装あり）。
- news_collector は外部リダイレクトや大容量レスポンスに対する安全処理を含みますが、実稼働環境ではネットワーク制限やタイムアウト設定を行ってください。

---

## 開発

- 型ヒントとドキュメント文字列を多用しています。リファクタや単体テストを作成すると品質が向上します。
- DuckDB を利用したクエリ部分は実データでの検証が重要です（週末/祝日・欠損値等の取り扱い）。

---

必要に応じて README に追記します。例えば:
- schema 初期化方法（kabusys.data.schema の具体的な説明）
- CI / テスト実行手順
- 実運用時の deployment / cron ジョブ例

追加で追記したい項目があれば教えてください。