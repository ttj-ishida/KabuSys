# KabuSys

日本株向け自動売買プラットフォームのライブラリ実装（モジュール群）。  
このリポジトリはデータ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDBスキーマなどを含む設計になっています。

主な設計方針は、
- ルックアヘッドバイアスの回避（target_date 時点のデータのみ使用）
- 冪等性（DB 書き込みは ON CONFLICT / トランザクションで保護）
- テスト容易性（id_token 注入等）
- 外部依存の最小化（pandas 等に依存せず標準ライブラリ + 必要パッケージで実装）
です。

---

## 機能一覧

- 環境設定管理
  - .env / OS 環境変数から自動読み込み（プロジェクトルート検出）。自動ロードを無効化するフラグあり。
  - `settings` から必要な設定を取得（J-Quants トークン、kabu API パスワード、Slack トークン等）。

- データ取得 / 保存（J-Quants クライアント）
  - 日足（OHLCV）・財務データ・マーケットカレンダーの取得（ページネーション対応）。
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュを実装。
  - DuckDB への冪等保存（ON CONFLICT/UPDATE）。

- ETL パイプライン
  - 差分更新（最終取得日を参照して必要分のみ取得）・バックフィル対応。
  - 市場カレンダー・日足・財務データの一括 ETL（品質チェックフックあり）。

- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義・初期化。
  - インデックス・DDL をまとめて作成する `init_schema()`。

- 特徴量計算（research / strategy）
  - Momentum, Volatility, Value 等のファクター計算（prices_daily / raw_financials を参照）。
  - Z スコア正規化ユーティリティ。
  - features テーブルへの正規化済み特徴量のバルク UPSERT。

- シグナル生成
  - features と ai_scores を統合して最終スコアを算出、BUY/SELL シグナルを作成して signals テーブルへ保存。
  - Bear レジーム検知、stop-loss 等のエグジット判定を実装。
  - 重みのカスタム指定、閾値調整が可能。

- ニュース収集
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、XML セキュリティ対策（defusedxml）。
  - raw_news / news_symbols への冪等保存、記事から銘柄コード抽出。

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ、営業日判定（DB 優先、未登録日は曜日フォールバック）。
  - next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティ。

- 監査ログ（audit）
  - シグナル → 発注 → 約定 のトレースを支援する監査テーブル群（監査用DDL を備える）。

---

## 動作環境・前提

- 推奨 Python バージョン: 3.10+
  - 型注釈や union 型（|）を使用しているため 3.10 以上を想定しています。
- 主な依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API）を利用するためアクセストークンが必要。

---

## セットアップ手順

1. リポジトリをクローンして、開発環境に入る
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）開発インストール:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード
     - SLACK_BOT_TOKEN: Slack Bot トークン（通知等に使用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: デフォルトは data/kabusys.duckdb
     - SQLITE_PATH: 監視 DB のデフォルトは data/monitoring.db
   - 自動 .env 読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（例）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: でインメモリ DB 可
     ```

---

## 使い方（主要な操作例）

以下は簡単な利用例です。実運用ではログ設定や例外処理を適切に行ってください。

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)   # 今日分の ETL を実行
  print(result.to_dict())
  ```

- 特徴量をビルドして features テーブルへ保存
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2026, 1, 31))
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2026, 1, 31))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes を与えると本文から銘柄抽出を行い news_symbols を更新する
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  d = date(2026, 2, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: デフォルト DB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると .env 自動読み込みを無効化

環境変数が不足している場合、多くのプロパティは ValueError を投げます（settings._require により）。

---

## ディレクトリ構成（主要ファイル）

※ 実際のソースは `src/kabusys/` 配下に配置されています。主なファイル一覧:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得 / 保存）
    - news_collector.py      -- RSS ニュース収集・前処理・保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - stats.py               -- 統計ユーティリティ（Z スコア等）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- 市場カレンダー更新 / 営業日ユーティリティ
    - features.py            -- data.stats の再エクスポート
    - audit.py               -- 監査ログ用 DDL
    - execution/             -- （発注周りはここで管理、実装は拡張想定）
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Volatility / Value 計算
    - feature_exploration.py -- IC, forward returns, summary
  - strategy/
    - __init__.py
    - feature_engineering.py -- features ビルド（正規化・ユニバースフィルタ）
    - signal_generator.py    -- final_score 計算・BUY/SELL 生成
  - execution/                -- 発注実行層（実際の broker 接続等はここで拡張）
  - monitoring/               -- 監視 / アラート用機能（拡張想定）

---

## 注意点・運用上のヒント

- DuckDB ファイルのバックアップ・運用:
  - データファイルはデフォルトで data/ 配下に作成されます。定期的にバックアップしてください。
- レート制限 / API エラー:
  - jquants_client は固定間隔スロットリングとリトライを実装していますが、長時間のバッチや復旧時は API レートに注意してください。
- セキュリティ:
  - .env に API トークンを平文で保存する場合はアクセス制御を行ってください。
  - news_collector は SSRF・XML 攻撃対策（SSRF リダイレクト検査、defusedxml）を実装しています。ただし外部データは常に注意して扱ってください。
- 本番環境:
  - KABUSYS_ENV を `live` に設定すると本番モードを表すフラグが ON になります。実際の発注フローを組む際には慎重なリスク管理を実装してください。

---

## 貢献・拡張ポイント

- execution 層のブローカー接続（kabu ステーション等）実装
- リアルタイム監視・アラート機能（monitoring）
- AI スコア生成 / モデル学習コードの統合
- 単体テスト・CI 設定、型チェック（mypy）や static analysis の追加

---

以上がこのコードベースの概要と導入手順です。必要なら、README にサンプル .env.example の内容や具体的な CI / デプロイ手順、詳しいスキーマ図や StrategyModel.md へのリンクなども追加できます。何を優先して追記するか教えてください。