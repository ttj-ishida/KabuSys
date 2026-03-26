# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ/研究/バックテスト基盤）。  
本 README は提供されたコードベースに基づく簡易ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト、およびニュース収集を行うためのモジュール群を含むシステムです。  
設計方針としては「ルックアヘッドバイアス回避」「冪等性」「DB への安全な保存」「バックテストと本番ロジックの分離」を重視しています。

主な設計対象：
- データ収集（J-Quants API / RSS ニュース）
- 研究用ファクター計算（DuckDB を想定）
- 特徴量構築 → シグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定 / 重み付け / サイジング / セクター制限）
- バックテストフレームワーク（擬似約定・トレード記録・メトリクス）
- ニュース収集・銘柄抽出（RSS）

---

## 機能一覧（主要機能）

- 環境設定管理
  - .env（プロジェクトルート）からの自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の取得ラッパー（settings）

- データ収集
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
    - 株価日足 / 財務データ / 上場銘柄情報 / マーケットカレンダー取得
  - ニュース収集（RSS）と前処理（URL 正規化・トラッキング除去・SSRF 対策）
  - DuckDB への冪等保存ユーティリティ

- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - ファクター探索（将来リターン計算 / IC 計算 / 統計サマリー）
  - Z スコア正規化ユーティリティとの連携

- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターのマージ、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT

- シグナル生成（strategy.signal_generator）
  - features / ai_scores を元に final_score を計算
  - Bear レジーム時の BUY 抑制、SELL（エグジット）判定
  - signals テーブルへの日次置換（冪等）

- ポートフォリオ構築（portfolio）
  - 候補選定（スコア順選出）
  - 重み計算（等配分、スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - 株数計算（リスクベース / weight ベース、単元丸め、aggregate cap）

- バックテスト（backtest）
  - インメモリ DuckDB に必要データをコピーして実行
  - PortfolioSimulator による擬似約定（スリッページ/手数料モデル）
  - 日次スナップショット・トレード記録・メトリクス（CAGR, Sharpe, MaxDD, WinRate 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

---

## 要件（主な依存パッケージ）

提供コードから明示的に参照される外部ライブラリ例（プロジェクトに合わせて requirements を用意してください）：

- Python 3.10+
- duckdb
- defusedxml

その他標準ライブラリ（urllib, urllib.parse, datetime, logging, math, collections など）を使用しています。

（実際の pyproject.toml / requirements.txt はこの断片には含まれていません。開発環境に合わせて依存を整備してください）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン（既にコードがある想定）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   ※ 実プロジェクトでは `pip install -r requirements.txt` または `pip install -e .` を使う想定です。

4. .env を作成（プロジェクトルートに配置）
   - config.Settings が .env を自動読み込みします（ただしプロジェクトルートは .git / pyproject.toml を基準に探索）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（必要なキー）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi      # 任意
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

5. DuckDB スキーマ/データ準備
   - バックテストや一部処理は事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar, stocks などのテーブルが整備されている前提です。
   - provided code は kabusys.data.schema.init_schema を参照している箇所があるため、実運用ではスキーマ初期化用の SQL / 初期化関数を用意してください。

---

## 使い方

以下は代表的な利用例です。

- バックテスト（CLI）

  必要な DB ファイル（DuckDB）が用意されている前提。例:

  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb

  主なオプション:
  - --start / --end: 日付（YYYY-MM-DD）
  - --cash: 初期資金（円）
  - --slippage / --commission: スリッページ・手数料率
  - --allocation-method: equal | score | risk_based
  - --max-positions: 最大保有数（デフォルト 10）
  - --lot-size: 単元（デフォルト 100）
  - --db: DuckDB ファイルパス（必須）

  バックテストは内部で以下を実行します（概略）:
  - DuckDB の必要テーブルをインメモリにコピー
  - 各営業日について: 約定（前日発注）、positions 書き込み、評価（終値）、シグナル生成、ポートフォリオ構築 → 翌日発注

- Python API（例）

  - DuckDB 接続の取得（schema.init_schema を想定）と特徴量構築:

    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    from datetime import date
    conn = init_schema("path/to/kabusys.duckdb")
    cnt = build_features(conn, target_date=date(2024, 1, 31))
    conn.close()

  - シグナル生成:

    from kabusys.strategy import generate_signals
    conn = init_schema("path/to/kabusys.duckdb")
    n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
    conn.close()

  - J-Quants からデータ取得と保存:

    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    conn = init_schema("path/to/kabusys.duckdb")
    records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2024,1,1))
    saved = save_daily_quotes(conn, records)
    conn.close()

  - ニュース収集ジョブ:

    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("path/to/kabusys.duckdb")
    results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
    conn.close()

注意:
- 多くの関数は DuckDB 接続（kabusys.data.schema.init_schema の返す接続）を受け取ります。
- 日付は target_date の時点の「知り得る情報のみ」を使う実装になっています（ルックアヘッド回避）。
- 一部機能は事前にテーブル（raw_prices / raw_financials / prices_daily / features / ai_scores / signals / positions / stocks 等）の準備が必要です。

---

## 主要モジュール・ディレクトリ構成

（コードベースの該当部分を抜粋した構成例）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（J-Quants トークン・kabu API パスワード・Slack トークン・DB パス等）
  - data/
    - jquants_client.py  — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py  — RSS 収集・正規化・DB 保存
    - (schema.py を参照する箇所あり: DB スキーマ初期化用)
  - research/
    - factor_research.py  — momentum/volatility/value ファクター計算
    - feature_exploration.py — IC / forward_returns / factor_summary
  - strategy/
    - feature_engineering.py — features テーブル構築（Z スコア正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py — 候補選定・等配分/スコア加重
    - position_sizing.py  — 株数計算（risk_based / weight ベース）
    - risk_adjustment.py  — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストの全体ループ（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定・history/trades 管理）
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - portfolio/__init__.py, strategy/__init__.py, research/__init__.py, backtest/__init__.py などエクスポートの整備

各モジュールは「DuckDB 接続を受け取る」「DB を直接書き換える箇所は日付単位の置換（冪等）を行う」「本番 API 依存を最小化する」設計になっています。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

注意: config.py はプロジェクトルートの .env と OS 環境変数を自動で読み込みます。自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## トラブルシューティング（よくある注意点）

- DuckDB のテーブルが不足しているとバックテストやシグナル生成が失敗します。事前に必要テーブルを準備してください（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）。
- J-Quants API 呼び出しはレート制限とリトライを実装していますが、トークン切れで 401 が出た場合は refresh トークンが必要です。
- ニュース収集時の外部接続は SSRF 対策およびレスポンスサイズ上限を設けています。RSS の仕様に沿ったソースを使ってください。
- バックテストは「当日終値で翌日発注量を見積もり、翌日始値で約定する」フローを採用しています。実運用の発注とはタイミングが異なります。

---

## 貢献 / 拡張アイデア

- stock ごとの lot_size を取り扱う（現状一括 lot_size）
- position_sizing のコスト見積りを拡張（前日終値や取得原価フォールバック）
- signal_generator のニュース/AI スコア統合の改善
- 分足シミュレーション対応（SimulatedClock を拡張）

---

以上がこのコードベースの概要と導入・利用方法のまとめです。他に追加したいセクション（API リファレンス、テスト手順、pyproject/CI 設定など）があれば指定してください。