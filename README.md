# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けのデータ基盤・特徴量生成・シグナル生成から発注監査までを含む
自動売買システムのコアライブラリ群です。DuckDB をデータストアに用い、J-Quants API 等から
データを取得して ETL → 特徴量生成 → シグナル生成 → 発注ログの流れをサポートします。

主な設計方針
- ルックアヘッドバイアス回避（各処理は target_date 時点の情報のみを使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- テスト容易性（id_token 注入やモックしやすい構造）
- 最小限の外部依存（標準ライブラリ + 必要最小限のライブラリ）

---

## 機能一覧

- 環境設定管理
  - `.env` / OS 環境変数から設定読み込み（プロジェクトルート自動検出）
  - 必須項目の検査・ランタイムチェック（env 値のバリデーション）

- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）・財務データ・JPX カレンダーの取得（ページネーション対応）
  - レート制限・リトライ・401 自動リフレッシュ対応
  - DuckDB への冪等保存（raw_* テーブル）

- ETL パイプライン
  - 差分取得（最終取得日ベース）・バックフィル対応
  - カレンダー調整、品質チェック呼び出し、統合的な日次 ETL 実行

- データスキーマ管理
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 各種インデックスの作成

- 研究用モジュール（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 特徴量生成（strategy.feature_engineering）
  - research モジュールの生ファクターを統合・正規化し `features` テーブルへ UPSERT

- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナル生成、エグジット判定（ストップロス等）
  - `signals` テーブルへの日付単位置換（冪等）

- ニュース収集（data.news_collector）
  - RSS 収集・前処理・記事ID生成（URL 正規化 → SHA-256 の先頭 32 文字）
  - SSRF 対策、Gzip サイズチェック、XML 安全パース（defusedxml）
  - raw_news / news_symbols への安全な保存

- マーケットカレンダー管理
  - 営業日判定・next/prev 営業日取得・範囲内営業日リスト取得
  - カレンダーの夜間更新ジョブ

- 監査ログ（data.audit）
  - signal_events / order_requests / executions など、発注〜約定の監査トレース

---

## セットアップ手順

前提
- Python 3.8+（型ヒントに | を使うため 3.10 推奨）
- DuckDB（Python パッケージで利用）
- ネットワークアクセス（J-Quants / RSS 取得用）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   ※ 実運用ではロギングや Slack 通知、証券会社 API クライアント等が別途必要です。

3. 環境変数（.env）を用意する
   — プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   簡易例（.env.example を参考に作成してください）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL を変更する場合:
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   補足:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化します（テスト用途）。

4. データベース初期化
   - Python REPL やスクリプトで DuckDB スキーマを初期化します。

   例:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

5. （任意）データ収集テスト
   - J-Quants トークンがあれば ETL を実行してデータ取得を試せます（長時間・大量 API 呼び出しに注意）。

---

## 使い方（主要 API の例）

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しないと今日を基準に実行
  print(result.to_dict())

- 特徴量（features）生成
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 15))
  print(f"features upserted: {n}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 15))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効な 4 桁銘柄コードのセット
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)

- J-Quants からの手動フェッチ例
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

注意点
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計です。コネクションの共有やトランザクション設計は呼び出し側で管理してください。
- ETL は API レート制限やネットワーク状況により時間がかかることがあります。
- シグナル生成は features / ai_scores / positions 等のテーブル状態に依存します。期待する挙動を得るには適切な前処理が必要です。

---

## 環境変数一覧（主なもの）

必須（Settings._require により未設定時は例外）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack bot token（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知用）

オプション
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込み無効化フラグ（1 等で無効）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB など（デフォルト data/monitoring.db）

---

## ディレクトリ構成（抜粋）

src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                       # 環境変数・設定管理
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py            # J-Quants API クライアント（取得・保存）
   │  ├─ news_collector.py            # RSS ニュース収集・DB 保存
   │  ├─ schema.py                    # DuckDB スキーマ定義・初期化
   │  ├─ stats.py                     # 統計ユーティリティ（zscore_normalize 等）
   │  ├─ pipeline.py                  # ETL パイプライン（run_daily_etl 等）
   │  ├─ features.py                  # features 再エクスポート
   │  ├─ calendar_management.py       # 市場カレンダー管理・ジョブ
   │  └─ audit.py                     # 監査ログスキーマ
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py           # Momentum/Volatility/Value の計算
   │  └─ feature_exploration.py       # 将来リターン / IC / summary 等
   ├─ strategy/
   │  ├─ __init__.py
   │  ├─ feature_engineering.py       # features テーブル生成ロジック
   │  └─ signal_generator.py          # final_score 計算・signals 書き込み
   ├─ execution/
   │  └─ __init__.py                  # 発注層（実装は別途）
   └─ monitoring/                      # 監視・モニタリング関連（実装ファイル未列挙）

上記は主要コンポーネントの一覧です。実際のファイルはさらに多くの関数・ユーティリティを含みます。

---

## 開発上のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- jquants_client の HTTP 周りやニュース取得の外部呼び出しはモックしやすい設計です（関数に id_token 注入、_urlopen の差し替え等）。
- DuckDB の初期化は init_schema() を呼ぶだけで完了します。":memory:" を渡せばインメモリ DB を使えます（ユニットテスト向け）。
- strategy 層は発注 API に依存しないため、signals テーブルを生成してから外部の execution 層で実際の発注処理を別コンポーネントとして扱えます。

---

この README はコードベースに含まれるモジュール仕様に基づく概要です。詳細な設計（StrategyModel.md / DataPlatform.md 等）や運用手順は別ドキュメントを参照してください。必要であれば README に追加したい使い方のサンプルや運用ガイドを生成します。