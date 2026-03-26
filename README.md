# KabuSys

日本株向けの自動売買 / バックテストフレームワーク。価格・財務・ニュース等のデータ収集、特徴量生成、シグナル生成、ポートフォリオ構築、擬似約定によるバックテストを一貫して実行できるモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス排除（target_date 時点のデータのみ使用）
- DuckDB を用いたローカルデータ管理（ETL → 分析 → バックテスト）
- 外部 API（J-Quants 等）との疎結合（リトライ・レート制御・トークン自動リフレッシュ）
- 冪等性とトランザクション管理を重視した DB 操作

バージョン: 0.1.0

---

## 機能一覧

- data/
  - J-Quants クライアント（価格・財務・上場情報・カレンダーの取得、保存）
  - ニュース収集（RSS 収集、正規化、銘柄抽出、raw_news 保存）
- research/
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索ユーティリティ（将来リターン、IC、統計サマリ等）
- strategy/
  - 特徴量エンジニアリング（研究結果の正規化・features テーブルへの保存）
  - シグナル生成（features + ai_scores を統合して BUY/SELL を生成）
- portfolio/
  - 候補選定・重み計算（等配分・スコア配分）
  - ポジションサイジング（risk-based 等）
  - リスク調整（セクター上限・レジーム乗数）
- backtest/
  - エンジン（データをコピーした in-memory DuckDB を用いたバックテスト）
  - シミュレータ（擬似約定、スリッページ・手数料モデル、日次スナップショット）
  - メトリクス（CAGR, Sharpe, MaxDD, Win rate, Payoff ratio）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- monitoring / execution / slack 等の基礎フレーム（実運用向けの拡張ポイント）

---

## セットアップ手順

前提：
- Python 3.10 以上を推奨（typing の | 記法・将来注釈等を使用）
- DuckDB（Python パッケージ）、defusedxml 等が必要

1. リポジトリをクローン：
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）：
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）：
   ```
   pip install duckdb defusedxml
   ```
   - 実行環境によっては追加で `requests` や `pandas` 等を使うことがありますが、本コードベースでは主に `duckdb` と `defusedxml` が明示的に使用されています。

4. パッケージを開発モードでインストール（任意）：
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.cfg 等がある場合）

5. 環境変数の設定：
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます（デフォルト）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（Settings クラスで参照）：
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（実運用で使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — 通知先の Slack チャンネル ID
   - 省略可能な変数：
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（monitoring）パス（デフォルト: data/monitoring.db）

6. DB スキーマ初期化：
   - 本リポジトリでは `kabusys.data.schema.init_schema` を通じて DuckDB スキーマを初期化する想定です（schema モジュールを使って DB を作成・テーブルを準備してください）。
   - 例（スクリプトから）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # データ投入処理等
     conn.close()
     ```

---

## 使い方

### バックテスト（CLI）

duckdb に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が揃っていることを前提に、CLI からバックテストを実行できます。

例：
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100
```

主な引数：
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --db : DuckDB ファイルパス（必須）
- --cash : 初期資金（JPY）
- --slippage / --commission : スリッページ・手数料率
- --allocation-method : capital allocation ("equal" | "score" | "risk_based")
- --max-positions / --max-utilization / --risk-pct / --stop-loss-pct 等も指定可能

実行結果は標準出力にメトリクス（CAGR 等）を表示し、内部で `BacktestResult`（history・trades・metrics）を返す API も提供しています。

### Python API（主な利用例）

- 特徴量生成（features テーブルへ UPSERT）：
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2023, 12, 29))
  print(f"features upserted: {count}")
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込み）：
  ```python
  from kabusys.strategy import generate_signals
  count = generate_signals(conn, target_date=date(2023, 12, 29))
  print(f"signals generated: {count}")
  ```

- J-Quants からデータ取得と保存：
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集の実行：
  ```python
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", ...}  # stocks マスタ等から取得
  results = run_news_collection(conn, known_codes=known_codes)
  ```

- バックテスト API を直接呼ぶ：
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

注意点：
- generate_signals は market_regime や ai_scores、features、positions 等のテーブルを参照します。DB 内のデータ整合性に注意してください。
- build_features / strategy 関数は DuckDB 接続を直接受け取り、クエリで必要なテーブルを読み書きします。
- J-Quants API 呼び出しにはトークン（JQUANTS_REFRESH_TOKEN）が必要です。設定がない場合は例外が発生します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 for Slack 通知)
- DUCKDB_PATH — ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite ファイル（既定: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（既定: development）
- LOG_LEVEL — DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを無効化

.env ファイルのパースはシェル風の記法に対応し、クォートやコメントの取り扱いに注意して読み込みます。.env.local は .env を上書きする優先度で読み込まれます。プロジェクトルートは .git または pyproject.toml を基準に検出されます。

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定だと Settings のプロパティで ValueError を投げます。README のサンプル .env を用意してください（.env.example を参照）。
- DuckDB のスキーマ初期化（tables）や前処理（raw_prices → prices_daily 等の ETL）はリポジトリ内の `data.schema` 等に依存します。バックテストやシグナル生成を行う前に DB テーブルが正しく準備されていることを確認してください。
- J-Quants API のレート制限（120 req/min）に合わせて内部でスロットリングを行います。大量データ取得時は実行時間に注意。
- ニュース収集は外部ネットワーク接続を行います。SSRF 対策やレスポンスサイズ上限を備えていますが、実行環境のネットワークポリシーに従ってください。
- 実運用（live）モードでは資金の実行・外部発注の扱いに十分注意してください。本リポジトリの execution/monitoring 部分は拡張ポイントとして設計されています。

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys 以下）

- __init__.py
  - パッケージ主要エクスポートの定義
- config.py
  - 環境変数読み込み・Settings クラス（アプリ設定）
- data/
  - jquants_client.py — J-Quants API クライアント、データ取得・保存機能
  - news_collector.py — RSS 収集、正規化、raw_news / news_symbols 保存
  - （schema.py 等はスキーマ初期化用）
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- strategy/
  - feature_engineering.py — features 作成・正規化・DB 保存
  - signal_generator.py — final_score 計算、BUY/SELL の生成・保存
- portfolio/
  - portfolio_builder.py — 候補選定・基礎重み計算
  - position_sizing.py — 株数算出ロジック（risk_based, equal, score）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- backtest/
  - engine.py — バックテストループ、データコピー、ポートフォリオ構築統合
  - simulator.py — 擬似約定ロジック、履歴・トレード記録
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
  - clock.py — 将来拡張用の模擬時計
- execution/, monitoring/, portfolio/（その他） — 実運用側の拡張ポイント

---

## 貢献・拡張ポイント

- execution 層の実装（kabu API との実売買連携）
- Slack / モニタリング強化（アラート、ダッシュボード連携）
- 銘柄別の lot_size 管理、手数料モデルの拡張
- AI スコアを投入する pipeline（ai_scores テーブルの自動更新）
- 分足シミュレーションのサポート（SimulatedClock の活用）

---

この README は本コードベースの主要機能・利用手順を簡潔にまとめたものです。詳細な設計仕様（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md 等）はプロジェクトのドキュメントルートを参照してください。問題や不明点があれば実行ログ（LOG_LEVEL=DEBUG）を確認し、該当モジュールの docstring / 関数コメントも参照してください。