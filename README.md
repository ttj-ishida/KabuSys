# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査トレーサビリティ、マーケットカレンダー管理など、戦略実行に必要な主要コンポーネントを提供します。

---

## 主な特徴（機能一覧）

- データ収集
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - 株価（OHLCV）、四半期財務、JPX カレンダーの取得
- ETL / データプラットフォーム
  - 差分取得（バックフィル対応）と冪等保存（DuckDB へ ON CONFLICT 処理）
  - 品質チェックフレームワーク（欠損・スパイク等の検出）
  - マーケットカレンダー管理・営業日ロジック
- ニュース収集
  - RSS 取得、前処理、記事ID生成（URL正規化+SHA-256）、SSRF対策、保存・銘柄紐付け
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL＋Python）
  - 将来リターン（forward returns）、IC（Spearman）計算、統計サマリー
- 特徴量・シグナル生成（戦略層）
  - ファクター正規化（Zスコア）、ユニバースフィルタ、最終スコア計算
  - BUY/SELL シグナル生成、Bear レジーム抑制、エグジット判定（ストップロス等）
- スキーマ・監査
  - DuckDB スキーマ初期化（Raw/Processed/Feature/Execution 層）
  - 監査ログ（signal_events / order_requests / executions）設計
- 汎用ユーティリティ
  - Z スコア正規化、日付ユーティリティ、CSV/HTTP ハンドリング等

---

## 要求環境

- Python 3.10 以上（型注釈や union 表記などを使用）
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されている部分も多いですが、上記は必須です。

（プロジェクトの packaging に requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数・設定

KabuSys は環境変数から設定を読み込みます。プロジェクトルートの `.env` / `.env.local` を自動でロードします（`.git` または `pyproject.toml` を基準にプロジェクトルートを探索）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる環境変数（実行に必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他オプション（デフォルト値あり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

設定は `kabusys.config.settings` からプログラム的に参照できます。

---

## セットアップ手順（ローカル開発の一例）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係インストール
   - pip install duckdb defusedxml
   - （プロジェクトが pyproject.toml / requirements.txt を持つ場合はそれに従う）

3. プロジェクトルートに `.env` を作成（例: .env.example を参照）
   - JQUANTS_REFRESH_TOKEN=...
   - KABUS_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...

4. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 基本的な使い方（コード例）

以下は主要ワークフローの最小例です。実運用では例外処理・ログ設定・スケジューリングを追加してください。

- DuckDB の初期化（1回）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量の構築（strategy.feature_engineering）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date.today())
  print("features upserted:", count)
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date.today())
  print("signals generated:", total)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードセット（例: {'7203', '6758', ...}）
  results = run_news_collection(conn, known_codes={'7203','6758'})
  print(results)
  ```

- J-Quants を直接利用（例: 日足取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from datetime import date
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数の読み込みと検証（自動 .env ロード、必須変数チェック）
- kabusys.data
  - jquants_client.py — API クライアント（取得 / 保存ユーティリティ）
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py — ETL ジョブ（run_daily_etl など）
  - news_collector.py — RSS 収集・DB 保存・銘柄抽出
  - calendar_management.py — 営業日判定・カレンダー更新ジョブ
  - stats.py / features.py — Z スコア正規化等のユーティリティ
  - audit.py — 発注〜約定の監査ログスキーマ
- kabusys.research
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — forward returns / IC / summary
- kabusys.strategy
  - feature_engineering.py — raw factor を正規化し features テーブルへ保存
  - signal_generator.py — features と ai_scores を統合して signals を生成
- kabusys.execution / kabusys.monitoring
  - 発注層 / 監視のプレースホルダ（実装の拡張箇所）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - (その他 data モジュール)
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
    - monitoring/
      - (モジュール実装予定)
- pyproject.toml / setup.cfg / .gitignore （プロジェクトルート）

---

## 運用上の注意・トラブルシュート

- 環境変数の未設定
  - 必須値が欠けていると `kabusys.config._require` により ValueError が発生します。`.env` を作成してください。
- DuckDB ファイルのパーミッション
  - `init_schema` は親ディレクトリを自動作成しますが、書き込み権限があるか確認してください。
- J-Quants API レート制限
  - ライブラリは 120 req/min のレート制御とリトライを実装していますが、過度な同時実行やループに注意してください。
- RSS ニュース収集のセキュリティ
  - SSRF 防止のため、非 http/https スキームやプライベートアドレスへのアクセスは拒否されます。
- テスト
  - モジュール内でネットワークやファイルI/Oを呼び出す箇所は差し替え（モック）可能な設計です。ユニットテストでは依存注入や環境変数制御を利用してください。

---

## 今後の拡張案

- execution 層のブローカー連携（kabuステーション等）と注文送信・再試行ロジック強化
- AI モデル統合（ai_scores の算出ワークフロー）
- Web UI / ダッシュボードによる監視・手動介入
- テスト用の docker-compose（DuckDB・サンプルデータ取り込み自動化）

---

必要であれば README に含める具体的な .env.example、実行用スクリプトのテンプレート、あるいは cron / Airflow ジョブ定義の例を追加します。どれを追加しますか？