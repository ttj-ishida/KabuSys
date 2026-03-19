KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータ基盤・ファクタ計算・戦略シグナル生成・ETL を含む
研究〜運用までを想定した Python パッケージです。

主な設計方針:
- DuckDB をデータストアとして利用し、Raw → Processed → Feature → Execution の層でデータを管理
- 研究（research）モジュールで計算した生ファクターを正規化して features に保存
- features と AI スコアを統合して売買シグナル（BUY/SELL）を生成
- J-Quants API からのデータ取得（株価・財務・カレンダー）、RSS ニュース収集等を提供
- 冪等性・レート制御・リトライ・SSRF対策など、実運用を意識した実装

機能一覧
--------
主要機能（モジュールごとに抜粋）:

- kabusys.config
  - .env（/ .env.local）自動読み込み（プロジェクトルート検出）
  - 環境変数アクセスラッパ（settings）
  - KABUSYS_ENV（development/paper_trading/live）やLOG_LEVEL 検証

- kabusys.data
  - jquants_client: J-Quants API クライアント（トークンリフレッシュ、レート制御、リトライ、DuckDB 保存ユーティリティ）
  - schema: DuckDB スキーマ定義・初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）と個別 ETL ジョブ
  - news_collector: RSS 収集・正規化・DB 保存・銘柄抽出（SSRF対策・gzip/サイズ制限）
  - calendar_management: 市場カレンダー管理・営業日判定・更新ジョブ
  - stats: クロスセクション Z スコア正規化ユーティリティ

- kabusys.research
  - factor_research: momentum/value/volatility などの定量ファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・要約統計

- kabusys.strategy
  - feature_engineering.build_features: ファクター結合・ユニバースフィルタ・正規化・features への UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合し final_score を計算、BUY/SELL シグナル生成・signals テーブルへ保存

- その他
  - audit / execution / monitoring のための骨組み（監査ログや発注管理のDDL 等）

セットアップ手順
---------------
1. Python 環境
   - Python 3.9+ を推奨（typing の記法等を参照）

2. 必要パッケージ（例）
   - duckdb
   - defusedxml
   - （標準ライブラリのみで動作する箇所も多いですが、DuckDB・XML パース用に上記が必要）
   インストール例:
   ```
   pip install duckdb defusedxml
   ```

3. リポジトリをクローン / インストール
   - 開発時:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
     （パッケージ化されていない場合は PYTHONPATH に src を追加して利用してください）
4. 環境変数 / .env
   - プロジェクトルートの .env（および .env.local を上書きとして）を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings に基づく）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL  （デフォルト: INFO）
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"

使い方（代表的な API）
---------------------

基本例: DuckDB スキーマ初期化と日次 ETL、特徴量計算、シグナル生成

Python スクリプト例:
```
from datetime import date
from kabusys.data import schema, pipeline
from kabusys.strategy import build_features, generate_signals

# 1) DB 初期化（ファイルは settings.duckdb_path または任意パス）
conn = schema.init_schema("data/kabusys.duckdb")

# 2) 日次 ETL を実行（J-Quants トークンは settings 経由で自動取得）
etl_result = pipeline.run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 3) 特徴量を構築（features テーブルを更新）
n_features = build_features(conn, target_date=date.today())
print("built features:", n_features)

# 4) シグナル生成
n_signals = generate_signals(conn, target_date=date.today())
print("signals written:", n_signals)
```

ニュース収集の実行例:
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効コードの集合（例: 全上場銘柄リスト）
result = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(result)
```

J-Quants から直接データを取得して保存する例:
```
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, quotes)
```

注意点（運用上のポイント）
- 環境変数は必須項目が多いため .env を用意してください（.env.example を参照する運用を想定）。
- J-Quants API はレート制限に基づく制御およびリトライロジックを内蔵していますが、ETL の実行頻度は運用方針に合わせてください。
- features / signals テーブルへは「日付単位の置換」で書き込む（冪等）実装になっています。
- テストや CI で自動ロードを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
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
  - (monitoring パッケージは __all__ に記載があるが、実装はディレクトリ構成に依存します)

README に含めていないが重要な実装上のポイント
---------------------------------------
- DuckDB スキーマ（schema.init_schema）は多くのテーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, orders, trades, positions, ...）を作成します。初期化時に親ディレクトリを自動作成します。
- news_collector は RSS の安全性（SSRF ブロック、gzip サイズチェック、XML パースの安全処理）と記事ID の正規化（URL 正規化→SHA256）を行います。
- jquants_client は ID トークンのキャッシュ・自動リフレッシュ、ページネーション対応、HTTP エラーに対する指数バックオフを実装しています。
- strategy 側はルックアヘッドバイアスを防ぐため、target_date 時点でのデータのみ参照する方針で実装されています。

貢献・開発
----------
- コードを修正・拡張する場合は tests（存在する場合）を追加し、ローカルで DuckDB インメモリ（":memory:"）を使ったテストを推奨します。
- .env や機密情報はリポジトリに含めないでください。CI 用シークレットは CI 管理機能を用いて設定してください。

ライセンス
---------
（ライセンス情報がプロジェクトにある場合はここに記載してください）

お問い合わせ
------------
実装や設計に関する質問、運用に関する相談などがあれば issue を立ててください。