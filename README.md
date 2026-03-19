# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README です。  
このリポジトリは、データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査/実行用スキーマなどを含む一連の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。  
主な目的は次のとおりです。

- J-Quants API 等からの市場データ・財務データ・カレンダーの取得と DuckDB への保存（冪等）
- データ品質チェック、ETL（差分取得・バックフィル）
- 研究（research）で算出した生ファクターの正規化／合成による特徴量生成
- 戦略（strategy）に基づく売買シグナル生成（BUY/SELL）
- RSS ベースのニュース収集と銘柄紐付け
- 実行・監査（execution / audit）用のスキーマ設計（発注、約定、ポジション監視など）

設計のキーワード：冪等性（idempotent）、ルックアヘッドバイアス防止、トレーサビリティ、外部依存の最小化（標準ライブラリ + 必要最小限の外部ライブラリ）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（トークンリフレッシュ、ページネーション、レート制御、リトライ）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: ETL（差分取得、バックフィル、日次 ETL エントリ）
  - news_collector: RSS 収集、前処理、raw_news 保存、記事→銘柄紐付け
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン・IC・統計サマリー等の研究ユーティリティ
- strategy/
  - feature_engineering: 生ファクターの正規化・フィルタ適用・features テーブルへの書き込み
  - signal_generator: features と ai_scores を統合して final_score を計算し signals テーブルに BUY/SELL を書き込む
- execution / audit（スキーマ定義を含む）：監査ログ、order_requests、executions 等の設計（トレーサビリティ）
- config: 環境変数管理（.env 自動読み込み、必須変数チェック、実行環境判定）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に PEP 604 を使用）
- Git（開発環境での .env 自動検出に使用）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 最低限必要な外部ライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （将来的に requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（config.py）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（config.Settings 参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（execution 層を利用する場合）
- SLACK_BOT_TOKEN       : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意・デフォルト
- KABUSYS_ENV : 実行環境。'development' (default), 'paper_trading', 'live'
- LOG_LEVEL   : ログレベル。'DEBUG','INFO','WARNING','ERROR','CRITICAL'（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env の自動ロードを無効化
- DUCKDB_PATH : DuckDB ファイルのパス（default: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリング用）パス（default: data/monitoring.db）
- KABU_API_BASE_URL : kabu API のベース URL（default: http://localhost:18080/kabusapi）

5. データベース初期化
   - Python で DuckDB スキーマを作成します（init_schema を使用）:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 使い方（簡易サンプル）

以下は Python スクリプト/REPL での基本操作例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からデータ取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日を使う
print(result.to_dict())
```

- 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2024, 1, 10))
print(f"features upserted: {count}")
```

- シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2024, 1, 10), threshold=0.6)
print(f"signals written: {n}")
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は有効な銘柄コードセットを渡すと銘柄抽出が行われる
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: new_saved_count}
```

- カレンダー操作（営業日判定など）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
print(is_trading_day(conn, date(2024, 1, 2)))
print(next_trading_day(conn, date(2024, 1, 2)))
```

注意点：
- 各処理は DuckDB のテーブル（prices_daily、raw_financials、features、ai_scores、positions など）に依存します。初期ロードや ETL を適切に行ってから戦略処理を実行してください。
- generate_signals / build_features は target_date 時点のデータのみを用いるよう設計されています（ルックアヘッドバイアス回避）。

---

## .env（例）

プロジェクトルートに `.env` を作成して以下のように設定します（実際の値はご自身のシークレットで置き換えてください）。

例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

config.Settings は必須変数が未設定の場合に ValueError を投げます。`.env.example` を用意しておくと親切です（本リポジトリ内に `.env.example` があれば参照してください）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルのツリー（src/kabusys 以下）。実際のリポジトリではさらに細分化されている可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - features.py
      - audit.py
      - calendar_management.py
      - ...（その他 data 関連）
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
      - ...（発注関連は今後拡張）
    - monitoring/
      - ...（監視・通知関連）
    - ...（その他補助モジュール）

---

## 開発・運用上の注意

- 冪等性
  - 外部データの保存は ON CONFLICT / DO UPDATE（または DO NOTHING）で実装されています。再実行しても重複せず安全に済むことを意図しています。
- ルックアヘッドバイアス
  - 研究／戦略処理は target_date 時点で利用可能なデータのみを使う設計です。将来データを利用しないよう注意して実装されています。
- トークン管理
  - J-Quants トークンはリフレッシュフローを実装して自動更新します。`JQUANTS_REFRESH_TOKEN` を設定してください。
- レート制御・リトライ
  - J-Quants はレート制限（デフォルト 120 req/min）とリトライ・バックオフを考慮してクライアント実装済みです。
- セキュリティ
  - news_collector は SSRF・XML Bomb 対策（リダイレクト検査・defusedxml・受信サイズ上限）を実装しています。
- テスト
  - モジュールは外部依存（HTTP 等）を注入/モック可能に実装されている箇所があり、ユニットテストの作成が容易です。

---

## ライセンス・貢献

- ライセンス情報はリポジトリ内の LICENSE ファイル・プロジェクトのメタ情報を参照してください（このコードベースには明示されていません）。

貢献（PR / Issue）は歓迎します。設計文書（DataPlatform.md, StrategyModel.md 等）に準拠して機能拡張・修正を行ってください。

---

もし README の例や CLI 用の簡易ラッパー、または具体的な .env.example を追加で作成してほしい場合は教えてください。