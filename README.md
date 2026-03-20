# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータ収集・特徴量生成・シグナル生成・発注監査などを想定した
自動売買プラットフォームのコアライブラリ群です。DuckDB をデータレイク／分析用 DB として利用し、
J-Quants API や RSS ニュースを取り込み、戦略・研究・実行レイヤーを分離した設計を取っています。

主な目的
- 市場データ（株価・財務・カレンダー）を安定的に取得・保存する ETL
- 研究フェーズで算出した raw ファクターを戦略用に正規化・合成する特徴量処理
- features / ai_scores を統合して売買シグナルを生成する戦略ロジック
- ニュース収集（RSS）・銘柄抽出・DB 保存の実装
- DuckDB スキーマの定義・初期化と監査ログ設計

※ この README はコードベース（src/kabusys）に基づいた概要・導入・使い方の例を示します。

## 機能一覧（ハイライト）
- 環境変数管理
  - .env / .env.local を自動ロード（プロジェクトルート判定は .git / pyproject.toml）
  - 必須設定は Settings クラス経由で取得（欠如時は例外）
- データ取得 / 保存（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - Rate limiting（120 req/min）、リトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分）・バックフィル対応
  - 品質チェック呼び出しと結果集約
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- スキーマ管理
  - DuckDB 用の完全なDDL定義／初期化（Raw・Processed・Feature・Execution 層）
- 研究（research）モジュール
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Spearman）・統計サマリー
- 戦略（strategy）モジュール
  - 特徴量生成（build_features: Z スコア正規化・ユニバースフィルタ等）
  - シグナル生成（generate_signals: コンポーネント別スコア合算、Bear 抑制、SELL 判定）
- ニュース収集（news_collector）
  - RSS フィード取得（SSRF 対策・Gzip/サイズ制限・XML 扱いに安全な defusedxml）
  - 記事正規化・ID 生成（URL 正規化→SHA256）、raw_news / news_symbols への冪等保存
  - テキストからの銘柄抽出（4 桁コード）
- 監査ログ（audit）
  - signal_events / order_requests / executions など、トレース可能な監査テーブル定義

## 必要条件
- Python 3.10 以上（型注釈で | が使われているため）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください。

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. パッケージと依存のインストール
   - プロジェクトパッケージを編集可能インストール
     ```
     pip install -e .
     ```
   - 最低依存を個別インストール
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動で読み込まれます（.git または pyproject.toml が検出された場合）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 `.env`（実運用では機密値を適切に管理してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから初期化できます（DUCKDB_PATH は settings.duckdb_path で指定可能）。
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # または
   conn = init_schema(":memory:")  # テスト用
   ```

## 使い方（主要 API サンプル）

以下は最小限の利用例です。運用環境ではログ設定やエラーハンドリング、Scheduler（cron 等）を併用してください。

- 環境設定参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live, settings.env)
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（build_features）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date(2025, 3, 1))
  print(f"features upserted: {count}")
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2025, 3, 1))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols 保存）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 上場銘柄セット
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

## 設定（環境変数一覧）
主に Settings クラスで参照される環境変数（主要なもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（任意）

必須項目が設定されていない場合、Settings のプロパティ参照時に ValueError が送出されます。

## ディレクトリ構成（概要）
以下は主要なファイル/モジュールのツリー（src/kabusys 配下）です。細かな補助モジュールはコメントに記載の設計仕様に従っています。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存/認証/レート制御）
    - news_collector.py      — RSS 収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義と init_schema()
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — data の公用インターフェース
    - calendar_management.py — カレンダー管理／バッチ更新ジョブ
    - audit.py               — 発注〜約定の監査ログ DDL（監査用テーブル）
    - execution/             — 発注/ブローカー連携層（空のパッケージ）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・ボラ・バリュー等のファクター計算
    - feature_exploration.py — IC 計算・将来リターン計算・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・フィルタ）
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - monitoring/              — 監視用 DB / ロギング等（実装ファイルはここに配置想定）

（実際のプロジェクトには tests/、scripts/、docs/ などが追加されることを推奨します）

## 運用上の注意点
- DuckDB のファイルはバックアップ・ロールフォワード戦略を検討してください。
- J-Quants のレート制限や API 利用規約を遵守してください（実装内でレート制御をしています）。
- production（live）環境では機密情報（トークン・パスワード）を安全に管理（Vault 等）してください。
- features / signals の算出はルックアヘッドバイアス防止のために target_date 時点のデータのみを使用する設計になっています。運用でデータ参照タイミングに注意してください。
- ニュース収集では外部 URL の検証（SSRF 対策）とレスポンスサイズ制限を実装していますが、運用環境でも取得ソースの健全性確認を行ってください。

---

この README はコードベースの概要と代表的な使い方を示しています。追加の詳細（DB テーブル仕様、StrategyModel.md、DataPlatform.md など）はプロジェクト内ドキュメントに従ってください。必要であれば、README に含めるスクリプト例や運用手順のテンプレートも作成しますのでお知らせください。