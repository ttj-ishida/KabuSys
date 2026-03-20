# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義／初期化など、運用に必要な主要コンポーネントを提供します。

注意: 本リポジトリはライブラリ実装の抜粋を含みます。実際の運用前に設定や環境依存の要素（API トークン、kabuステーション連携など）を必ず確認してください。

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）  
    - ページネーション、レート制限、リトライ、トークン自動リフレッシュに対応
  - raw データを DuckDB に冪等保存（ON CONFLICT / トランザクション）
- ETL パイプライン
  - 差分取得（バックフィル対応）、品質チェックフック、日次 ETL 実行エントリ
- データスキーマ
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義と初期化
- 研究・特徴量計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC（Spearman）計算、統計サマリー
- 戦略
  - 特徴量結合・正規化（features テーブル作成）
  - シグナル生成（final_score 計算、Bear レジーム判定、BUY / SELL シグナルの作成）
- ニュース収集
  - RSS フィード収集、前処理、記事の冪等保存、銘柄抽出と紐付け（news_symbols）
  - SSRF 対策、XML の安全パース（defusedxml）、サイズ制限
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days などのユーティリティ
- 監査ログ設計（order/exec のトレースを前提とした DDL）

## 必要環境

- Python >= 3.10（typing の | None 構文を使用）
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

（プロジェクトの実際の requirements.txt / pyproject.toml を参照してください）

## 環境変数（必須 / 推奨）

このライブラリは環境変数（または .env ファイル）で設定を読み込みます。プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL (任意) — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

.env のフォーマットはシェル互換（export プレフィックス / 引用 / コメントに対応）です。

## セットアップ手順

1. リポジトリをクローンして開発用インストール（編集可能な状態）
   - python パッケージ化がある想定:
     - python -m pip install -e .
2. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （pyproject / requirements があればそれを使用）
3. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、CI / 実行環境で環境変数をセット
4. DuckDB スキーマの初期化
   - 下記の使い方例を参照

## 使い方（主要な操作の例）

下記は Python REPL またはスクリプトから実行する例です。実行前に必ず必要な環境変数を設定してください。

- DuckDB スキーマ初期化
  - from kabusys.config import settings
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - これにより DuckDB ファイルとすべてのテーブル・インデックスが作成されます。

- 日次 ETL の実行（株価 / 財務 / カレンダー）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - result は ETLResult オブジェクト（取得件数・保存件数・品質問題一覧などを含む）

- 特徴量構築（features テーブル作成）
  - from kabusys.strategy import build_features
  - from datetime import date
  - build_features(conn, date(2024, 1, 1))
  - 指定日分を冪等に置き換えます（まず削除してから挿入）。

- シグナル生成
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, date(2024, 1, 1))
  - features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ日付単位で置換します。

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
  - デフォルトソース（Yahoo Finance のカテゴリ RSS）を使用。新規保存件数を返します。

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading_day(conn, some_date)

- J-Quants からのデータ取得（直接呼び出し）
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

注意点:
- ほとんどの書き込み API はトランザクション＋冪等性（ON CONFLICT）に配慮されています。
- ETL / データ取得はネットワークや API のエラーがあり得るため、呼び出し側で適切にログや例外を扱ってください。
- システム実行モードは KABUSYS_ENV に依存します（live モードでは実際の発注を行うコードと連携する想定）。

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                                   # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                          # J-Quants API クライアント & 保存関数
    - news_collector.py                          # RSS ニュース収集・保存
    - schema.py                                  # DuckDB スキーマ定義・初期化
    - stats.py                                   # Zスコアなどの統計ユーティリティ
    - pipeline.py                                # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py                     # マーケットカレンダー管理
    - features.py                                # 公開インターフェース（zscore）
    - audit.py                                   # 監査ログ DDL（audit 用）
    - execution/ (発注関連のプレースホルダ)
  - research/
    - __init__.py
    - factor_research.py                         # Momentum / Volatility / Value 計算
    - feature_exploration.py                     # IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py                     # features テーブル構築（正規化など）
    - signal_generator.py                        # final_score 計算と signals 作成
  - execution/                                    # 発注処理層（実装の拡張想定）
  - monitoring/                                   # 監視・アラート関連（SQLite 等）

上記以外にも補助モジュール（quality チェック等）があります。詳細はソースを参照してください。

## 開発・運用に関する補足

- 自動 .env ロード
  - package import 時にプロジェクトルートから `.env` / `.env.local` を自動ロードします（OS 環境変数 > .env.local > .env の優先度）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 安全性 / 耐障害性
  - ニュース収集は SSRF 対策・受信サイズ制限・安全な XML パーサを採用しています。
  - J-Quants クライアントはレート制限（120 req/min）、指数バックオフ、401 のリフレッシュロジックを実装しています。
- テスト
  - ネットワーク外部依存箇所は ID トークンや HTTP 通信を注入／モックしやすい設計になっています（例: _urlopen の差し替え等）。

## よくある操作コマンド（例）

- スキーマ初期化スクリプト（例）
  - python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"
- 日次 ETL を cron / workflow で実行
  - python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn=init_schema(settings.duckdb_path); print(run_daily_etl(conn).to_dict())"

---

問題や実行時の不明点があれば、どの部分で困っているか（エラー内容や実行したコード・環境設定の抜粋）を教えてください。具体的な使用例や追加のドキュメントを作成します。