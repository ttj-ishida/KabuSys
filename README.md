# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API と kabuステーション（発注）を前提に、データ収集（ETL）・特徴量生成・シグナル生成・監査 / 実行レイヤーまでの基本機能を提供します。

注意: 本リポジトリはライブラリ／フレームワークの骨組みを提供するものであり、実際の運用では各種 API トークンや運用上のリスク管理・安全対策を必ず実装してください。

---

## プロジェクト概要

主な目的:
- J-Quants から市場データ（株価・財務・マーケットカレンダー）を取得して DuckDB に蓄積する ETL パイプライン
- 研究用ファクター計算（momentum / value / volatility 等）
- 戦略用特徴量の作成（Z スコア正規化・ユニバースフィルタ）
- 正規化済み特徴量と AI スコアを統合したシグナル生成（BUY / SELL）
- ニュース収集（RSS）と銘柄紐付け機能
- DuckDB スキーマ（Raw / Processed / Feature / Execution 層）と監査ログ用テーブル定義

設計上の特徴:
- DuckDB を中心としたローカル DB（":memory:" も可）
- 冪等性（ON CONFLICT / upsert など）を考慮した保存処理
- Look-ahead bias 回避のため「target_date 時点の情報のみ」を使用する設計
- ネットワーク・ファイル操作での安全対策（SSRF, XML インジェクション 対策等）
- 設定は環境変数 / .env ファイルから読み込み（自動ロード機構あり）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、token リフレッシュ、DuckDB への保存ユーティリティ）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務）の差分更新／保存／品質チェック
  - schema: DuckDB のスキーマ初期化（全テーブルとインデックスの作成）
  - news_collector: RSS からニュース取得・正規化・raw_news 保存・銘柄抽出
  - calendar_management: 営業日判定・前後営業日の検索・カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリー
- strategy/
  - feature_engineering: 生ファクターを統合・正規化し `features` テーブルへ保存
  - signal_generator: features と ai_scores を組み合わせて final_score を算出し `signals` テーブルへ保存
- monitoring / execution 層のスケルトン（監査・発注管理用テーブルやユーティリティが含まれる）

---

## セットアップ手順

前提:
- Python 3.9+（typing 機能等を利用しています）
- pip が利用可能

1. リポジトリをクローンし開発環境を準備
   - 任意の仮想環境（venv / poetry / conda）を使用してください。

2. 必要パッケージをインストール（例）
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 追加で開発用パッケージや linters を入れる場合は各自で管理してください。

3. 環境変数（.env）を設定
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
     （実行する機能により必須変数は変わります。設定がないと Settings が ValueError を投げます）

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を指定すればインメモリ DB になります。

---

## 使い方（簡単な例）

以下は主要ワークフローの実例です。実運用ではログ・エラーハンドリング・スケジューラ（cron / Airflow 等）を追加してください。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価/財務差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 研究モジュールでファクターを計算（単独実行）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value

target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

4) 特徴量を構成して `features` テーブルへ保存
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2024, 1, 31))
print(f"upserted {n} features")
```

5) シグナルを生成して `signals` テーブルへ保存
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2024, 1, 31))
print(f"signals generated: {count}")
```

6) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効な銘柄コード集合（例: 国際証券コード一覧）
saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(saved_map)
```

7) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注: 上記は各関数が期待するテーブル構造（prices_daily / raw_financials / features / positions / ai_scores 等）が存在することが前提です。初回は ETL により raw_* テーブルが埋まり、必要に応じて加工（raw_prices → prices_daily など）を実装してください。

---

## 設定と環境変数

主な環境変数（settings から参照されるもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — sqlite (monitoring 用) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

settings は `kabusys.config.settings` オブジェクト経由で利用できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント、保存ユーティリティ
  - news_collector.py              — RSS 収集と保存
  - pipeline.py                    — ETL パイプライン
  - schema.py                      — DuckDB スキーマ初期化
  - stats.py                       — zscore_normalize 等
  - features.py                    — data.stats の再エクスポート
  - calendar_management.py         — market_calendar 管理
  - audit.py                       — 監査ログテーブル定義（スケルトン）
- research/
  - __init__.py
  - factor_research.py             — momentum / volatility / value 計算
  - feature_exploration.py         — 将来リターン・IC・summary 等
- strategy/
  - __init__.py
  - feature_engineering.py         — features 作成（ユニバースフィルタ・正規化・UPSERT）
  - signal_generator.py            — final_score 計算と signals 生成
- execution/                        — 実行層（空の __init__、実装は拡張想定）
- monitoring/                       — 監視 / メトリクス（拡張想定）

---

## 開発上の注意 / 実運用アラート

- 本コードは現状で「研究 / バックテスト」用途のロジックと「基本的な ETL / 保存処理」を含みますが、実際の資金を扱う運用ではさらに厳密なバリデーション・二重発注防止・安全ガード（立ち往生時の失敗モード、ネットワークエラー時の挙動など）が必要です。
- API トークンや秘密情報は適切に管理してください（Secrets Manager / Vault 等の利用を推奨）。
- DB のバックアップ・監査ログ保持（削除不可ポリシー）を検討してください。
- ニュース取得処理は外部フィードを扱うため、RSS の仕様差異やエンコード、サイズ制限等に注意してください。
- J-Quants の API レート制限を厳守する実装がありますが、外部環境やトラフィックによる差異は適宜モニタしてください。

---

## ライセンス / 貢献

この README ではライセンスや貢献方法に関する定義は含めていません。リポジトリに LICENSE ファイルや CONTRIBUTING ガイドがある場合はそちらに従ってください。

---

必要であれば、セットアップ用のスクリプト例（requirements.txt / entrypoint スクリプト / systemd タイマー例 / cron ジョブ）や CI 用のテスト記述（pytest）テンプレートも追記できます。どのドキュメントを優先して追加しましょうか？