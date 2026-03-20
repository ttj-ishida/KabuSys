# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J‑Quants API からの株価 / 財務 / カレンダー取得（レート制御・リトライ・トークン自動更新付き）
- DuckDB をバックエンドとした Raw / Processed / Feature / Execution 層のスキーマ管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究（research）側で算出した生ファクターを正規化して features テーブルへ保存する特徴量エンジニアリング
- features と AI スコアを統合して売買シグナルを生成する戦略ロジック（BUY / SELL の判定）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策・サイズ上限・トラッキングパラメータ除去）
- 監査ログ／トレーサビリティのためのテーブル定義

設計上の特徴：
- DuckDB を用いたローカルデータベース（ファイル or :memory:）
- API 呼び出しはレート制御・リトライ・トークン更新を備えた堅牢な実装
- DB 保存は冪等（ON CONFLICT / トランザクション）で二重挿入を回避
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみ使用

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local / OS 環境変数から設定を読み込む（自動ロード有効）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 判定

- kabusys.data.jquants_client
  - J‑Quants API との通信（get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - レートリミット（120 req/min）、リトライ / 指数バックオフ、401 時のトークン自動リフレッシュ
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）

- kabusys.data.schema
  - DuckDB の全スキーマ定義（raw / processed / feature / execution / audit）
  - init_schema(db_path) で DB の初期化（冪等）

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー、株価、財務の差分取得 + 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分取得・バックフィルのロジックを内包

- kabusys.data.news_collector
  - RSS からニュースを収集して raw_news に保存
  - URL 正規化（トラッキング除去）、SSRF 対策、gzip/サイズ制限、記事ID を SHA-256 で生成
  - 記事と銘柄コードの紐付け（news_symbols）

- kabusys.data.stats / data.features
  - zscore_normalize: クロスセクションの Z スコア正規化（research と共有）

- kabusys.research
  - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary（特徴量評価ツール）

- kabusys.strategy
  - build_features: research のファクターを正規化・フィルタして features テーブルへ保存
  - generate_signals: features / ai_scores / positions を基に final_score を計算し signals テーブルへ保存

- kabusys.execution / kabusys.monitoring
  - （パッケージエクスポート用に存在。将来的に発注周り・監視機能を担う想定）

---

## セットアップ手順

必要環境（目安）
- Python 3.9+（typing の一部記法・型ヒントに依存）
- DuckDB Python パッケージ
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ（urllib, logging 等）

推奨インストール例（プロジェクトルートで）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに setup.py / pyproject.toml があれば pip install -e . が利用可能）

3. .env を用意
   - プロジェクトルートに .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト有り）:
     - KABUSYS_ENV （development / paper_trading / live）デフォルト: development
     - LOG_LEVEL （DEBUG/INFO/...）デフォルト: INFO
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）

4. 自動 .env ロードの無効化（テスト等）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定すると自動ロードを無効化

---

## 使い方（基本的なワークフロー例）

以下は最小限の操作例（Python REPL / スクリプト）です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" を指定するとメモリ DB
```

2) 日次 ETL 実行（J‑Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date.today())  # ETLResult オブジェクト
print(result.to_dict())
```

3) 特徴量構築（features テーブルの作成 / 置換）
```python
from kabusys.strategy import build_features
build_count = build_features(conn, target_date=date.today())
print(f"features upserted: {build_count}")
```

4) シグナル生成（features と ai_scores を統合して signals を作成）
```python
from kabusys.strategy import generate_signals
signal_count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {signal_count}")
```

5) ニュース収集（RSS の取得と保存）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に用いる有効コード集合（例: prices_daily のコード一覧）
known_codes = set(r[0] for r in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall())
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

注意点:
- 各種保存関数は冪等（ON CONFLICT）で動作するため、同じデータを再度保存しても安全です。
- J‑Quants API 呼び出しは内部でレート制御・リトライ・トークン更新を行います。長時間のページネーション取得でもトークンをキャッシュして共有します。

ログ出力:
- 標準的に logging を利用しています。スクリプト実行時に logging.basicConfig(level=...) 等で制御してください。
- 環境変数 LOG_LEVEL も利用可能です（settings.log_level）。

---

## 環境変数（主なもの）

主要な環境変数（settings 経由で参照される）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J‑Quants のリフレッシュトークン。get_id_token に使用されます。

- KABU_API_PASSWORD (必須)
  - kabuステーション等、発注 API 用のパスワード（将来的な execution 層で使用想定）。

- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH
  - デフォルト DB ファイルパス（例: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用などに使用する sqlite ファイルパス（例: data/monitoring.db）

- KABUSYS_ENV
  - 環境（development / paper_trading / live）。settings.is_live 等で参照。

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/...）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 値を設定するとプロジェクトルートの .env 自動読み込みを無効化（テスト用）

.env のパース挙動:
- .env/.env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を基準にルートを特定）
- .env.local は .env を上書き（既存 OS 環境変数は保護）
- export KEY=val, 引用符、行末コメント等に対応する独自パーサを使用

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py         # J‑Quants API クライアント（取得＋保存）
  - pipeline.py               # ETL パイプライン
  - schema.py                 # DuckDB スキーマと初期化
  - stats.py                  # 統計ユーティリティ（zscore_normalize）
  - features.py               # data.stats の公開ラッパ
  - news_collector.py         # RSS 取得と DB 保存
  - calendar_management.py    # market_calendar 関連ユーティリティと夜間更新ジョブ
  - audit.py                  # 監査ログ DDL（signal_events / order_requests / executions 等）
- src/kabusys/research/
  - __init__.py
  - factor_research.py        # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py    # 将来リターン / IC / 統計サマリー
- src/kabusys/strategy/
  - __init__.py
  - feature_engineering.py    # build_features（ユニバースフィルタ・正規化・UPSERT）
  - signal_generator.py       # generate_signals（final_score 計算・BUY/SELL 判定）
- src/kabusys/execution/        # 現時点はパッケージ用に存在
- src/kabusys/monitoring/      # 将来的な監視用モジュール想定

---

## 実運用上の注意 / 備考

- セキュリティ
  - RSS/HTTP 取得時は SSRF 対策（リダイレクト検査、プライベート IP 拒否）を実装済み
  - defusedxml を用いて XML 攻撃を緩和
  - .env に秘密情報を格納する場合はリポジトリにコミットしないこと

- 冪等性とトランザクション
  - DB 書き込みは多くが ON CONFLICT を用いた冪等処理、かつトランザクションで囲まれています
  - エラー時は適切に ROLLBACK を試みる設計

- テスト
  - 設定の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使うとテストでの環境分離が容易

- 拡張
  - execution 層（ブローカー連携）や monitoring（Slack 通知等）への接続は設定次第で容易に追加可能

---

以上がこのコードベースの README.md（日本語）です。要望があれば、セットアップ用の .env.example のテンプレートや、実際の CLI / システム起動スクリプト例、ユニットテストの骨組みなども追加で作成します。必要な内容を教えてください。