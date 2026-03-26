# KabuSys

日本株向けの自動売買 / バックテスト基盤ライブラリです。  
ファクター計算・特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、擬似約定シミュレーション、J-Quants からのデータ取得やニュース収集など、研究〜本番運用に必要な主要機能をモジュール化して提供します。

---

## 概要

KabuSys は以下のレイヤーで構成された投資システム用ライブラリです。

- data: J-Quants API クライアント、ニュース収集、DuckDB への保存ロジック
- research: ファクター計算・探索用ユーティリティ
- strategy: 特徴量作成、シグナル生成
- portfolio: 候補選定、重み計算、ポジションサイジング、リスク制御
- backtest: バックテストエンジン（擬似約定を含む）とメトリクス計算

設計方針としては「ルックアヘッドバイアス回避」「DB への冪等保存」「研究用と実稼働での依存分離（発注 API に依存しない）」を重視しています。

---

## 主な機能

- J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制限・リトライ）
- DuckDB へのデータ保存（株価、財務、カレンダー等）
- ニュースの RSS 収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- ファクター計算（momentum, volatility, value 等）
- 特徴量エンジニアリング（ユニバースフィルタ、Zスコア正規化、クリッピング）
- シグナル生成（因子加重、AIスコア統合、Bear フィルタ、SELL（エグジット）判定）
- ポートフォリオ構築（候補選定、等金額/スコア加重/リスクベースのサイジング、セクター上限）
- バックテストエンジン（擬似約定、スリッページ／手数料モデル、結果のメトリクス）
- CLI バックテスト実行（python -m kabusys.backtest.run）

---

## 必要要件

- Python 3.10+
- 依存パッケージ（DuckDB 等） — setup または requirements を参照してください

（本リポジトリに含まれる pyproject.toml / requirements.txt がある想定です。なければ duckdb などを手動でインストールしてください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージのインストール（開発時）
   - pip install -e .

   もしくは最低限：
   - pip install duckdb defusedxml

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（起点はこのパッケージのファイル位置に基づく）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. データベース
   - デフォルトの DuckDB ファイルパスは settings.duckdb_path（デフォルト `data/kabusys.duckdb`）です。
   - schema 初期化関数は `kabusys.data.schema.init_schema(db_path_or_:memory:)` を使います（実装ファイルはプロジェクト内に存在する前提で参照されます）。
   - バックテスト用に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）を用意してください。

---

## 環境変数（必須）

以下は Settings クラスで参照される主要な環境変数です。実運用前に .env を作成してください。

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須、使用する場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須、使用する場合）

任意 / デフォルトがあるもの:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## 使い方

### バックテスト（CLI）

DuckDB に必要テーブルが揃っている前提で、CLI からバックテストを実行できます。

例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb

主なオプション:
- --start / --end : 期間（YYYY-MM-DD）
- --cash : 初期資金（円）
- --allocation-method : equal / score / risk_based
- --slippage, --commission, --max-position-pct, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size
- --db : DuckDB ファイルパス（必須）

CLI 実行後にバックテストの主要指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, TotalTrades）が表示されます。

### プログラム API

主なエントリポイント（一部）:

- 特徴量構築
  from kabusys.strategy import build_features
  build_features(conn, target_date)

- シグナル生成
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date, threshold=0.6, weights=None)

- J-Quants データ取得 & 保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar
  data = fetch_daily_quotes(...)
  save_daily_quotes(conn, data)

- ニュース収集
  from kabusys.data.news_collector import run_news_collection
  run_news_collection(conn, sources=None, known_codes=None)

- バックテスト実行（API）
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)

注意点:
- 多くの関数は DuckDB の接続オブジェクト（kabusys.data.schema.init_schema で得られる）を引数に取ります。
- build_features / generate_signals 等は同一日に対して「日付単位で delete → insert の置換」を行うため冪等です。
- J-Quants API 呼び出しはレート制限やリトライ、401 の自動リフレッシュを備えていますが、正しいリフレッシュトークンが必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定の読み込み
- data/
  - jquants_client.py  — J-Quants API クライアント、保存関数
  - news_collector.py  — RSS 収集・保存・銘柄抽出
  - (schema.py, calendar_management.py などは参照箇所あり)
- research/
  - factor_research.py  — momentum / volatility / value の計算
  - feature_exploration.py — IC / forward returns / summary
- strategy/
  - feature_engineering.py — features テーブル構築
  - signal_generator.py — final_score 計算と signals 書き込み
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定ロジック
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- backtest/
  - engine.py — バックテストループ（run_backtest）
  - simulator.py — 擬似約定とポートフォリオ状態管理
  - metrics.py — バックテスト評価指標
  - run.py — CLI エントリポイント
  - clock.py — 将来の拡張用模擬時計
- portfolio/ __init__.py, strategy/ __init__.py, research/ __init__.py, backtest/ __init__.py などのパッケージエクスポート

---

## 開発・デバッグのヒント

- 環境変数読み込みは config.py が自動で行いますが、テストやスクリプト実行時に影響する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB の in-memory モード（":memory:"）を利用してテスト用のデータを流し込み、バックテストを高速に実行できます（engine._build_backtest_conn を参照）。
- ニュース収集モジュールは外部ネットワークを利用するため、ユニットテストではネットワーク呼び出しをモックすることを推奨します（_urlopen を差し替え可能）。

---

## 貢献 / ライセンス

貢献は歓迎します。Issue / PR を通じて提案してください。ライセンス情報はこのリポジトリに含まれる LICENSE ファイルを参照してください（プロジェクトに未付属であれば別途明示してください）。

---

README は以上です。実行時や開発時に詰まった点があれば、どのモジュール・どの関数で問題が起きているかを明示して質問してください。