# KabuSys

日本株向けの自動売買システム用ライブラリ（研究・データ基盤・戦略・バックテスト・ETL を含む）。  
このリポジトリは DuckDB をデータストアとして利用し、J-Quants API や RSS フィードからデータ収集、特徴量計算、シグナル生成、バックテストまでの主要機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## 機能一覧

主な機能・モジュール

- config
  - 環境変数の読み込み（.env / .env.local の自動ロード, KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
  - settings オブジェクトでアプリケーション設定を取得（必須環境変数の検証含む）

- data
  - jquants_client: J-Quants API クライアント（認証、ページネーション、レート制御、保存関数）
  - news_collector: RSS 取得・前処理・DB保存（SSRF対策、ID生成、銘柄抽出）
  - schema: DuckDB スキーマ定義 / 初期化（init_schema）
  - pipeline: ETL ワークフロー（差分取得、バックフィル、品質チェック）
  - stats: 汎用統計ユーティリティ（Zスコア正規化など）

- research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）など解析ユーティリティ

- strategy
  - feature_engineering.build_features: 生ファクターを統合・正規化して features テーブルへ書き込み
  - signal_generator.generate_signals: features と ai_scores を統合し BUY/SELL シグナルを生成

- backtest
  - engine.run_backtest: DuckDB データをコピーしてインメモリで日次バックテストを実行
  - simulator.PortfolioSimulator: 約定・ポジション管理のシミュレータ
  - metrics.calc_metrics: バックテストの評価指標計算
  - run: CLI エントリーポイント（python -m kabusys.backtest.run）

- execution / monitoring
  - 発注や監視に関する名前空間を想定（このスニペット群では行数のみ示唆）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、常に target_date 時点までのデータのみを使用
- DuckDB を中心とした SQL + Python 実装（外部 heavy ライブラリ依存を最小化）
- 冪等性（ON CONFLICT / トランザクション）とエラーハンドリングを重視

---

## 必要要件

- Python 3.10 以上（typing の `|` 記法や型ヒントに依存）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, logging, datetime, math など）

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または要件ファイルがあれば: pip install -r requirements.txt
```

---

## 環境変数

config.Settings を通じて参照される主要な環境変数:

必須（設定がないと ValueError が発生します）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動読み込みを無効)
- KABUSYS_API_BASE_URL（kabu API のベース URL、デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（データベースのデフォルトパス、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DBパス、デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から .env を自動で読み込みます。
- 読み込み優先順: OS環境変数 > .env.local > .env
- 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成と依存ライブラリのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # もし requirements.txt があれば:
   # pip install -r requirements.txt
   ```

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を設定してください。
   - 必須項目（上記参照）を必ず設定してください。

4. DuckDB スキーマ初期化
   Python REPL もしくはスクリプトで init_schema を呼び出します（デフォルトパスを指定する場合はそのパスを使用）。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   conn.close()
   ```

---

## 使い方（代表的な例）

- バックテスト CLI（推奨）
  DuckDB データベースに prices_daily, features, ai_scores, market_regime, market_calendar が揃っていることが前提です。
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb
  ```

- プログラムからバックテストを実行（API）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  # 結果の参照
  print(result.metrics)
  ```

- ファクター / 特徴量作成
  build_features を使って features テーブルを作成（target_date を指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,1,31))
  print(f"upserted {count} features")
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  print(f"Generated {n} signals for 2024-01-31")
  conn.close()
  ```

- J-Quants からの差分 ETL（価格）
  pipeline.run_prices_etl などの関数を利用して差分取得→保存を行います（id_token 注入可能）。
  （例はドキュメント内の関数定義を参照してください）

- ニュース収集（RSS）
  news_collector.run_news_collection を使って RSS から記事を収集し、raw_news / news_symbols に保存します。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - metrics.py
    - simulator.py
    - clock.py
    - run.py  (CLI)
  - execution/          (発注関連の名前空間)
  - monitoring/         (監視関連の名前空間)

上記以外にも細かいユーティリティや補助モジュールが含まれます。詳細は各モジュールの docstring を参照してください。

---

## 開発者向けメモ / 注意点

- Python 3.10+ が要件です（型ヒントの記法に依存）。
- DuckDB はネイティブな型チェックやトランザクションを活用します。init_schema は初回に全テーブルとインデックスを作成します。
- jquants_client は API レート制限（120 req/min）を内部で制御し、401 受信時は refresh token から自動リフレッシュを試みます。
- news_collector は SSRF・XML Bomb 対策（defusedxml、リダイレクト検査、サイズ上限）を実装しています。
- ETL は差分取得・バックフィルロジックを持ち、品質チェック（quality モジュール）と併用する想定です（品質チェックは呼び出し元で処理判断）。

---

問題報告・貢献
- バグ報告や改善提案は issue を作成してください。プルリクエスト歓迎です。

---

README は以上です。必要であれば、具体的な ETL / DB 初期化手順や .env.example のテンプレート、CI 用設定例などを追加で作成します。どの情報を優先して追加しましょうか？