# KabuSys

日本株向けの自動売買システム用ライブラリ（ミニマム実装）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集、簡易ポートフォリオシミュレータなどを含みます。

Note: この README はリポジトリ内のソースコード（src/kabusys 以下）に基づいて作成しています。

---

## 主要な特徴

- データ取得
  - J-Quants API クライアント（レートリミット制御・リトライ・トークン自動リフレッシュ）
  - JPX マーケットカレンダー、株価、財務データ取得
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックのフレームワーク
  - DuckDB への冪等保存（ON CONFLICT ベース）
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成、証券コード抽出、SSRF 対策、Gzip/サイズ制限
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- 戦略（strategy）
  - 特徴量構築（正規化・ユニバースフィルタ）
  - シグナル生成（最終スコア計算・BUY/SELL判定・Bear抑制）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループによるシミュレーション、メトリクス計算（CAGR, Sharpe, Max DD 等）
  - CLI エントリポイントあり
- データスキーマ管理
  - DuckDB スキーマ定義と初期化ユーティリティ

設計方針の抜粋:
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点の情報のみを使用
- 冪等性（DB保存は ON CONFLICT / DO UPDATE または DO NOTHING）
- 外部依存を最小化（研究系ユーティリティは標準ライブラリのみで実装）

---

## 要求環境

- Python 3.9+（ソースは型ヒントに最新構文を含みます）
- 主要依存ライブラリ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス：J-Quants API / RSS フィード取得時

依存はプロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。ない場合は最低限 duckdb と defusedxml をインストールしてください。

例:
```bash
python -m pip install duckdb defusedxml
```

---

## 環境変数（.env）

自動的にプロジェクトルートの `.env` / `.env.local`（存在すれば）をロードします（挙動は `kabusys.config` を参照）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（実行機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

オプション:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   python -m pip install -U pip
   python -m pip install duckdb defusedxml
   ```
4. 必要な環境変数を `.env` に設定（上記参照）
5. DuckDB スキーマを初期化
   Python REPL やスクリプトから:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - `:memory:` を指定するとインメモリ DB を初期化できます（テスト用）。

---

## 使い方（代表的な例）

- バックテスト（CLI）
  - データベースに必要なテーブル（prices_daily / features / ai_scores / market_regime / market_calendar 等）が事前に入っていることが前提です。
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db data/kabusys.duckdb
  ```
  出力にバックテストの主要メトリクスを表示します。

- DuckDB スキーマ初期化（スクリプト）
  ```py
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 必要な初期データを投入したら閉じる
  conn.close()
  ```

- J-Quants からデータを取得して保存（例）
  ```py
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL（株価差分ETL の呼び出し例）
  ```py
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

- 特徴量構築 / シグナル生成（プログラムから）
  ```py
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features, generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")

  build_features(conn, target_date=date(2024, 1, 31))
  generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- ニュース収集
  ```py
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

- バックテストを Python API から実行
  ```py
  from datetime import date
  import duckdb
  from kabusys.backtest.engine import run_backtest

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py — 環境変数・設定管理（.env 自動ロード・Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 取得・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema()
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分更新・品質チェック）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン・IC・サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター正規化・features テーブル書込
    - signal_generator.py — final_score 計算・signals 書込
  - backtest/
    - __init__.py
    - engine.py — run_backtest の実装（全体ループ）
    - simulator.py — PortfolioSimulator、DailySnapshot、TradeRecord
    - metrics.py — バックテスト評価指標計算
    - clock.py — SimulatedClock（将来拡張用）
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
  - execution/  — 発注/約定層（現在はパッケージのプレースホルダ）
  - monitoring/ — 監視関連（プレースホルダ）

（実際のファイル一覧はリポジトリの src/kabusys ディレクトリを参照してください）

---

## 実装上の注意点 / 運用メモ

- J-Quants のレート制限（120 req/min）を厳守するため、クライアントは固定間隔のスロットリングを行います。
- fetch API はページネーションに対応し、ページ間でトークンキャッシュを共有します。
- news_collector は SSRF 対策（リダイレクト検査・プライベートIP拒否）と受信サイズ上限を実装しています。
- research モジュールは外部ライブラリに依存しない設計のため、大規模データ処理の際は性能に注意してください（DuckDB 側で SQL を効率的に使う設計です）。
- バックテストは本番 DB を汚さないため、内部でインメモリ DuckDB にデータをコピーして実行します。
- features / signals / positions 等は日付単位で「DELETE + INSERT」の置換を行い冪等性を保っています（トランザクション利用）。

---

## トラブルシューティング

- .env がロードされない:
  - プロジェクトルートの判定は `config._find_project_root()` により `.git` または `pyproject.toml` を探しています。テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自分で環境を制御できます。
- J-Quants API の 401 が返る:
  - refresh token の期限切れなどが考えられます。`JQUANTS_REFRESH_TOKEN` を再確認してください。クライアントは 401 時にトークンを1回リフレッシュして再試行します。
- DuckDB のスキーマ初期化でエラー:
  - 既存の DB が壊れている可能性があります。バックアップを取り、`init_schema(":memory:")` で動作確認してからファイルベースに適用してください。

---

## 貢献 / 拡張ポイント

- execution 層：実際の発注（kabuステーション API 連携）実装
- monitoring：Slack/Prometheus 等を使った運用監視・アラート
- AI スコアリング：ai_scores テーブルを生成する外部プロセス（未実装の例あり）
- テスト：各モジュールのユニットテスト追加（特にネットワーク部はモック化）

---

以上。必要であれば README に含めるサンプルコードや手順（Docker 化、CI 設定、さらに詳細な DB 初期データの用意手順など）を追記します。どの部分を優先して拡充しますか？