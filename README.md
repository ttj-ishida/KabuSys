# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。市場データの取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマと監査・実行系のスケルトンを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API などからの市場データ取得と DuckDB への保存（差分更新・冪等性）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量（features）生成と正規化（Zスコア）
- 戦略による最終スコア計算と BUY / SELL シグナル生成（立ち上げから実行まで分離）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- DuckDB のスキーマ定義と監査／実行ログ用テーブル

設計上のポイント：

- DuckDB を用いたローカル DB（:memory: も可）。ETL は差分取得・バックフィル対応。
- 外部 API 呼び出し（発注など）とは層を分離し、戦略層は発注層に依存しない設計。
- 冪等性（ON CONFLICT）およびトランザクションによる原子性を重視。
- Look-ahead バイアス回避を意識した日付基準の実装。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ・DuckDB 保存）
  - pipeline: 日次 ETL（prices / financials / market calendar）の差分取得と品質チェック
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - features / stats: Zスコア正規化など統計ユーティリティ
  - audit: 監査ログ用テーブル定義（シグナル→オーダー→約定のトレース）
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター集計
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: research 結果から features を作成して保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL を判定して signals テーブルへ書き込み
- config.py: 環境変数 / .env の自動読み込みと設定ラッパー（必須トークン取得用プロパティ）
- 拡張: execution/ や monitoring/（発注や監視ロジックを置く想定）

---

## セットアップ手順

前提
- Python 3.9+（typing 機能が用いられているため互換性を合わせてください）
- DuckDB（Python パッケージとしてインストール）
- ネットワーク接続（J-Quants API, RSS など）

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - プロジェクト root に setup/requirements ファイルがあればそれを利用してください。
   - 開発時は linters / test ライブラリを追加して下さい（本リポジトリには requirements ファイルを含めていません）。

3. パッケージをインストール（ローカル開発）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` として必要な値を保存できます。
   - 自動読み込みされる優先順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（Config.Settings が参照）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu ステーション等の API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

注意: `.env` は機密情報を含むため、バージョン管理へコミットしないでください（.gitignore に含めてください）。`.env.example` を参考に作成してください。

---

## 使い方（サンプル）

以下は Python REPL / スクリプトからの基本操作例です。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- ":memory:" を渡すとインメモリ DB が使えます。
- 既存テーブルがあればスキップされるため冪等です。

2) 日次 ETL の実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ETL は market calendar → prices → financials → 品質チェック の順で実行します。
- jquants_client の id_token は自動的に取得・リフレッシュされます（JQUANTS_REFRESH_TOKEN が必須）。

3) 特徴量生成（features 作成）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（RSS）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: saved_count}
```

6) 設定の参照

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須、未設定だと ValueError
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env)                    # development/paper_trading/live
```

---

## 開発・運用上の注意

- jquants_client は API レート（120 req/min）を守るため内部で固定間隔スロットリングを行います。大量取得時は注意してください。
- HTTP 429 / 5xx 等に対して指数バックオフのリトライを実装しています。401 はトークン自動リフレッシュ後に1回リトライします。
- news_collector は SSRF 対策、受信サイズ上限、XML の defusedxml パーサー利用などセキュリティを配慮しています。
- DuckDB の SQL は多くの箇所でトランザクションと ON CONFLICT を使って冪等性を担保しています。
- 本リポジトリには発注（ブローカー接続）に関する実装はほぼ含まれていません（execution/ はスケルトン）。実運用では証券会社 API の実装・テスト・監査が必要です。
- 監査ログ（audit モジュール）によりシグナル→オーダー→約定のトレーサビリティを保証する設計になっています。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - schema.py
    - news_collector.py
    - calendar_management.py
    - features.py
    - stats.py
    - audit.py
    - pipeline.py
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
  - monitoring/ (想定フォルダ。監視系は今後拡張)

主要なモジュールと役割：
- kabusys.config: 環境変数管理・検証（.env 自動読み込み）
- kabusys.data.schema: DuckDB の DDL と初期化関数 (init_schema)
- kabusys.data.jquants_client: J-Quants API の取得＋保存ユーティリティ
- kabusys.data.pipeline: ETL ジョブの実行フロー（run_daily_etl など）
- kabusys.research: ファクター計算と探索用ユーティリティ
- kabusys.strategy: 特徴量生成・シグナル生成の公開 API

---

## ライセンス・貢献

この README ではライセンスや貢献ガイドラインは同梱していません。公開する場合は LICENSE ファイルおよび CONTRIBUTING.md を追加してください。

---

必要に応じて README に例のコマンド（cron/airflow ジョブ設定、systemd ユニット、CI ワークフロー等）や .env.example のテンプレート、よくあるトラブルシュート（トークン/ネットワーク/DB 初期化）を追加できます。どのような情報を優先して追記したいか教えてください。