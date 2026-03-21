# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をバックエンドにして、J-Quants からのデータ収集、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどを含むワークフローを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を備えたモジュール群です。

- データ収集（J-Quants API）／保存（DuckDB）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（JPX）
- ファクター（Momentum / Value / Volatility / Liquidity）計算（research）
- 特徴量エンジニアリング（正規化・フィルタ）と features テーブルへの保存
- シグナル生成（final_score 計算、BUY/SELL 生成）と signals テーブルへの保存
- ニュース収集（RSS）と銘柄紐付け
- 監査ログ（signal → order → execution のトレース）
- 環境変数管理（.env の自動読み込み、設定バリデーション）

設計方針のポイント:
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみを使用
- DuckDB を用いた冪等保存（INSERT ... ON CONFLICT）とトランザクション制御
- J-Quants API 呼び出しはレート制限とリトライを備える
- 研究（research）モジュールは本番の発注層に依存しない設計

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（価格・財務・カレンダー）、差分取得・バックフィル・品質チェック
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注〜約定の監査ログテーブル定義
  - stats / features: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計測、統計サマリー
- strategy/
  - feature_engineering: 生ファクターの統合・正規化・ユニバースフィルタ適用・features 保存
  - signal_generator: features と ai_scores を組み合わせた final_score 計算、BUY/SELL 生成、signals 保存
- config.py: 環境変数からの設定取得（自動 .env 読み込みロジック含む）
- pipeline や各モジュールはトランザクションで原子性を確保し、冪等性を重視

---

## セットアップ手順

前提:
- Python 3.9+（typing の記法と一部ライブラリ利用を想定）
- DuckDB を利用可能な環境

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - （標準ライブラリのみで実装された部分も多いですが、DuckDB と defusedxml は必須です）

   ※ 他に Slack API と通信するコードや kabu API/証券会社連携がある場合は別途パッケージが必要になる可能性があります。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（config.py が自動ロード）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（主な）環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   簡単な .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベーススキーマの初期化
   - Python REPL やスクリプトで DuckDB スキーマを初期化します。
   - 例:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
     これにより必要なテーブル・インデックスが作成されます。

---

## 使い方（簡単なワークフロー例）

以下は代表的な一連の処理フロー（Python スニペット）です。

1. DB 初期化
   ```
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL 実行（市場カレンダー更新 → 価格・財務差分取得 → 品質チェック）
   ```
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量作成（features テーブルの生成）
   ```
   from datetime import date
   from kabusys.strategy import build_features

   n = build_features(conn, target_date=date(2025, 3, 20))
   print(f'features upserted: {n}')
   ```

4. シグナル生成（signals テーブルへ保存）
   ```
   from kabusys.strategy import generate_signals

   total = generate_signals(conn, target_date=date(2025, 3, 20))
   print(f'total signals saved: {total}')
   ```

5. ニュース収集（RSS）と銘柄紐付け
   ```
   from kabusys.data.news_collector import run_news_collection

   known_codes = {'7203', '6758', '9984'}  # 事前に用意した有効銘柄セット
   stats = run_news_collection(conn, known_codes=known_codes)
   print(stats)
   ```

6. カレンダー夜間更新ジョブ
   ```
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f'calendar saved: {saved}')
   ```

注意点:
- run_daily_etl / run_prices_etl 等は内部で J-Quants API（jquants_client）を利用します。JQUANTS_REFRESH_TOKEN が必須です。
- ETL は差分取得・バックフィルのロジックを持ち、既存データとの整合性に配慮しています。
- generate_signals は ai_scores テーブルの存在も参照します（未登録時は中立扱い）。

---

## 設定・環境

- 設定オブジェクト: kabusys.config.settings
  - プロパティ経由で設定値を取得できます（例: settings.jquants_refresh_token）。
  - 有効な KABUSYS_ENV: development, paper_trading, live（settings.is_live / is_paper / is_dev が利用可能）
  - LOG_LEVEL の妥当性チェックあり（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- .env の読み込み順序:
  - OS 環境変数 > .env.local > .env
  - 自動読み込みはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- データベース:
  - DuckDB を推奨（デフォルト path: data/kabusys.duckdb）
  - 監視用途などに SQLite を別途使用することを想定（SQLITE_PATH）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイルと役割です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＋保存ユーティリティ）
    - news_collector.py      — RSS 収集・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — 日次 ETL（run_daily_etl 等）
    - calendar_management.py — カレンダー判定 / 更新ジョブ
    - features.py            — zscore_normalize の再エクスポート
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ用 DDL 定義
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（ユニバースフィルタ・正規化・UPSERT）
    - signal_generator.py    — final_score 計算・BUY/SELL 生成・signals 保存
  - execution/
    - __init__.py            — 発注層（将来的な拡張）
  - monitoring/              — 監視／ジョブ管理等（将来拡張）

（ファイル数が多いため、上は主要モジュールの抜粋です。各ファイルは docstring と設計コメントを豊富に持ちます）

---

## 運用上の注意 / 補足

- J-Quants API:
  - レート制限（デフォルト 120 req/min）を固定間隔スロットリングで管理
  - リトライ（指数バックオフ）、401 発生時はリフレッシュトークンから ID トークンを自動更新して再試行
- ニュース収集:
  - RSS の XML パースには defusedxml（XML Bomb 対策）を使用
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策を実装
- データ品質:
  - pipeline.run_daily_etl は品質チェック（quality モジュール）を呼ぶ設計になっています（quality モジュールは別実装想定）
  - スキップや警告はログに出力され、致命的でない限り処理を継続する設計
- 本番運用:
  - KABUSYS_ENV を `live` にすることで本番判定が可能（settings.is_live）
  - 発注 / execution 層は別モジュールで拡張して接続してください（現在はスキーマと監査ログの骨格が用意されています）

---

## 貢献・拡張点（例）

- execution 層のブローカー接続（kabu API / 他ブローカー）の実装
- 品質チェック（quality モジュール）の実装・拡充
- AI スコア生成パイプライン（ai_scores の計算・投入）
- モニタリング・アラート（Slack 通知や Prometheus エクスポーター）

---

README は以上です。  
必要であれば、セットアップ手順のスクリプト例（requirements.txt、Dockerfile、systemd ユニット例）や、各モジュールの API 使用例を追加で作成します。どの情報がほしいか教えてください。