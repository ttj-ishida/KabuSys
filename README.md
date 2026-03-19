# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
DuckDB をデータレイクに用い、J-Quants API からデータを取得して ETL → 特徴量生成 → シグナル生成までをサポートします。  
本リポジトリは戦略設計（research）と運用（execution / monitoring）を分離したレイヤード設計を採用しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダーなどの市場データを安全に取得・永続化（DuckDB）
- データ品質チェック、差分更新、バックフィルを備えた ETL パイプライン
- 研究環境で作成した raw factor を正規化・合成して features テーブルへ保存する特徴量パイプライン
- 正規化済みの特徴量と AI スコアを統合して売買シグナル（BUY / SELL）を生成するシグナル生成ロジック
- RSS を利用したニュース収集・記事 → 銘柄紐付け
- 発注・約定・ポジション等を保存する監査・実行レイヤ（スキーマ定義）

設計の要点:
- ルックアヘッドバイアス防止のため、すべての計算は target_date 時点で利用可能なデータのみを使用
- DuckDB への保存は冪等（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）で実装
- 外部 API 呼び出しは jquants_client に集約。レートリミット・リトライ・トークンリフレッシュ等に対応
- ニュース取得は SSRF 対策、XML パースリスク対策、サイズ制限などを実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・レート制御・トークン自動更新）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 差分 ETL（prices / financials / market calendar）と日次 ETL 実行（run_daily_etl）
  - news_collector: RSS 取得 → raw_news 保存 → 銘柄抽出・紐付け
  - calendar_management: 営業日判定・next/prev_trading_day 等ユーティリティ
  - stats: Z スコア正規化など統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value ファクターの計算
  - feature_exploration: 将来リターン計算（forward returns）、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering.build_features: raw factor をマージ・フィルタ・正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
- config: 環境変数読み込み・設定ラッパー（.env 自動読み込み、必須キーのチェック）
- news / audit / execution / monitoring 用の補助モジュール群（スキーマ・監査ログ等）

---

## 要件

- Python 3.10 以上（型注記に PEP 604 形式の Union 型を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作するユーティリティも多いですが、DuckDB や defusedxml 等は必須です。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発時は pip install -e . を検討
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## 環境変数 / 設定 (.env)

config モジュールはプロジェクトルートの `.env`（および `.env.local`）を自動的に読み込みます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主に使用する環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等との連携パスワード
- KABU_API_BASE_URL — kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡易 `.env` 例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- `.env.local` は `.env` 上書き用に優先して読み込まれます。
- OS 環境変数は .env の設定より優先されます。

---

## セットアップ手順（最小構成）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストールがあれば:
   # pip install -e .
   ```

2. 必要な環境変数を設定（`.env` を作成）
   - 上記の `.env` 例を参考に必須キーを設定してください。

3. DuckDB スキーマの初期化
   Python REPL やスクリプトから実行できます:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   `":memory:"` を渡すとインメモリ DB になります（テスト用途）。

---

## 使い方（代表的なワークフロー例）

以下は最も基本的な日次ワークフローの例です。

1. DuckDB を初期化して接続を取得
   ```python
   from kabusys.data.schema import init_schema, get_connection

   conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を使用
   # 2回目以降は get_connection を使用して既存 DB に接続可能
   # conn = get_connection("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   res = run_daily_etl(conn, target_date=date.today())
   print(res.to_dict())
   ```

3. 特徴量（features）を構築
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナルを生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   signals_written = generate_signals(conn, target_date=date.today())
   print(f"signals written: {signals_written}")
   ```

5. ニュース収集ジョブを実行（任意）
   ```python
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", "..."}  # 既知の銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

6. 実運用時は `KABUSYS_ENV=paper_trading` / `live` を使い、ログレベルや Slack 通知を調整してください。

---

## API 主要関数（抜粋）

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（スキーマ作成）
  - get_connection(db_path) → 既存 DB への接続

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) → ETLResult（取得・保存・品質チェック）

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), save_daily_quotes(...)
  - fetch_financial_statements(...), save_financial_statements(...)
  - fetch_market_calendar(...), save_market_calendar(...)
  - get_id_token(refresh_token=None)

- kabusys.research
  - calc_momentum(conn, date), calc_volatility(...), calc_value(...),
  - calc_forward_returns(...), calc_ic(...), factor_summary(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

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
      - (その他: quality.py 等想定)
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
      - (監視用モジュール等)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートに配置する想定）

各モジュールは用途別に分離されており、研究用コード（research）と運用コード（data / strategy / execution）が明確に分かれています。

---

## 運用上の注意点

- 環境変数の管理:
  - 機密情報（トークン・パスワード）は `.env` / シークレットマネージャ等で安全に管理してください。
- テストと本番の分離:
  - KABUSYS_ENV を使って挙動（paper_trading / live）を切り替えてください。
- API レート制限:
  - jquants_client は 120 req/min を想定して制御していますが、複数プロセスで同時に呼ぶ場合は注意が必要です。
- DB バックアップ:
  - DuckDB ファイルは定期的にバックアップしてください（監査データは削除しない方針）。
- セキュリティ:
  - news_collector は SSRF 対策と XML パース安全対策を実装していますが、外部フィード追加時は信頼性を確認してください。

---

## 貢献 / 開発

- コードフォーマットやテストを用意し、ユニットテストで jquants_client 等の外部呼出しはモックしてください。
- 新しい ETL ジョブや品質チェックは data/ 以下に追加し、pipeline.run_daily_etl に統合してください。
- ドキュメント（DataPlatform.md / StrategyModel.md）が参照される実装方針を満たすようにしてください。

---

## ライセンス

（リポジトリの LICENSE を参照してください）

---

必要であれば、README にサンプル .env.example、より詳しい起動スクリプト（systemd / cron / Airflow などのサンプル）、テストの書き方やサンプル SQL（テーブル確認クエリ）を追記できます。どの情報を追加しますか？