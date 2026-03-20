# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ミニマム実装）。
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマなど
戦略開発と運用の基盤となるモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象とした自動売買システムの基盤ライブラリです。  
主な目的は次のとおりです。

- J-Quants API による市場データ・財務データ・カレンダーの取得（レート制限・リトライ対応）
- DuckDB ベースのデータスキーマと冪等な保存ロジック
- ETL パイプライン（差分取得・品質チェック）
- 研究（research）で得たファクターを利用した特徴量作成・正規化
- 戦略レイヤーでのシグナル生成（BUY / SELL）
- ニュース RSS 収集と銘柄紐付け
- カレンダー管理・営業日判定・監査ログ（audit）等のユーティリティ

設計方針として「ルックアヘッドバイアス防止」「冪等性」「外部依存を最小化」を重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限、リトライ、トークン自動更新）
  - schema: DuckDB のテーブル定義・初期化（Raw/Processed/Feature/Execution 層）
  - pipeline: 日次 ETL（差分更新、バックフィル、品質チェック）
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定
  - stats: Z スコア正規化などの統計ユーティリティ
  - features: zscore_normalize の公開ラッパー
- research/
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算（forward returns）、IC（Spearman）等の研究支援
- strategy/
  - feature_engineering: raw ファクターを正規化して `features` テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出し `signals` テーブルへ出力
- execution/, monitoring/（骨格：発注処理や監視ロジックを置く想定）
- config: .env 自動読み込み、環境設定アクセス（settings オブジェクト）
- audit: 監査ログ用スキーマ（signal_events / order_requests / executions）

主要な API（例）
- DuckDB スキーマ初期化: kabusys.data.schema.init_schema(db_path)
- 日次 ETL 実行: kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- 特徴量作成: kabusys.strategy.build_features(conn, target_date=...)
- シグナル生成: kabusys.strategy.generate_signals(conn, target_date=...)
- RSS 収集: kabusys.data.news_collector.run_news_collection(conn, sources=..., known_codes=...)

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の union 表記などを想定）
- 必要なライブラリは pip でインストールします。

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージをプロジェクトに追加している場合は requirements.txt / pyproject.toml を利用）

4. 環境変数の設定
   - プロジェクトルートに `.env` および（必要なら）`.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- KABUSYS_ENV: 実行環境（有効値: development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - `:memory:` を指定すればインメモリ DB が使えます。

---

## 使い方（簡単な例）

以下は主要ワークフローのサンプル例です。実運用スクリプトやジョブに組み込んでください。

- DuckDB の初期化と日次 ETL 実行
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量のビルド（research で計算した raw ファクターを正規化して features テーブルへ保存）
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features
    from kabusys.config import settings

    conn = get_connection(settings.duckdb_path)
    count = build_features(conn, date(2024, 1, 1))
    print(f"features upserted: {count}")

- シグナルの生成
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import generate_signals
    from kabusys.config import settings

    conn = get_connection(settings.duckdb_path)
    total = generate_signals(conn, date(2024, 1, 1), threshold=0.6)
    print(f"signals total: {total}")

- ニュース収集ジョブ
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    from kabusys.config import settings

    conn = get_connection(settings.duckdb_path)
    known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
    results = run_news_collection(conn, sources=None, known_codes=known_codes)
    print(results)

- J-Quants API を直接呼んでデータ取得→保存
    from kabusys.data import jquants_client as jq
    from kabusys.data.schema import get_connection
    from datetime import date

    conn = get_connection("data/kabusys.duckdb")
    recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = jq.save_daily_quotes(conn, recs)
    print(f"fetched={len(recs)} saved={saved}")

注意:
- ここで示したすべての操作は DuckDB 接続を直接操作します。トランザクションや例外管理は各関数内で行われますが、複合処理を行う際は呼び出し側で適切に例外処理を追加してください。
- settings（kabusys.config.settings）から環境設定を取得できます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソース配置例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py  -- RSS 収集・前処理・保存・銘柄抽出
    - schema.py          -- DuckDB スキーマ定義と init_schema
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）
    - stats.py           -- 統計ユーティリティ（zscore_normalize）
    - features.py        -- features 用ラッパー
    - calendar_management.py -- カレンダー管理ユーティリティ
    - audit.py           -- 監査ログ用スキーマ（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py      -- momentum/volatility/value 計算
    - feature_exploration.py  -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  -- features テーブル構築
    - signal_generator.py     -- final_score 計算と signals 生成
  - execution/
    - __init__.py
    # （発注周りの実装を置く場所）
  - monitoring/
    # （監視・メトリクス・アラートの実装を置く場所）

ドキュメント参照:
- DataSchema.md, DataPlatform.md, StrategyModel.md などの設計文書に基づいた実装（コード内コメントで参照）

---

## 動作上の注意点 / 実運用に向けた補足

- 環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれか。live 実行時の発注ロジックは慎重にテストしてください。
- .env の自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- 冪等性:
  - jquants_client.save_*、news_collector.save_raw_news 等は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で実装されています。
- セキュリティ:
  - news_collector は SSRF 対策（ホスト検査、リダイレクト検証）・XML パースを defusedxml で安全に処理します。
- テスト / モック:
  - ネットワーク操作を行う関数は外部化・注入しやすい設計（例: id_token を注入、_urlopen をモック可能）になっています。

---

## 貢献 / バグ報告

バグ報告やプルリクエストはリポジトリの Issue / Pull Request をご利用ください。  
設計ドキュメント（DataPlatform.md / StrategyModel.md 等）に従った実装を心がけていますので、仕様に関する質問や改善提案は歓迎します。

---

以上がこのコードベースの概要と基本的な使い方です。詳しい内部動作や設計仕様は各モジュール内のドキュメント文字列（docstring）と関連設計ドキュメントを参照してください。