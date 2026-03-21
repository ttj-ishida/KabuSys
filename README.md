# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータプラットフォームとして用い、J‑Quants から市場データ・財務データを取得して ETL → 特徴量生成 → シグナル生成 → 実行（発注）へつなぐための共通機能を提供します。

- パッケージ名: `kabusys`
- バージョン: `0.1.0`

---

目次
- プロジェクト概要
- 主な機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方（サンプル）
  - DB 初期化
  - 日次 ETL 実行
  - 特徴量構築
  - シグナル生成
- ディレクトリ構成
- 注意事項 / 運用上のヒント

---

プロジェクト概要
----------------
KabuSys は以下の目的に設計された Python ライブラリです。

- J‑Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL パイプライン
- 研究（research）で計算した生ファクターの正規化・合成（feature engineering）
- 正規化済みファクター＋AI スコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け（ニュースに基づく情報）
- DuckDB のスキーマ初期化、監査ログ・実行レイヤーのスキーマ定義

設計の要点:
- ルックアヘッドバイアスを避けるため「target_date 時点で利用可能なデータのみ」を使用
- DuckDB を中心とした冪等（idempotent）保存（ON CONFLICT / DO UPDATE 等）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ等を実装
- 実運用（live）と検証（paper_trading / development）を分離できる設定

主な機能一覧
--------------
- データ取得 / 保存
  - J‑Quants クライアント（株価日足 / 財務 / マーケットカレンダー）
  - raw データを DuckDB の raw_* テーブルへ冪等保存
- ETL
  - 差分取得ロジック（最終取得日から差分を取得）
  - 日次 ETL ジョブ（calendar → prices → financials → 品質チェック）
- スキーマ管理
  - DuckDB のテーブル定義とインデックスを一括作成する `init_schema`
- 研究支援
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - 将来リターン / IC（Spearman）計算 / 統計サマリー
- 戦略・シグナル
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals） — BUY / SELL を signals テーブルへ書き込み
  - 保有ポジションのエグジット判定（ストップロス等）
- ニュース収集
  - RSS 取得、前処理、raw_news 保存、記事 ↔ 銘柄の紐付け
  - SSRF 対策・受信サイズ制限・XML 脆弱性対策（defusedxml）
- 管理・監査
  - 発注・約定・ポジション・監査ログ用テーブル群の定義

要件
----
- Python 3.10 以上（PEP 604 型記法や型ヒントを使用）
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等

（プロジェクトに pyproject.toml / requirements.txt があればそちらを優先してインストールしてください）

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb defusedxml
   # プロジェクトを editable install する場合（プロジェクトルートに pyproject/setup がある前提）
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須の環境変数については次節を参照してください。

4. DuckDB スキーマ初期化
   - 例: デフォルトの DB パスは `data/kabusys.duckdb`（設定で変更可）
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

環境変数（.env）例
-------------------
config モジュール（kabusys.config.Settings）が参照する主なキー:

必須:
- JQUANTS_REFRESH_TOKEN=<あなたの J‑Quants リフレッシュトークン>
- KABU_API_PASSWORD=<kabu ステーション API パスワード>
- SLACK_BOT_TOKEN=<Slack Bot トークン>
- SLACK_CHANNEL_ID=<通知先 Slack チャンネル ID>

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

.example:
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

基本的な使い方（サンプル）
------------------------

前提: DuckDB 接続は `kabusys.data.schema.init_schema()` で初期化済みとする。

1) DB 初期化（1行）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
- ETL は market_calendar → prices → financials → 品質チェックの順で差分取得します。
- J‑Quants の認証トークンは `settings.jquants_refresh_token`（環境変数）から利用されます。

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```
- research 側で算出した生ファクター（prices_daily / raw_financials 参照）を正規化・クリップして `features` テーブルへ保存します。

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals generated: {total}")
```
- `ai_scores` テーブルがあれば AI スコアを組み込みます。Bear レジーム時は BUY シグナルを抑制します。
- 生成されたシグナルは `signals` テーブルへ日付単位で置換（冪等）して保存されます。

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```
- デフォルトソースは `DEFAULT_RSS_SOURCES`。独自ソースを渡すことも可能です。
- XML パースや SSRF を考慮した安全設計が組み込まれています。

ディレクトリ構成
-----------------
以下は主要なモジュールの一覧（パッケージのルートは `src/kabusys/`）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J‑Quants API クライアント（取得 + 保存）
    - news_collector.py      # RSS ニュース収集
    - schema.py              # DuckDB スキーマ定義と init
    - stats.py               # 統計ユーティリティ（zscore 等）
    - pipeline.py            # ETL パイプライン
    - features.py            # data 側の feature ユーティリティ再エクスポート
    - calendar_management.py # 市場カレンダーユーティリティ
    - audit.py               # 監査ログ / 発注トレーサビリティ
    - (その他 data 層モジュール)
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（momentum/volatility/value）
    - feature_exploration.py # 将来リターン / IC / summarise
  - strategy/
    - __init__.py
    - feature_engineering.py # features テーブル作成（正規化／フィルタ）
    - signal_generator.py    # final_score 計算 → signals テーブル生成
  - execution/                # 実行（発注）関連プレースホルダ
  - monitoring/               # 監視/モニタリング用モジュール（DB/Slack等）

（実際のツリーはプロジェクトルートを参照してください）

注意事項 / 運用上のヒント
------------------------
- 環境変数に API トークン等の秘密情報を含めます。リポジトリには絶対にコミットしないでください。
- KABUSYS_ENV を `live` にするとライブ運用用の挙動（警告・保護ルールなど）が有効になる想定です。テストはまず `development` / `paper_trading` で行ってください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb`。バックアップや永続化を運用設計に含めてください。
- 自動で .env をロードしますが、テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- J‑Quants API にはレート制限があるため、クライアント側では固定間隔スロットリングとリトライを実装しています。大量一括フェッチ時は実行時間に注意してください。
- ニュース収集では SSRF / XML BOM 等の攻撃に対策していますが、外部フィードの追加は信頼できるソースに限定してください。

ライセンス / Contributing
--------------------------
- 本 README はコードベースの説明を目的としています。実運用に導入する場合は追加のレビュー・安全対策（発注の二重化防止、資金管理、レート制限監視など）を行ってください。
- 貢献の際はテスト・型チェック・静的解析（lint）を追加することを推奨します。

---

その他、具体的な利用ケース（監視ジョブ、Slack 通知、kabu ステーションとの接続、実行エンジン）についてのドキュメントが必要であれば、用途に応じた手順やサンプルを追記します。どの部分を詳細化したいか教えてください。