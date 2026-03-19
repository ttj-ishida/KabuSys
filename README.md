# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
市場データの取得・ETL、特徴量算出、シグナル生成、ニュース収集、監査/実行レイヤーのスキーマ管理など、研究〜運用までのワークフローを想定したモジュール群を提供します。

主な目的
- J-Quants API などからのデータ取得と DuckDB への永続化（冪等化）
- 研究用ファクターの計算・正規化（ルックアヘッド回避を意識）
- 戦略シグナルの生成（スコアリング、Buy/Sell 判定、エグジット判定）
- ニュース収集と銘柄紐付け（RSS → raw_news / news_symbols）
- スキーマ・監査テーブルの初期化および運用ユーティリティ

---

## 機能一覧

- 環境設定管理
  - .env ファイルおよび OS 環境変数から設定をロード（自動ロードを無効化可）
- Data レイヤ
  - J-Quants API クライアント（レート制御 / リトライ / トークン自動更新）
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分更新、バックフィル、品質チェック呼び出し）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限/XML セーフガード）
  - 統計ユーティリティ（Z スコア正規化など）
  - マーケットカレンダー管理（営業日判定、next/prev/trading_days）
- Research / Strategy
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量構築（正規化・ユニバースフィルタ）
  - シグナル生成（final_score 計算、Bear レジーム対応、BUY/SELL の永続化）
  - 特徴量探索ユーティリティ（forward returns / IC / summary）
- Execution / Audit
  - 実行レイヤ用スキーマ（signal_queue / orders / trades / positions 等）
  - 監査ログテーブル定義（signal_events / order_requests / executions 等）
- ユーティリティ
  - ニュース中の銘柄抽出（既知の 4 桁コード）
  - HTTP リクエストの堅牢化（gzip 対応、サイズ制限、リダイレクト検査）

---

## 前提条件

- Python 3.10+
  - コードベースでの型ヒント（|）や標準ライブラリだけでの実装を前提にしています。
- 必要な Python パッケージ（一例）
  - duckdb
  - defusedxml

実際の依存はプロジェクトの packaging / pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

2. 必要パッケージをインストール
   （実プロジェクトでは pyproject.toml / requirements.txt を使ってください）
   ```bash
   pip install duckdb defusedxml
   # 開発用にパッケージを編集可能インストールする場合:
   pip install -e .
   ```

3. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数例：
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   デフォルトでは DUCKDB_PATH が `data/kabusys.duckdb`。Python REPL やスクリプトで初期化できます。
   ```python
   from kabusys.config import settings
   from kabusys.data import schema

   conn = schema.init_schema(settings.duckdb_path)
   # またはメモリ DB で試す:
   conn = schema.init_schema(":memory:")
   ```

---

## 使い方（代表例）

以下はライブラリの代表的な呼び出し例です。実運用では適切なジョブスケジューラやバッチ制御を組み合わせてください。

1. 日次 ETL の実行（株価・財務・カレンダー取得）
   ```python
   from datetime import date
   import logging
   from kabusys.data import pipeline, schema
   from kabusys.config import settings

   logging.basicConfig(level=settings.log_level)

   conn = schema.init_schema(settings.duckdb_path)
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量の構築（features テーブルへ保存）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   count = build_features(conn, target_date=date(2025, 1, 31))
   print(f"features upserted: {count}")
   ```

3. シグナル生成（signals テーブルへ保存）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import generate_signals
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   num_signals = generate_signals(conn, target_date=date(2025, 1, 31))
   print(f"signals written: {num_signals}")
   ```

4. ニュース収集と保存
   ```python
   import duckdb
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   # known_codes: 既知の銘柄コード集合（news の銘柄抽出用）
   known_codes = {"7203", "6758", ...}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. J-Quants からのデータ取得（個別利用）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.get_connection(settings.duckdb_path)
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   print(f"saved: {saved}")
   ```

6. スキーマの再初期化（開発時）
   - 既存 DB のバックアップ後に `init_schema()` を呼び出してください。init_schema は既存テーブルがあればスキップして安全に実行できます。

---

## 設定（自動読み込みについて）

- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探して `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数を設定：
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須環境変数が未設定の場合、Settings プロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       — RSS ニュース取得・保存、銘柄抽出
    - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — data.stats のインターフェース再エクスポート
    - calendar_management.py  — market_calendar 管理、営業日ヘルパー、カレンダー更新ジョブ
    - audit.py                — 監査ログ（signal_events, order_requests, executions）
    - quality.py?             — 品質チェックモジュール（pipeline から参照、存在が想定される）
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility ファクター計算
    - feature_exploration.py  — forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py     — final_score 計算・BUY/SELL 判定・signals 保存
  - execution/
    - __init__.py             — 実行レイヤ（発注ラッパー等はこの下に実装される想定）
  - monitoring/               — 監視・アラート用モジュール（DBやSlack通知など。実装想定）
  - その他ドキュメント（DataPlatform.md / StrategyModel.md 等を参照する想定）

※ 上記はコードベースの主要モジュールを抜粋したものです。詳細は各モジュールの docstring を参照してください。

---

## 開発 / テストのヒント

- 単体テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存を排除できます。
- DuckDB の一時接続として `":memory:"` を使うと高速にテストが可能です。
- jquants_client のネットワーク呼び出しは外部依存があるため、テストではモック（関数差し替え）して検証してください（例: _urlopen / _request のモック）。

---

## 注意点（運用上のポイント）

- J-Quants API のレート制限（120 req/min）に従うよう内部で RateLimiter を実装しています。独自に並列化すると制限を越える恐れがあります。
- ETL は差分取得とバックフィルを組み合わせてデータの後出し修正を吸収する設計です。運用ポリシーに応じて backfill_days を調整してください。
- features / signals 等は日付単位で DELETE→INSERT の置換処理を行い原子性を確保しています（トランザクション使用）。
- ニュース取得では SSRF・XML Bomb・巨大レスポンス等へ対策を組み込んでいますが、運用環境ではネットワーク制御やフィードホワイトリストを運用してください。

---

必要に応じて README を拡張します（例: CI 設定、デプロイ手順、監視・アラート設定、実運用での安全対策）。どの項目を追加したいか教えてください。