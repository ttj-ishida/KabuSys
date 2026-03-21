KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ収集、特徴量生成、シグナル生成、および発注/監査ログのための基盤ライブラリ群です。  
主に以下の層を含みます。

- Data Layer：J-Quants からのデータ取得、DuckDB での永続化、ニュース収集、カレンダー管理、ETL パイプライン
- Research Layer：ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- Strategy Layer：特徴量を統合してシグナル（BUY/SELL）を生成
- Execution / Audit：発注フロー・監査ログ（スキーマ含む。発注実装はレイヤを分離）

主な設計方針
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（ON CONFLICT / トランザクションでの置換）
- API レート制御・リトライ・トークン自動更新
- DuckDB を中心とした軽量かつ自己完結なデータ基盤

機能一覧
-------
主な機能（モジュール単位）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV（development / paper_trading / live）管理
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御、再試行、ページネーション、保存ユーティリティ）
  - schema: DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - pipeline: 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・記事保存・銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定・更新ジョブ
  - stats / features: Z スコア正規化等の統計ユーティリティ
  - audit: 発注〜約定のトレーサビリティ用スキーマ定義
- kabusys.research
  - factor_research: mom/vol/val 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC、統計サマリ
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの正規化・features テーブルへの保存
  - signal_generator.generate_signals: features / ai_scores を統合して BUY/SELL シグナル作成
- その他
  - 安全対策（RSS の SSRF 対策、defusedxml 使用、レスポンスサイズ制限など）
  - ログ出力・例外ハンドリング・トランザクション整合性

セットアップ手順
--------------
前提
- Python 3.10 以上（型アノテーションの | を使用）
- DuckDB を利用するためのネイティブ環境

推奨パッケージ（最低限）
- duckdb
- defusedxml

例（仮想環境を使用）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （パッケージ管理ファイルがある場合は pip install -e . など）

環境変数 / .env
- 自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env と .env.local を読み込みます。
- 自動ロードを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=＜your_jquants_refresh_token＞
- KABU_API_PASSWORD=＜kabu_api_password＞
- SLACK_BOT_TOKEN=＜slack_bot_token＞
- SLACK_CHANNEL_ID=＜slack_channel_id＞

任意 / デフォルト
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

簡単な .env 例
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

使い方（コード例）
-----------------

1) データベース初期化
```python
from kabusys.data.schema import init_schema
# ファイル DB を初期化（必要な親ディレクトリを自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

3) 特徴量構築（target_date に対して features を作成）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 7))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, date(2025, 1, 7))
print(f"signals written: {n_signals}")
```

5) ニュース収集ジョブ（RSS 取得・保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes: 銘柄抽出に使う有効コード集合（例: 全上場銘柄のコードセット）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(results)
```

6) 市場カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar entries saved: {saved}")
```

7) 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)  # KABUSYS_ENV が 'live' の場合 True
```

注意点と運用上のヒント
- run_daily_etl は複数ステップ（カレンダー→株価→財務→品質チェック）を順に実行し、各ステップは個別に例外処理されます。結果は ETLResult にまとめられます。
- features / signals の書き込みは日付単位で DELETE → INSERT の置換を行い冪等性を保ちます。
- generate_signals は Bear レジーム検出により BUY を抑制するロジックを持ちます。weights パラメータで各コンポーネント重みを調整できます（合計は自動的に正規化されます）。
- RSS フェッチには SSRF 対策や受信サイズ上限などの安全処理が含まれています。

ディレクトリ構成（抜粋）
---------------------
以下はパッケージ内の主要ファイル/ディレクトリ（src/kabusys）です。小さいユーティリティやテストは省略しています。

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント + 保存ユーティリティ
    - schema.py                        # DuckDB スキーマ定義・初期化
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - news_collector.py                # RSS 収集・保存・銘柄抽出
    - calendar_management.py           # 市場カレンダー管理
    - features.py                       # data.stats の再エクスポート
    - stats.py                          # zscore_normalize 等
    - audit.py                          # 監査ログスキーマ
    - ... (その他)
  - research/
    - __init__.py
    - factor_research.py               # ファクター計算（momentum/value/volatility）
    - feature_exploration.py           # 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py           # build_features
    - signal_generator.py              # generate_signals
  - execution/                          # 発注関連の実装（現状モジュール構成用）
  - monitoring/                         # 監視・メトリクス収集（必要に応じて実装）

補足・トラブルシューティング
---------------------------
- Python バージョンは 3.10 以上を推奨。型注釈や union types (|) を使用しています。
- DuckDB ファイルパス（DUCKDB_PATH）の親ディレクトリは schema.init_schema が自動で作成します。
- .env のパーシングはプロジェクト独自実装のため、特殊な引用やエスケープに対応しています（詳しくは kabusys.config の実装を参照）。
- 自動環境変数ロードを無効にしてテストを行いたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献・ライセンス
----------------
（必要に応じてここに貢献方法、コントリビュートガイド、ライセンス情報を追記してください）

以上が KabuSys の概要と基本的な使い方です。詳細な設計仕様（StrategyModel.md, DataPlatform.md 等）に基づく実装が多いため、特定の挙動や拡張を行う場合は該当モジュールの docstring・コメントを参照してください。