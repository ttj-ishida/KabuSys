# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL（J-Quants API を利用）、DuckDB ベースのスキーマ管理、特徴量計算、シグナル生成、ニュース収集、監査ログなど、戦略開発から実運用までの基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得／保存
  - J-Quants API クライアント（株価日足・財務・市場カレンダー等のページネーション対応取得、トークン自動リフレッシュ、リトライ／レート制御）
  - raw データを DuckDB に冪等（ON CONFLICT）で保存するユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日の差分取得、バックフィル対応）
  - 市場カレンダーの先読み・営業日調整
  - 品質チェック（品質問題検出は別モジュールで実行）
- スキーマ管理
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
- 特徴量・調査機能（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - クロスセクションの Z スコア正規化ユーティリティ
  - 将来リターン計算・IC（Spearman）・統計サマリ等の探索用関数
- 戦略サポート
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）：ファクター + AI スコア統合、BUY/SELL 判定、エグジットロジック（ストップロス等）
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip制限、XML の安全パース）、raw_news 保存、銘柄抽出・紐付け
- 監査 / トレーサビリティ
  - シグナル→発注→約定までトレースする監査用スキーマ（order_request_id 等の冪等キーを含む）
- その他ユーティリティ
  - マーケットカレンダー管理（営業日判定、前後営業日取得、期間の営業日列挙）
  - ロギングレベル／実行モード（development / paper_trading / live）設定管理

---

## 必要条件（依存パッケージ）

最低限必要なパッケージ（一例、環境に合わせて調整してください）:

- Python 3.9+
- duckdb
- defusedxml

（その他、標準ライブラリのみで実装されている箇所が多いですが、実行環境に合わせて追加パッケージが必要になる場合があります）

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
   - このコードベースは src/kabusys 配下に配置されています。プロジェクトルートに `pyproject.toml` や `.git` があると自動で .env が読み込まれます。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （必要に応じてその他のパッケージをインストール）

4. パッケージのインストール（開発モード）
   - プロジェクトルートに `pyproject.toml` / `setup.py` がある場合:
     - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置して環境変数を設定できます。自動読み込みはデフォルトで有効です（設定は `kabusys.config.settings` から参照）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（少なくともこれらは設定が必要な処理があります）:
- JQUANTS_REFRESH_TOKEN （J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD （kabuステーション API 用パスワード）
- SLACK_BOT_TOKEN （Slack 通知を行う場合）
- SLACK_CHANNEL_ID
オプション／デフォルト値あり:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト INFO）

---

## 使い方（クイックスタート）

以下は Python からライブラリを利用する基本的な例です。すべての API は DuckDB 接続を受け取り、ほとんどの処理は冪等に設計されています。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# デフォルトの DB パスを使う場合
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しない場合は本日扱い
print(result.to_dict())
```

3) 特徴量の構築
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2024, 1, 10))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2024, 1, 10))
print(f"signals generated: {count}")
```

5) ニュース収集ジョブの実行（RSS から収集して DB に保存）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を渡すと記事から銘柄コード抽出＋紐付けまで行う
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースごとの保存件数
```

6) 研究用関数（IC 計算や将来リターン）
```python
from kabusys.research import calc_forward_returns, calc_ic

# prices_daily 等を用意し、研究用分析を実行
forward = calc_forward_returns(conn, date(2024, 1, 10))
# factor_records は例えば calc_momentum などの出力
# ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 主要モジュールと責務（ディレクトリ構成）

プロジェクトの主要なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（.env 自動ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義・初期化
    - pipeline.py
      - 日次 ETL / 差分取得ロジック
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - news_collector.py
      - RSS 取得・整形・DB 保存・銘柄抽出
    - features.py
      - data.stats の再エクスポート
    - calendar_management.py
      - market_calendar 管理・営業日ロジック
    - audit.py
      - 監査ログ用スキーマ定義
    - execution/ (フォルダは存在、発注周りの実装予定)
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算・BUY/SELL 生成・signals 保存
  - execution/
    - （発注・約定を扱うレイヤー、実装は別途）
  - monitoring/
    - （監視用 DB/ロギング等を想定）

上記以外に、README やドキュメント（StrategyModel.md、DataPlatform.md 等）をプロジェクトルートに置く想定です（config.py 内で .env.example が参照されているため .env.example を作成しておくと便利です）。

---

## 設定（環境変数の例）

.env に記載する典型的なキー（例）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config.Settings は上記キーを参照します。必須キーが未設定の場合は ValueError が発生します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。

---

## 運用上の注意

- DuckDB のファイルパスは settings.duckdb_path に依存します。マルチプロセスで同一ファイルに同時アクセスする場合の制約に注意してください。
- J-Quants API のレート制御・リトライを組み込んでいますが、API 利用規約を遵守してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- features/build/signals の処理は look-ahead バイアス防止のため、target_date 時点のデータのみを利用する設計になっています。データが欠損していると結果が変わるため、ETL → features → signals の順で正しい日付で実行すること。

---

## トラブルシューティング

- 環境変数エラー:
  - settings のプロパティが未設定なら ValueError が発生します。`.env.example` を参考に `.env` を作成してください。
- DuckDB テーブルが存在しない:
  - 初回は必ず init_schema(db_path) を実行してテーブルを作成してください。
- ネットワーク／API エラー:
  - jquants_client の _request はリトライ・バックオフを実装しています。401 は自動リフレッシュを試みますが、refresh token の有効性を確認してください。

---

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。各モジュール内（docstring）に詳細な設計・仕様が記載されていますので、実装や拡張の際は該当モジュールのドキュメントを参照してください。必要であれば、運用手順やデプロイ手順、API キーのローテーション手順などの追加ドキュメントを作成できます。