# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリです。データ収集（J-Quants / RSS）、ETL、特徴量生成、戦略シグナル生成、発注監査用スキーマなど、取引システムのコア機能をモジュール化して提供します。

---

## 概要

主な設計方針・特徴：

- DuckDB を用いたローカルデータレイク（冪等保存 / ON CONFLICT 更新）
- J-Quants API からの差分取得（レート制御、リトライ、トークン自動リフレッシュ）
- RSS ニュース収集（SSRF / XML 攻撃対策、トラッキングパラメータ削除）
- 研究モジュールと運用モジュールの分離（look-ahead bias に配慮）
- 戦略用の特徴量正規化・スコア統合・売買シグナル生成（冪等処理）
- 環境設定は .env または環境変数から読み込み（自動ロード機能有）

---

## 機能一覧

- 環境/設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）
  - 必須環境変数取得ヘルパ
- データ層（kabusys.data）
  - J-Quants クライアント（fetch / save の idempotent 実装）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - ニュース収集（RSS 収集、記事正規化、銘柄抽出、DB保存）
  - マーケットカレンダー管理（営業日判定、next/prev）
  - 統計ユーティリティ（Z スコア正規化）
  - 監査ログスキーマ（signal → order → execution トレース用）
- 研究 / ファクター（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）
- 発注・実行（kabusys.execution）および監視（kabusys.monitoring）は拡張ポイント（パッケージ API 用意）

セキュリティ・堅牢性の設計ポイント：
- API レート制御とリトライ（J-Quants）
- RSS の SSRF / private host ブロック、gzip/size 上限
- DB 保存はトランザクションで原子性確保
- 自動環境ロードは無効化可能（テスト時）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法などを使用）
- pip が利用可能

1. リポジトリをクローン / コピーして作業ディレクトリへ移動。

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   最低限の依存例：
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクト内に `pyproject.toml` / `requirements.txt` がある場合はそれに従ってください）
   - duckdb: データ格納・クエリ実行用
   - defusedxml: RSS XML の安全なパース

4. 環境変数の設定
   プロジェクトルートに `.env` を置くか、OS 環境変数として設定します。主な必須変数：
   - JQUANTS_REFRESH_TOKEN (J-Quants 用 refresh token)
   - KABU_API_PASSWORD (kabuステーション API パスワード)
   - SLACK_BOT_TOKEN (Slack 通知用)
   - SLACK_CHANNEL_ID (Slack 通知先チャンネル ID)

   任意 / デフォルト可能：
   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト localhost）
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB 等（例: data/monitoring.db）

   テスト等で自動 .env ロードを無効化する場合：
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. データベース初期化
   Python REPL やスクリプトで DuckDB スキーマを作成します（パスは設定に合わせて変更）。
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（主要な操作例）

以下は代表的な処理の呼び出し例です。詳細は各モジュールの docstring を参照してください。

- 日次 ETL（カレンダー / 株価 / 財務 を差分取得し品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（戦略用 features テーブルをターゲット日で置換）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print("features upserted:", count)
  ```

- シグナル生成（features と ai_scores を統合して signals に書き込む）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print("signals written:", total)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants の ID トークン取得（必要なら）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

ログレベル・実行環境切替は環境変数 `LOG_LEVEL` / `KABUSYS_ENV` で制御できます（development / paper_trading / live）。

---

## ディレクトリ構成

主要ファイル/モジュールの構成（ルートは `src/kabusys/`）:

- __init__.py
- config.py
  - 環境変数自動読み込み、設定アクセス用 Settings
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save、レート制御、リトライ）
  - news_collector.py — RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（日次 ETL、差分取得ヘルパ）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — data.stats の再エクスポート
  - calendar_management.py — market_calendar の管理・営業日判定
  - audit.py — 監査ログ用 DDL（signal / order_request / executions 等）
  - (その他: quality, audit 周りが想定される拡張点)
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン・IC・サマリー解析
- strategy/
  - __init__.py
  - feature_engineering.py — raw ファクターの統合・正規化・features へ UPSERT
  - signal_generator.py — final_score 集計・BUY/SELL シグナルの生成・signals へ書き込み
- execution/
  - __init__.py (発注連携の実装箇所。拡張ポイント)
- monitoring/
  - __init__.py (監視・通知等の拡張ポイント)

---

## 補足 / 注意事項

- Python バージョンは 3.10 以上を推奨（型注釈の union 表記等）。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます（settings.duckdb_path）。
- J-Quants API のレート限界（120 req/min）を尊重する実装（固定間隔スロットリング）があります。大量取得時は時間を考慮してください。
- ニュース収集モジュールは外部ネットワークからのコンテンツを処理します。RSS の不正データ・大容量応答・内部ネットワーク参照を防ぐ保護が組み込まれていますが、運用時はソースの信頼性を確認してください。
- production（live）環境での発注実装は別途 broker 実装が必要です。本ライブラリは戦略・ETL・監査基盤を提供しますが、実際の発注接続は `execution` 層で実装する想定です。

---

この README はコードベースの概要と基本的な使い方を示すものです。各モジュールの詳細な挙動・引数・戻り値はソースコードの docstring を参照してください。質問や追記したい内容があればお知らせください。