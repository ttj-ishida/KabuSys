KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買（データプラットフォーム + 戦略）ライブラリです。  
主な目的は J-Quants 等からの市場データ取得、DuckDB によるデータ格納・加工、特徴量生成、シグナル作成、ニュース収集、発注監査用のスキーマ提供など、量化トレーディングの各レイヤーを整備することです。

設計方針（抜粋）
- データ取得・保存は冪等（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）に実装
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- DuckDB をデータストアとして想定（ローカルファイル / :memory: 対応）
- 外部依存を最小化（可能な箇所は標準ライブラリで実装）
- ネットワーク系はレート制御・リトライ・SSRF 対策などを実施

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント (data/jquants_client.py)
    - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
    - レートリミット対応、401 時のトークン自動リフレッシュ、リトライロジック
  - ETL パイプライン (data/pipeline.py)
    - 差分取得、バックフィル、品質チェックの統合実行（run_daily_etl）
- データスキーマ
  - DuckDB 用のスキーマ定義と初期化 (data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル定義
- ニュース収集
  - RSS 取得・前処理・raw_news/ news_symbols への保存 (data/news_collector.py)
  - SSRF 防止・サイズ制限・トラッキングパラメータ除去等の安全対策
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算 (research/factor_research.py)
  - 将来リターン, IC, 統計サマリー等の探索ユーティリティ (research/feature_exploration.py)
- 特徴量エンジニアリング
  - 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの書き込み (strategy/feature_engineering.py)
- シグナル生成
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成 (strategy/signal_generator.py)
  - Bear レジームでの BUY 抑制、エグジット（ストップロス等）判定
- 統計ユーティリティ
  - Zスコア正規化など（data/stats.py）
- 設定管理
  - .env / 環境変数の自動読込み、必須パラメータの検査 (config.py)

セットアップ
----------
前提
- Python 3.10 以上（型アノテーション Path | None 等を利用しているため）
- DuckDB（Python パッケージ）を利用

推奨手順（UNIX 系）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトをパッケージ化している場合は pip install -e .）

3. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（config.py による自動ロード）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携する場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意 / デフォルト値
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

簡易 .env.example
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（サンプル）
-----------------

以下の例は最小限の操作例です。すべて Python スクリプトや対話セッションで実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成してテーブルを初期化
# あるいは: conn = init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())  # ETL の結果オブジェクトを返す
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {num_signals}")
```

5) ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効コードセット（省略可）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)  # {source_name: saved_count}
```

設定管理について（自動 .env 読み込み）
------------------------------------
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出し、.env と .env.local を順に読み込みます。
- OS 環境変数が優先され、.env.local は .env の上書きに使用されます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数を参照すると未設定時に ValueError が発生します（settings.jquants_refresh_token 等）。

開発者向けメモ
--------------
- 型: Python 3.10 の型構文（X | None）を使用しています。
- 大量データ処理は DuckDB の SQL を多用しており、計算は原則 SQL で行われます（パフォーマンス重視）。
- ニュースの XML 解析には defusedxml を使い、XML 脅威に対処しています。
- J-Quants クライアントはレート制御と指数バックオフを持ちます。ID トークンはモジュール内キャッシュで共有されます。
- ETL の品質チェックモジュール（data/quality）は pipeline から呼び出されます（今回の抜粋では定義ファイルが省略されている可能性があります）。

ディレクトリ構成
----------------
（ソースルート: src/kabusys/ の主要ファイル）
- kabusys/
  - __init__.py
  - config.py                     : 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存）
    - news_collector.py           : RSS ニュース収集・保存
    - schema.py                   : DuckDB スキーマ定義・初期化
    - stats.py                    : 統計ユーティリティ（zscore_normalize など）
    - pipeline.py                 : ETL パイプライン（run_daily_etl 等）
    - features.py                 : data.stats の公開インターフェース
    - calendar_management.py      : 市場カレンダー管理（営業日判定等）
    - audit.py                    : 発注トレーサビリティ用監査テーブル定義
  - research/
    - __init__.py
    - factor_research.py          : Momentum / Volatility / Value 計算
    - feature_exploration.py      : 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py      : features テーブル構築ロジック
    - signal_generator.py         : final_score 計算と signals 生成
  - execution/                     : 発注実装（スケルトン）
  - monitoring/                    : 監視用モジュール（スケルトン・別ファイル内実装）

注意事項 / 既知の制限
--------------------
- 実際の証券会社への発注連携（kabusys.execution など）はこの抜粋には含まれていないため、実運用環境での発注処理には追加実装が必要です。
- 一部ドキュメント（StrategyModel.md / DataPlatform.md / Research 等）は参照設計書としてコード内で言及されていますが、本リポジトリに含まれない場合があります。
- 本 README はコードベースから抽出可能な情報に基づいて記述しています。運用前に必ずテストとコードレビューを行ってください。

サポート / 貢献
----------------
バグ報告・改善提案は Issue を通じてください。PR は歓迎します。大型変更前には Issue で設計議論を行ってください。

以上。