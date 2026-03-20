# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマなどを含むモジュール群です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API から市場データ・財務データ・市場カレンダーを取得して DuckDB に保存する（ETL）
- 研究（research）で得た生ファクターを正規化・合成して戦略用特徴量（features）を作成
- features と AI スコアを統合して売買シグナルを生成（BUY/SELL の判定、エグジット条件の判定）
- RSS からニュースを収集して raw_news / news_symbols に保存
- DuckDB のスキーマ定義・初期化・接続を提供
- 環境変数による設定管理（.env 自動ロード対応）

設計上の方針として、ルックアヘッドバイアス回避（target_date 時点のみを参照）、冪等性（ON CONFLICT / トランザクション）、ネットワーク周りの堅牢性（リトライ・レート制限・SSRF 対策）を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（jquants_client）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
  - ETL パイプライン（data.pipeline）
    - 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - スキーマの初期化（data.schema.init_schema）
- データ品質・カレンダー管理
  - market_calendar 操作（data.calendar_management）
- ニュース収集
  - RSS 取得と前処理（data.news_collector）
  - raw_news / news_symbols への保存（重複排除、SSRF・XML 安全対策）
- 研究用ファクター計算（research.factor_research）
  - momentum / volatility / value ファクター計算
  - forward returns / IC / factor summary（research.feature_exploration）
- 特徴量作成とシグナル生成（strategy）
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- 汎用統計ユーティリティ
  - zscore_normalize（data.stats）
- 環境設定管理（config）
  - .env 自動ロード（プロジェクトルート検出、.env / .env.local）
  - 必須環境変数アクセス via settings

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに `X | None` を使用しているため）
- duckdb, defusedxml などが必要

推奨手順（ローカル開発）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   例（minimal）:
   ```
   pip install duckdb defusedxml
   ```
   またはパッケージが pip に公開されている場合/プロジェクトに requirements ファイルがある場合はそちらを使用してください。
4. 開発インストール（プロジェクトパッケージを editable にする）
   ```
   pip install -e .
   ```
   （pyproject.toml / setup.cfg がある場合）

環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（config モジュールがルートを .git または pyproject.toml から検出します）。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API 用パスワード（execution 層で使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（optional だが設定が要求されるプロジェクト箇所あり）
- SLACK_CHANNEL_ID : Slack チャンネル ID
- 任意：
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

例 .env（雛形）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API とサンプル）

以下は代表的な利用例です。すべての処理は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量ビルド（strategy.feature_engineering.build_features）
```python
from datetime import date
from kabusys.strategy import build_features
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

4) シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
written = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals generated: {written}")
```

5) ニュース収集ジョブ（RSS 収集 -> raw_news 保存 -> 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効銘柄コードセット（抽出に使用）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # ソース名 -> 新規保存件数
```

6) J-Quants API クライアントを直接使う
```python
from kabusys.data import jquants_client as jq
# トークンを明示的に渡すことも、settings のトークンを使うことも可能
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

注意点:
- 各日付ベースの処理（feature build / signal generate）は target_date 時点の情報のみを参照する設計です（ルックアヘッドバイアス回避）。
- 各テーブルへの書き込みは日付単位の置換（DELETE + bulk INSERT）やトランザクションで原子性を担保しています。
- ETL の差分取得機能は DB 側の最終取得日を基に date_from を計算します。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の `src/kabusys` 以下の主要モジュールを抜粋します。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動ロード / Settings
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
    - news_collector.py         — RSS 収集・正規化・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義・init_schema
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — market_calendar 管理・営業日ロジック
    - features.py               — data.stats の再エクスポート
    - audit.py                  — 発注/約定の監査テーブル定義（トレーサビリティ）
  - research/
    - __init__.py
    - factor_research.py        — momentum / volatility / value の計算
    - feature_exploration.py    — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py    — 生ファクターの統合・正規化 -> features テーブル
    - signal_generator.py       — final_score 計算 -> signals テーブル挿入
  - execution/                   — execution 層（発注ロジック等）用ディレクトリ（空の __init__ 等）
  - monitoring/                  — 監視・アラート関連（別途実装想定）

各モジュールは docstring と関数コメントで設計意図・前提を明確にしているため、実装の読みやすさ・保守性に配慮しています。

---

## 環境・挙動に関する補足

- .env 自動ロード:
  - プロジェクトルートは `__file__` を起点に上方探索し、`.git` または `pyproject.toml` を見つけたディレクトリをルートとします。
  - 読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化できます。
- ログレベル: `LOG_LEVEL` 環境変数で制御（DEBUG/INFO/WARNING/...）。
- 環境（runtime）: `KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかで、動作切替に利用できます。
- API レート制御: J-Quants クライアントは 120 req/min を守るための内部 RateLimiter を備えています。リトライや 401（トークン更新）処理も実装されています。
- セキュリティ:
  - ニュース収集は SSRF 対策（リダイレクトホストチェック、私的アドレス判定）、XML の安全パーサ（defusedxml）を使用。
  - DB 層での冪等性（ON CONFLICT）・トランザクション処理を多用。

---

## 参考・次のステップ

- テーブル定義や DataPlatform.md / StrategyModel.md などの設計ドキュメントに沿っているため、本 README の例を起点に機能を統合してください。
- 運用時は KABUSYS_ENV を適切に設定し、テスト用の paper_trading / development 環境で十分に検証してから live で運用してください。
- 実際の発注（execution）や Slack 通知などのインテグレーションはプロジェクト固有の機能と結びつくため、個別に設定と検証が必要です。

---

問題や追加で README に載せたい情報（CI、テスト、依存バージョン固定、実運用ガイド等）があれば教えてください。それに合わせて追記・修正します。