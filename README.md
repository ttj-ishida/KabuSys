# KabuSys

日本株自動売買プラットフォーム（KabuSys）のライブラリです。  
データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注監査など、戦略運用に必要なコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の関心領域を分離したモジュール群で構成された日本株向け自動売買システムのライブラリです。

- データ層（J‑Quants からの生データ取得・DuckDB 保存）
- データ品質チェック・ETL パイプライン
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量（features）生成と正規化
- シグナル生成（final_score を計算して BUY/SELL を決定）
- ニュース収集・銘柄紐付け（RSS）
- マーケットカレンダー管理（JPX）
- 発注・実行・監査用スキーマ（DuckDB）

設計方針としては「ルックアヘッドバイアス回避」「冪等性（idempotency）」「外部 API のレート制御/リトライ」「DB トランザクションでの原子性」などを重視しています。

---

## 主な機能一覧

- J‑Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ対応
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン
  - 差分更新 / バックフィル / 品質チェック
- 研究用ファクター計算
  - momentum（1M/3M/6M/MA200乖離）
  - volatility（ATR20、出来高比率）
  - value（PER、ROE）
  - forward returns / IC / 統計サマリー
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（final_score による BUY/SELL、Bear レジーム抑制、ストップロス等）
- ニュース収集（RSS → raw_news、記事ID正規化、銘柄抽出）
- マーケットカレンダー管理（営業日判定 / prev/next_trading_day）
- 監査ログ（signal_events / order_requests / executions 等のスキーマ）

---

## 必要条件・依存関係

- Python 3.9+（typing の一部で | 型注釈を使用）
- duckdb
- defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある想定です。ローカル環境では仮想環境を推奨します。）

---

## セットアップ手順

1. リポジトリをクローン、もしくはパッケージをチェックアウトします。

2. 仮想環境を作成・有効化（例）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール:
   - pip を使う場合:
     ```bash
     pip install duckdb defusedxml
     # もし pyproject.toml や requirements.txt があれば:
     pip install -e .
     ```
   - 必要に応じてプロジェクトの packaging に従ってインストールしてください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込みの無効化 (1)
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化:
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     ```
   - 上記はデフォルトで `data/` ディレクトリを作成します。

---

## 使い方（簡単な例）

以下は代表的な処理の呼び出し例です。実運用ではログ・例外ハンドリング・ジョブスケジューラ（cron / airflow 等）を組み合わせて運用してください。

- DB 初期化（上で紹介）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行（prices / financials / calendar を差分取得）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- マーケットカレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- ニュース収集ジョブ（既知銘柄セットを渡すと news_symbols まで作成）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)
  ```

- 特徴量生成（features テーブルの作成）:
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date.today())
  print("features built:", count)
  ```

- シグナル生成:
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, date.today())
  print("signals:", total_signals)
  ```

- J‑Quants からの生データ取得（低レベル呼び出し例）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

---

## 注意点 / 運用時のポイント

- 環境変数が不足していると Settings のプロパティ（settings.jquants_refresh_token 等）で ValueError が発生します。ETL 等を実行する前に必須変数を設定してください。
- J‑Quants API のレート制限（120 req/min）に対応する RateLimiter 実装があります。大量の銘柄取得時はページネーションに注意してください。
- ETL や DB への書き込みは冪等性を意識して設計されています（ON CONFLICT / トランザクション）。
- テーブル設計では DuckDB のバージョンによる外部キー機能の差異（ON DELETE CASCADE 等）がコメントされています。運用時は DuckDB のバージョンに合わせた運用ルールを確立してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下のモジュールで構成されています。主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py        — J‑Quants API クライアント（fetch/save）
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl など）
    - news_collector.py        — RSS ニュース収集・DB保存・銘柄抽出
    - calendar_management.py   — マーケットカレンダーの操作・更新ジョブ
    - audit.py                 — 発注・実行の監査ログ用スキーマ
    - features.py              — features のユーティリティ公開（zscore）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - quality.py               — （品質チェックモジュール 想定: pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py       — momentum / volatility / value の計算
    - feature_exploration.py   — forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py   — features を作成して features テーブルに保存
    - signal_generator.py      — final_score を計算して signals を生成
  - execution/                 — 発注実行関連（プレースホルダ）
  - monitoring/               — 監視・モニタリング関連（プレースホルダ）

（実際のリポジトリでは他にも補助モジュールやテストが配置されている可能性があります。）

---

## 開発・テスト時のヒント

- settings は環境変数ベースなので、ユニットテストでは os.environ を直接操作するか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを止め、テスト用の環境を注入してください。
- network / I/O を含むモジュール（jquants_client.fetch_*、news_collector.fetch_rss など）はモックやスタブを使ってテストすることを推奨します。news_collector 内部の _urlopen は差替え可能（テスト時にモック）。
- DuckDB の ":memory:" を使うとインメモリ DB でスピーディにテストできます（init_schema(":memory:")）。

---

## ライセンス・貢献

（ライセンス情報や貢献ルールがあればここに追記してください。）

---

この README はコードベースの主要点をまとめたものです。詳細な設計仕様はリポジトリ内の各種ドキュメント（DataPlatform.md / StrategyModel.md / Research 文書等）を参照してください。質問や補足ドキュメントの作成が必要であれば教えてください。