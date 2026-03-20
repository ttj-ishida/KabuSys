# KabuSys

日本株向け自動売買基盤ライブラリ（モジュール群）。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。

主な目的は「研究→運用」までのワークフローをサポートすることです。リサーチコード（research/*）で計算した生ファクターを加工して features テーブルへ保存し、戦略ロジックで売買シグナルを生成します。データ取得は J-Quants API を想定し、DuckDB に保存・管理します。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（パッケージルート検出）
  - 必須設定取得のラッパー（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）取得（ページネーション対応・レート制御・リトライ）
  - 財務データ取得
  - マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT）
- ETL / パイプライン
  - 差分取得（バックフィル対応）、品質チェックフック、日次バッチ実行
- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- 特徴量エンジニアリング（strategy/research 層連携）
  - momentum / volatility / value の算出
  - クロスセクション Z スコア正規化・クリップ
  - features テーブルへの UPSERT（日付単位で置換、冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL のランク付けと signals テーブルへの保存
  - 保有ポジションのエグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出（紐付け）
  - SSRF 対策、gzip/サイズ・XML パース安全対策（defusedxml）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮の最小セット）:
```
pip install duckdb defusedxml
```

（プロジェクト配布で requirements.txt を用意している場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをチェックアウトしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```

2. 環境変数を用意する（プロジェクトルートに `.env` / `.env.local` を配置）
   - 自動読み込み: package 起点で .git または pyproject.toml を探索して .env を読み込みます。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用 DB）パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化（Python から）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主な API）

ここでは代表的な使い方を示します。各関数は詳細な docstring を持っています。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # :memory: でインメモリ可
  ```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants の個別データ取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
  financials = fetch_financial_statements(date_from=date(2024,1,1), date_to=date(2025,1,15))
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

---

## ログ・デバッグ

- LOG_LEVEL 環境変数でログレベルを制御します（デフォルト INFO）。
- ETL / API 呼び出しは内部で警告・例外処理を行い、失敗しても全体が停止しない設計です。重大なエラーは例外または ETLResult.errors に記録されます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュールは src/kabusys 配下に配置されています。代表的なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - pipeline.py                 — ETL パイプライン（差分取得 / 日次 ETL）
    - schema.py                   — DuckDB スキーマ定義と初期化
    - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py           — RSS ニュース収集 / 保存 / 銘柄抽出
    - features.py                 — features の公開ラッパ
    - calendar_management.py      — 市場カレンダー管理ユーティリティ
    - audit.py                    — 監査ログ / 発注トレーサビリティ（DDL）
    - pipeline.py                 — ETL の実装（上記）
  - research/
    - __init__.py
    - factor_research.py          — momentum/value/volatility 計算
    - feature_exploration.py      — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      — features 作成ワークフロー
    - signal_generator.py         — final_score 計算・シグナル生成
  - execution/                     — 発注・execution 層（未実装または拡張ポイント）
  - monitoring/                    — 監視用モジュール（存在すれば）

注: 上記はコードベースに含まれる主要モジュールの一覧です。詳しい機能や入出力仕様は各モジュールの docstring を参照してください。

---

## 設計方針・注意点（要約）

- ルックアヘッドバイアス対策: 取得時刻（fetched_at）や target_date 基準でデータ参照を行い、未来情報を参照しない設計。
- 冪等性: DB 保存は基本的に ON CONFLICT / UPSERT を使用して上書き禁止/更新を行う。
- 安全性: RSS の XML パースは defusedxml を利用し、SSRF 対策やレスポンスサイズ上限を設ける。
- テスト容易性: id_token 注入や KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストが容易。
- DB: DuckDB をローカル永続化（デフォルト: data/kabusys.duckdb）で使用。

---

## 追加情報 / 貢献

- バグ報告・機能要望は Issue を立ててください。
- 大きな変更（DDL 変更・スキーマ変更等）は互換性に注意して議論してください。
- モジュールに付された docstring を優先して参照してください（各関数は入力・出力・副作用を明記しています）。

---

以上。README に不足している情報（実例スクリプト、CI、Docker 化など）があれば、用途に合わせて追加します。必要であれば英語版 README も作成できます。