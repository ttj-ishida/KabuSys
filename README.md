# KabuSys

KabuSys は日本株の自動売買プラットフォームのコアライブラリです。J-Quants API などから市場データを取得して DuckDB に保存し、リサーチ → 特徴量生成 → シグナル生成 → 発注のワークフローを支援するモジュール群を提供します。

- 対象: 日本株（OHLCV / 財務 / カレンダー / ニュース収集）
- 設計方針: 冪等性、ルックアヘッドバイアス回避、外部依存最小化（可能な限り標準ライブラリ）

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（ページネーション、レート制限、トークン自動リフレッシュ、リトライ）
  - DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution 層）
  - 差分 ETL（価格・財務・市場カレンダーの差分取得と保存）
- ニュース収集
  - RSS フィードの取得、前処理、raw_news への冪等保存
  - 記事から銘柄コード抽出（4桁コード）
  - SSRF・XML 脅威対策・受信サイズ制限などの安全対策
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン・IC（情報係数）計算、ファクター統計サマリー
- 特徴量エンジニアリング
  - リサーチで得た生ファクターを正規化（Z スコア）・合成し `features` テーブルへ保存
  - ユニバースフィルタ（価格・流動性）適用、外れ値クリップ
- シグナル生成
  - features + ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成、保有ポジションのエグジット判定
  - signals テーブルへの日付単位置換（冪等）
- カレンダー管理
  - JPX の営業日判定、next/prev_trading_day、範囲内営業日の取得
  - 夜間バッチでカレンダー差分更新
- 監査（Audit）
  - シグナル → 発注 → 約定 のトレース用テーブル定義（order_request_id 等の冪等キー）
- 共通ユーティリティ
  - 環境変数設定管理、設定オブジェクト（settings）
  - 統計ユーティリティ（Z スコア正規化等）

---

## 必要条件 / 依存関係

- Python >= 3.10（型注釈で `X | Y` を使用）
- 主要パッケージ:
  - duckdb
  - defusedxml

インストール例（開発環境）:
```bash
python -m pip install -U pip
python -m pip install duckdb defusedxml
# パッケージを editable にインストールする場合（プロジェクトルートで）
python -m pip install -e .
```

※ packaging（setup.py/pyproject.toml）がある場合はそちらに従ってください。

---

## 環境変数

パッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（必須/デフォルトを示す）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/…（デフォルト: INFO）

settings は `from kabusys.config import settings` で参照できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境の準備・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   python -m pip install duckdb defusedxml
   # または
   python -m pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

4. DuckDB スキーマ初期化
   Python スクリプトまたは対話的に:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（よく使う API の例）

- 日次 ETL（市場カレンダー → 価格 → 財務 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量生成（research モジュールの factor を正規化して features に保存）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  conn.close()
  ```

- ニュース収集（RSS → raw_news, news_symbols）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は既知の銘柄コード集合（抽出のため）
  known_codes = {"7203", "6758", "9432"}
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  conn.close()
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 開発用ヒント

- 自動 .env ロードを無効にしたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト実行時に有用です。

- ログレベルは `LOG_LEVEL` で制御します（DEBUG/INFO/...）。

- J-Quants へのリクエストは内部でレートリミット（120 req/min）とリトライを行います。API キーの管理は `JQUANTS_REFRESH_TOKEN` を使用します。

---

## ディレクトリ構成（抜粋）

（プロジェクトの Python パッケージは `src/kabusys` 配下）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — 日次 ETL パイプライン（差分取得 / 品質チェック）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - news_collector.py — RSS フィード取得・保存・銘柄抽出
    - calendar_management.py — 市場カレンダー管理、営業日判定、更新ジョブ
    - features.py — features の公開インターフェース（再エクスポート）
    - audit.py — 監査ログ用スキーマ定義
    - execution/ — 発注/約定 関連（ディレクトリ、実装のエントリポイント）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / サマリー計算
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量正規化・UPSERT
    - signal_generator.py — final_score 計算、BUY/SELL 生成
  - execution/ — 実行層（発注 API との連携ポイント）
  - monitoring/ — 監視・メトリクス（SQLite 等との連携想定）

---

## ライセンス・貢献

ライセンスはリポジトリのルート（LICENSE）をご確認ください。バグ報告・改善提案は Issue / Pull Request を歓迎します。

---

README はここまでです。必要であれば、以下を追加で作成できます:
- .env.example のサンプル
- より詳細な API リファレンス（関数別）
- 運用手順（本番・paper_trading 用のデプロイ例）
ご希望があれば教えてください。