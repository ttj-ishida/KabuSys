# KabuSys

日本株向けの自動売買システム（ライブラリ）です。J-Quants / kabu ステーション等から市場データ・財務データ・ニュースを取得し、特徴量作成・シグナル生成・ETL・監査ログ等の基盤機能を提供します。

主な設計方針：
- DuckDB をデータストアに利用し、Raw → Processed → Feature → Execution の多層スキーマを提供
- ルックアヘッドバイアス防止を重視（計算は target_date 時点のみのデータを使用）
- 冪等性（ON CONFLICT / idempotent 保存）を重視
- 外部 API 呼び出しはクライアントモジュールに集約（認証・リトライ・レート制御実装）

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（jquants_client）：日足・財務・マーケットカレンダー取得、保存（冪等）
  - RSS ベースのニュース収集（news_collector）：前処理・SSRF対策・article→raw_news保存・銘柄紐付け
  - ETL パイプライン（data.pipeline）：差分取得・バックフィル・品質チェックを含む日次ETL
  - 市場カレンダー管理（data.calendar_management）

- データスキーマ管理
  - DuckDB スキーマ初期化（data.schema.init_schema）：全テーブルとインデックスを作成

- 研究 / 戦略
  - ファクター計算（research.factor_research）：Momentum / Value / Volatility / Liquidity 等
  - 特徴量エンジニアリング（strategy.feature_engineering）：正規化・ユニバースフィルタ・features テーブルへの書込
  - シグナル生成（strategy.signal_generator）：ファクター・AIスコア統合、BUY/SELLシグナル生成、signals へ保存
  - 研究支援：特徴量探索（research.feature_exploration）・統計ユーティリティ（data.stats）

- 発注 / 監査（骨組み）
  - Execution / audit モジュール群：signal→order→execution を追跡する監査テーブル群（設計済）

- ユーティリティ
  - 環境変数管理（config）：.env 自動読み込み（プロジェクトルート検出）と必須変数チェック
  - 統計ユーティリティ（zscore 正規化等）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （本 README のコードベースは src/kabusys 以下で実装されています）

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   最低限の依存例：
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクトに setup/requirements があれば pip install -e . や requirements.txt を利用してください）

4. 環境変数設定
   プロジェクトルートに `.env` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（必須 / 任意）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu API 用パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — 通知用 Slack トークン
   - SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネルID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

5. データベース初期化
   Python REPL やスクリプトから DuckDB スキーマを作成します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要 API の例）

以下はライブラリの主要な使い方例です。実運用時はログ・例外処理・スケジューラ（cron/airflow 等）を組み合わせてください。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（価格・財務・カレンダー取得＋品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- 特徴量作成
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2024, 1, 15))
  print(f"features upserted: {count}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  n = generate_signals(conn, target_date=date(2024, 1, 15))
  print(f"signals written: {n}")

- ニュース収集ジョブ（銘柄紐付けに既知銘柄セットを渡す）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  res = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)

- J-Quants からデータを強制取得して保存（jquants_client の fetch/save を直接利用）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

ログレベルや動作モード（paper_trading/live）は環境変数で制御できます（KABUSYS_ENV, LOG_LEVEL）。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数管理（.env 自動ロード、必須チェック）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（認証・リトライ・保存ロジック）
  - news_collector.py       — RSS 収集・前処理・DB保存・銘柄抽出
  - schema.py               — DuckDB スキーマ定義・初期化
  - stats.py                — zscore_normalize 等統計ユーティリティ
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  — マーケットカレンダーの管理／ユーティリティ
  - audit.py                — 監査ログ用テーブル DDL（signal / order / execution トレース）
  - features.py             — data.stats の公開ラッパー
- research/
  - __init__.py
  - factor_research.py      — Momentum / Volatility / Value の計算
  - feature_exploration.py  — forward returns / IC / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py  — features テーブル構築（正規化・ユニバースフィルタ）
  - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
- execution/                 — 発注・実行関連（モジュール骨組み）
- monitoring/                — 監視／通知関連（Slack 等）

（README に掲載されている以外にも多くの補助関数やユーティリティが実装されています）

---

## 環境・運用の注意点

- .env 自動読み込み：
  - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して検出します。CWD に依存しない動作。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- データ整合性：
  - many-to-many の紐付けや外部キーに関して DuckDB のバージョン差異（ON DELETE CASCADE 未サポート等）を意識した実装になっています。削除時はアプリ側で順序制御が必要です。

- 認証・レート制御：
  - J-Quants API のレート上限（120 req/min）を Respect するため内部でスロットリングしています。大量取得時はスロットリングの影響を考慮してください。

- ルックアヘッドバイアス：
  - すべての戦略計算は target_date 時点までの情報のみを使用するよう設計されています。研究コードや手動クエリでも同原則を守ってください。

- 本番モード：
  - KABUSYS_ENV による切替（development / paper_trading / live）が用意されています。is_live / is_paper / is_dev のプロパティで動作分岐できます。

---

## よくある操作（チェックリスト）

- 初回セットアップ：
  - .env を用意（JQUANTS_REFRESH_TOKEN 等）
  - pip install duckdb defusedxml
  - init_schema("data/kabusys.duckdb")

- 毎日運用（例）：
  - run_daily_etl を実行してデータを更新
  - build_features → generate_signals の順で戦略実行
  - signals を監視して発注キューに投入（execution 層と連携）

---

## 開発 / 貢献

- コードスタイルとテストを整備してください。自動環境ロードを使う際の副作用に注意（CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨）。
- 新しい外部依存を追加する場合は setup/requirements に反映し、README も更新してください。

---

問題や改善提案があれば、実装箇所（data.pipeline / strategy.* / data.jquants_client 等）を参照の上、Issue を作成してください。