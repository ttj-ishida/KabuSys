# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けのデータプラットフォーム / 戦略モジュール群です。J-Quants からの市場データ取得、DuckDB を用いたデータ管理、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注/監査のためのスキーマなどを含みます。設計は「ルックアヘッドバイアス防止」「冪等性」「テスト容易性」を重視しています。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須項目の取得メソッドを提供（`kabusys.config.settings`）

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）のページネーション対応取得・保存
  - 財務データの取得・保存
  - JPX マーケットカレンダー取得・保存
  - リトライ / トークン自動リフレッシュ / レート制限制御

- データベース（DuckDB）スキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義
  - スキーマ初期化（冪等）

- ETL パイプライン
  - 差分取得（最終取得日ベース）＋バックフィル
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 各ジョブは個別に実行可能

- 研究（research）モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリ

- 特徴量エンジニアリング
  - 生ファクターのマージ、ユニバースフィルタ、Zスコア正規化、クリッピング、features テーブルへの UPSERT

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム検出による BUY 抑制
  - BUY / SELL シグナルの判定と signals テーブルへの書き込み（冪等）

- ニュース収集
  - RSS 取得（SSRF 対策、gzip/サイズ上限、XML 脆弱性対策）
  - 記事ID の正規化（URL 正規化 → SHA256）
  - raw_news / news_symbols への冪等保存
  - テキスト前処理、銘柄コード抽出（4桁）

- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日列挙
  - カレンダー更新バッチ（バックフィル、健全性チェック）

- 監査（audit）スキーマ（Signal → Order → Execution のトレーサビリティ）

---

## セットアップ手順

前提:
- Python 3.10 以上推奨（typing のユニオン | を使用しているため）
- DuckDB を使用するため duckdb パッケージが必要
- defusedxml（RSS パースの安全化）など一部依存がある

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境の作成と有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows: .venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクト化されている場合）pip install -e .

   ※ requirements.txt 等が付属している場合はそちらを使用してください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くことで自動読み込みされます（既存 OS 環境変数は保護）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: データベースファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - 自動 .env 読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化
   - 下記「使い方」参照。

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから利用する基本例です。すべて DuckDB の接続（kabusys.data.schema.init_schema / get_connection）を介して操作します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成されます
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
print(result.to_dict())
```

3) 特徴量の構築（ある日付に対して）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date(2025, 1, 1))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

n_signals = generate_signals(conn, date(2025, 1, 1), threshold=0.6)
print(f"signals written: {n_signals}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9432"}  # 有効銘柄コードセット（DB 等から取得）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar records saved: {saved}")
```

7) テスト・デバッグ用
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB をメモリモードで使う: init_schema(":memory:")

---

## 主要モジュール（短い説明）

- kabusys.config
  - 環境変数読み込み / settings オブジェクト提供

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得・保存関数含む）
  - schema.py: DuckDB スキーマ定義と init_schema
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 収集と raw_news 保存、銘柄抽出
  - calendar_management.py: カレンダー判定・更新ロジック
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - features.py: zscore_normalize の再エクスポート
  - audit.py: 監査（signal_events / order_requests / executions など）スキーマ

- kabusys.research
  - factor_research.py: mom / vol / value 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ
  - research/__init__.py: 研究用ユーティリティの公開

- kabusys.strategy
  - feature_engineering.py: 生ファクターの正規化・フィルタ・features への保存
  - signal_generator.py: features と ai_scores 統合 → BUY/SELL シグナル生成

- kabusys.execution / kabusys.monitoring
  - プレースホルダ（将来の発注・監視ロジックを想定）

---

## ディレクトリ構成（抜粋）

（プロジェクトの src ディレクトリを想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - stats.py
    - features.py
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
  - monitoring/
    - (将来の監視コード)

---

## 環境変数の主な一覧

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (発注連携を行う環境で必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須: Slack 通知を使う場合)
- SLACK_CHANNEL_ID (必須: Slack 通知を使う場合)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live, デフォルト development)
- LOG_LEVEL (DEBUG/INFO/...)

.env ファイルはプロジェクトルートに置くことで自動読み込みされます。読み込みロジックはシェル風の export 付き行、クォート、コメント等に対応しています。

---

## ロギング・トラブルシューティング

- LOG_LEVEL を DEBUG に設定すると詳細ログが得られます。
- J-Quants API の 401 は自動リフレッシュ処理を試行します。連続して失敗する場合は JQUANTS_REFRESH_TOKEN を確認してください。
- RSS の取得では SSRF 対策のため private ホストや非 http(s) スキームを拒否します。フィード URL を確認してください。
- DuckDB のスキーマ初期化でエラーが出る場合、ファイルパスやディレクトリの権限を確認してください。

---

## 開発メモ / 設計方針（要点）

- ルックアヘッドバイアスを避けるため、すべての計算は target_date 時点で利用可能なデータのみを使用します。
- DB への保存は可能な限り冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で実装。
- ネットワーク呼び出しはレート制限・リトライ・トークンリフレッシュを実装。
- 外部依存は最小化（標準ライブラリ + 必要最小限の外部パッケージ）。
- テスト容易性のため、id_token や HTTP 呼び出し部分は注入・モック可能な設計。

---

必要であれば、README に含める CI 手順、example .env.example、またはより詳細な API リファレンス（関数別の使用例やパラメータ説明）を追記します。どの情報を追加しますか？