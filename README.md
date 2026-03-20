# KabuSys

日本株の自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。  
主に次の責務を持ちます：

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータストアとスキーマ定義
- ETL パイプライン（差分取得・保存・品質チェック）
- 特徴量（features）生成・正規化
- 戦略に基づくシグナル生成（BUY/SELL）
- RSS ベースのニュース収集と銘柄紐付け
- 市場カレンダー管理（営業日計算など）
- 監査ログ（signal → order → execution のトレース）
- 研究用ユーティリティ（IC、forward returns、factor summary 等）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「API レート制御」「トレーサビリティ」を重視しています。

---

## 機能一覧（主なもの）

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（run_daily_etl 等）、差分取得ロジック
  - schema: DuckDB スキーマ初期化（init_schema）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定 / next/prev trading day / calendar 更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: zscore_normalize の公開インターフェース
  - audit: 監査ログ用のテーブル定義
- research/
  - factor_research: Momentum / Value / Volatility 等ファクター計算
  - feature_exploration: 将来リターン、IC、ファクターサマリ
- strategy/
  - feature_engineering.build_features: features テーブル構築（正規化・クリップ・UPSERT）
  - signal_generator.generate_signals: features + ai_scores を統合してシグナル作成
- config: .env / 環境変数の読み込みと Settings（必須トークン等）
- execution, monitoring: 発注や監視周りの層（パッケージ構成は用意）

---

## 必要条件（Prerequisites）

- Python 3.10 以上（コードで | 型や型ヒントを使用）
- 必要パッケージ（主に）:
  - duckdb
  - defusedxml
- 標準ライブラリのみで動く部分も多いですが、実行環境では上記をインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要であれば他の依存を追加
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（主なもの）

設定は .env または OS 環境変数から読み込まれます（config.py）。自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出して .env, .env.local を読みます。自動読み込み無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack 通知チャンネル

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring 用)（デフォルト: data/monitoring.db）

注意: Settings クラスのプロパティは必須変数が未設定だと例外を投げます。

---

## セットアップ手順（ローカル起動例）

1. リポジトリをクローン・作業ディレクトリへ移動
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（duckdb, defusedxml など）
4. .env を作成して必要な環境変数を設定（上記参照）
   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. DuckDB スキーマ初期化（Python REPL やスクリプトで実行）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)
   ```
   - ":memory:" を指定するとインメモリ DB として動作します。
6. （オプション）最初の ETL 実行でデータを取得
   - J-Quants API アクセスに必要なトークンが設定されていることを確認してください。

---

## 使い方（代表的なワークフロー）

以下は代表的な処理の実行例（Python スクリプト／REPL）です。

- DuckDB 接続の作成 / スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回: スキーマ作成
conn = init_schema(settings.duckdb_path)

# 既存 DB へ接続する場合
# conn = get_connection(settings.duckdb_path)
```

- 日次 ETL の実行（市場カレンダー、株価、財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）構築
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: {'7203', '6758', ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
print(res)
```

- J-Quants の低レベル取得（必要に応じて）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
```

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス回避のため、すべての戦略・特徴量計算は target_date 時点までの情報のみを使用する設計です。
- DuckDB への保存は冪等性（ON CONFLICT）を意識した実装になっています。
- J-Quants API はレート制限に従って固定間隔スロットリングで呼び出します（120 req/min）。
- ニュース収集は SSRF や XMLBomb 対策（SSRF リダイレクト検査、defusedxml、レスポンスサイズ制限など）を施しています。
- 環境により発注層（execution）と監視層（monitoring）は別実装または外部の橋渡しが必要です（このコードベースは基盤を提供）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ宣言
  - config.py — 環境変数読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - news_collector.py — RSS 収集 / 保存 / 銘柄抽出
    - calendar_management.py — market_calendar 管理 / 営業日ロジック
    - features.py — features 公開インターフェース（zscore_normalize）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログテーブル定義
    - quality.py — （参照されるが省略されている場合あり、品質チェック実装想定箇所）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py — forward returns, IC, factor summary, rank
  - strategy/
    - __init__.py — build_features, generate_signals を公開
    - feature_engineering.py — features 構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals 生成・書込
  - execution/ — 発注周りの層（現状空パッケージ）
  - monitoring/ — 監視周り（現状空パッケージ）
- pyproject.toml / setup.py 等（該当する場合）

---

## 開発・運用時のヒント

- 自動で .env を読み込む仕組みがありますが、テストや CI で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスは Settings.duckdb_path で指定できます。CI や単体テストでは `":memory:"` を使うと便利です。
- J-Quants のトークンは期限切れになった場合に自動でリフレッシュ処理を行います（get_id_token / _request の実装に基づく）。
- ETL は段階ごとに独立したエラーハンドリングが行われます（1工程の失敗が全体停止を引き起こさない設計）。

---

## ライセンス・貢献

（このリポジトリに LICENSE があればその内容を記載してください。ここでは省略しています。）

貢献方法やバグ報告、機能リクエストは Issue / Pull Request を通じてお願いします。

---

以上が本コードベースの README.md に含める主要情報です。必要ならば、セットアップ・運用手順のサンプルスクリプトや .env.example のテンプレート、CI 用の起動コマンドなどを追記します。どの部分を補足したいか教えてください。