# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を用いたデータ層、J-Quants API クライアント、特徴量計算・シグナル生成、RSS ベースのニュース収集、ETL パイプライン、監査ログ等を含むモジュール化された実装を提供します。

主な想定用途:
- J-Quants からの市場データ取得と DuckDB への永続化（ETL）
- 研究用ファクター計算・特徴量生成（research モジュール）
- 戦略のスコア計算と売買シグナル生成（strategy モジュール）
- ニュース収集と銘柄紐付け（news_collector）
- 発注・約定・ポジション管理用のスキーマ（execution / audit）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（Settings クラス）
- データ取得・永続化（J-Quants）
  - API クライアント（リトライ / レートリミット / トークン自動リフレッシュ対応）
  - 日足・財務・市場カレンダー等の取得・DuckDB への冪等保存
- ETL パイプライン
  - 差分取得（backfill 対応）と品質チェック統合
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- データスキーマ
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義と初期化
- 研究（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルの UPSERT
- シグナル生成（strategy.signal_generator）
  - 正規化済み特徴量 + AI スコアを統合して final_score を算出し BUY/SELL シグナルを生成
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理・記事保存・銘柄抽出（SSRF 対策・XML 攻撃対策あり）
- 汎用統計ユーティリティ（zscore_normalize など）

---

## 必要環境 / 前提

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）
- J-Quants の refresh token、kabu API パスワード、Slack トークン（運用時）

必須環境変数（Settings により参照される）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他（オプション・デフォルトあり）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトを editable インストールする場合）
     - pip install -e .

   ※ 実際のプロジェクトには requirements.txt / pyproject.toml を用意している想定です。

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は上書き）。
   - 最低限設定する例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   - 自動読み込みを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要 API と簡単な例）

以下は Python REPL やスクリプトからの利用例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL を実行（J-Quants トークンは Settings から取得されます）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 研究用ファクター計算 / 特徴量生成 / シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 1, 15)

# features を構築（features テーブルに書き込む）
n = build_features(conn, target)
print(f"features upserted: {n}")

# シグナル生成（signals テーブルに書き込む）
count = generate_signals(conn, target)
print(f"signals generated: {count}")
```

4) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) J-Quants API を直接使う（ID トークン取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings に設定された refresh token を使用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,15))
```

注意:
- ほとんどの関数は DuckDB 接続を受け取り外部副作用（発注 API 等）を持ちません。テストしやすい設計です。
- ETL / API 呼び出しはネットワーク・API レートに依存します。運用時はログ・レート制御を必ず確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    (環境変数 / Settings)
  - data/
    - __init__.py
    - schema.py                  (DuckDB スキーマ定義 / init_schema)
    - jquants_client.py          (J-Quants API クライアント / 保存ユーティリティ)
    - pipeline.py                (ETL パイプライン)
    - news_collector.py          (RSS ニュース収集)
    - features.py                (zscore_normalize エクスポート)
    - stats.py                   (統計ユーティリティ)
    - calendar_management.py     (市場カレンダー管理)
    - audit.py                   (監査ログ用スキーマ / DDL)
    - audit.py (続き)             (インデックスなど)
  - research/
    - __init__.py
    - factor_research.py         (momentum / volatility / value の計算)
    - feature_exploration.py     (forward returns / IC / summary)
  - strategy/
    - __init__.py
    - feature_engineering.py     (features の構築)
    - signal_generator.py        (final_score 計算・signals 生成)
  - execution/                   (発注 / 実行 関連モジュール（空ファイルあり）)
  - monitoring/                  (監視・メトリクス系モジュール想定)

（ファイルは実装済みのものと空の __init__ 等が混在します。README は抜粋を示しています。）

---

## 設計上の注意点 / 運用メモ

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出します。配布後やテスト時に必要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自分で環境を注入してください。
- J-Quants クライアントはレート制限（120 req/min）とリトライ（指定 status の場合）を組み込んでいます。大量の一括取得は分割して実行してください。
- DuckDB の INSERT は多くの箇所で ON CONFLICT（冪等保存）を使用しています。スキーマ初期化は init_schema() を最初に実行してください。
- ニュース収集は SSRF や XML 攻撃に対する対策を講じていますが、外部 RSS に依存するため入力ソースの信頼性と運用監視を行ってください。
- KABUSYS_ENV は運用モード（development / paper_trading / live）を切り替えます。is_live / is_paper / is_dev 判定が Settings により提供されています。

---

## 付記

- テストコード・CI・ライセンス等はこの README の対象外です。実運用に投入する前に十分な検証（バックテスト、ペーパートレード、モニタリング）を行ってください。
- 追加のドキュメント（StrategyModel.md, DataPlatform.md, DataSchema.md など）がリポジトリにある想定です。より詳細な仕様や数式はそれらを参照してください。

---

必要であれば、README にサンプル .env.example、より詳細な API 使用例（関数一覧と引数説明）、あるいは簡単な CLI ラッパーの使い方を追記します。どの情報を補足しましょうか？