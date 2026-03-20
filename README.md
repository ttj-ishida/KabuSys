# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。データ取得・ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・スキーマ管理などを含むモジュール群を提供します。

注: このリポジトリはライブラリ/コンポーネント群の実装であり、実際の運用では設定（API トークン等）と外部サービス（J-Quants、kabuステーション 等）への接続が必要です。

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ実装
- ETL / データ基盤
  - DuckDB ベースのスキーマ定義・初期化（raw / processed / feature / execution 層）
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェックフロー）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
- 特徴量・リサーチ
  - モメンタム / バリュー / ボラティリティ 等のファクター計算（research）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 戦略
  - 特徴量の合成・正規化（features テーブルへの保存）
  - シグナル生成ロジック（final_score 計算、BUY/SELL 判定、エグジット）
- ニュース収集
  - RSS フィード収集（XML パース保護、SSRF 対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- 監査・実行レイヤー（スキーマ）
  - signal / order / executions / positions / audit テーブル群を定義

## 動作要件

- Python 3.10 以上（ソースに明示的な | 型注釈を使用）
- 推奨依存パッケージ（minimal）
  - duckdb
  - defusedxml

実運用では追加の依存（例えば Slack 通知、kabuステーション HTTP クライアントなど）や運用用スクリプトが必要になる可能性があります。

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo_url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - パッケージをローカルインストール（editable）
     - pip install -e .

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

4. 環境変数を設定
   - ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（モジュール kabusys.config による自動読み込み）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数（少なくとも下記は設定してください）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（execution 層を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知を行う場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   その他の設定:
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / ...（デフォルト: INFO）

6. データベース初期化（DuckDB スキーマ作成）
   - Python から:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブルとインデックスが作成されます（冪等）。

## 使い方（主要なAPI例）

下記はライブラリを利用する際の典型的な流れのサンプルコード例です。

1) DB 初期化・接続
- Python REPL / スクリプト例:
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema, get_connection
    conn = init_schema(settings.duckdb_path)

2) 日次 ETL を実行してデータを取り込む
- from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) 特徴量を構築（features テーブルへ保存）
- from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date.today())  # 指定日分を再生成（冪等）

4) シグナル生成
- from kabusys.strategy import generate_signals
  count = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals generated: {count}")

5) ニュース収集ジョブ実行
- from kabusys.data.news_collector import run_news_collection
  known_codes = set(...)  # 既知の銘柄コードセット（抽出用）
  res = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)

6) カレンダー更新ジョブ
- from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意点:
- 多くの関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema() が接続を返すのでこれを流用してください。
- 各 ETL / 保存処理は基本的に冪等になるよう実装されています（ON CONFLICT 等）。

## 推奨運用フロー（簡易）

1. 毎晩（バッチ）:
   - calendar_update_job（市場カレンダー更新）
   - run_daily_etl（当日または営業日分のデータ取得）
   - run_news_collection（ニュース収集）
2. ETL 後:
   - build_features（特徴量生成）
   - generate_signals（シグナル生成）
3. signal → execution 層（別モジュール／ブリッジ）で実際の発注を行う

## 環境変数の例 (.env.example)

例として .env ファイルに次の値を記載します（実際のトークンは安全に管理してください）:

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意: リポジトリには .env.example が無い場合があるため、上記を参考に作成してください。

自動読み込みの優先順位: OS 環境変数 > .env.local > .env。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## 主要モジュール（ディレクトリ構成）

以下は主要なファイル/ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数・設定の読み込み/管理
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント + 保存ロジック
    - schema.py                  - DuckDB スキーマ定義・初期化
    - pipeline.py                - ETL パイプライン、run_daily_etl 等
    - stats.py                   - zscore_normalize など統計ユーティリティ
    - features.py                - 公開インターフェース（zscore再エクスポート）
    - news_collector.py          - RSS 収集・前処理・DB 保存
    - calendar_management.py     - 市場カレンダー管理・営業日判定
    - audit.py                   - 監査ログスキーマ（signal/events/order/execution）
    - ...（quality 等の補助モジュールがある想定）
  - research/
    - __init__.py
    - factor_research.py         - momentum/volatility/value 等のファクター計算
    - feature_exploration.py     - 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     - features テーブル生成（正規化・フィルタ）
    - signal_generator.py        - final_score 計算、BUY/SELL シグナル生成
  - execution/
    - __init__.py                - 発注/約定層のエントリ（実装は別途）
  - monitoring/ (名前は __all__ にあるが実装は省略されている可能性あり)

（上記はリポジトリの内容に基づく主要ファイル一覧です。細かなファイルは実際の tree を参照してください。）

## 開発・デバッグのヒント

- ログレベルは環境変数 `LOG_LEVEL` で制御できます（DEBUG/INFO...）。
- settings.is_live / is_paper / is_dev で実行環境を切り替え可能。
- DuckDB を ":memory:" として渡すとインメモリ DB で単体テストが容易です。
- news_collector.fetch_rss はネットワークアクセスのハンドラを内部で使っているため、単体テストでは _urlopen をモックすると良いです。
- J-Quants クライアントは内部でトークンキャッシュ・自動リフレッシュを行います。テスト時は get_id_token を差し替えたり、_get_cached_token を force_refresh して動作確認できます。

## 注意事項（セキュリティ・運用）

- API トークンやパスワードは必ず安全に保管し、リポジトリにハードコードしないでください。
- ニュース収集では外部 URL を開くため SSRF 等に注意して設計されていますが、運用環境ではさらにネットワーク制限（ファイアウォール等）を推奨します。
- 実際の発注・約定を行う場合は十分なテスト（ペーパートレード・ステージング）とリスク管理が必要です。

---

この README はプロジェクトの概要と主要な使い方をまとめたものです。より詳しい設計仕様（StrategyModel.md、DataPlatform.md、その他のドキュメント）がある場合はそれらを参照してください。質問や追加したい項目があれば教えてください。