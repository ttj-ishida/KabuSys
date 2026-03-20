# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に使い、J-Quants API からのデータ取得、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む設計になっています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に蓄積する ETL パイプライン
- 研究環境で計算した生ファクターを正規化・合成して戦略用特徴量（features）を構築する機能
- features と AI スコアを統合して売買シグナルを生成する機能
- RSS ベースのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日判定 / 更新ジョブ）
- 発注・約定・ポジション管理や監査用スキーマの定義（DB レイヤ）

設計方針として、ルックアヘッドバイアス回避、冪等性（idempotency）、テスト容易性（依存注入可能）、外部ライブラリへの依存最小化（標準ライブラリ＋必須パッケージ）を重視しています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（取得・リトライ・レート制御・自動トークン更新）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
- データスキーマ
  - raw / processed / feature / execution 層のテーブル定義と初期化（init_schema）
- 研究用ファクター・特徴量
  - momentum / volatility / value 等のファクター計算（research パッケージ）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
  - 特徴量構築（strategy.feature_engineering.build_features）
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成（strategy.signal_generator.generate_signals）
- ニュース収集
  - RSS 取得、前処理、raw_news への冪等保存、銘柄コード抽出と紐付け（data.news_collector）
  - SSRF 対策、Gzip / サイズ制限、XML の安全パース
- 監査ログ
  - signal_events / order_requests / executions など監査用スキーマ（データのトレーサビリティ）

---

## 必要条件（Prerequisites）

- Python 3.9+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの実際の requirements.txt があればそちらを使用してください。）

インストール例（仮）:
pip install duckdb defusedxml

開発インストール:
pip install -e .

---

## 環境変数（主な設定項目）

環境変数は .env ファイルまたは OS 環境変数から自動読み込みされます（パッケージ内の kabusys.config がプロジェクトルートを走査し .env / .env.local を読みます）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

必須の環境変数が未設定の場合は、kabusys.config.Settings のプロパティアクセス時に ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を作成して有効化（推奨）
3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - 必要最低限: pip install duckdb defusedxml
4. .env ファイルを用意
   - プロジェクトルートに .env または .env.local を作成
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
5. DB スキーマ初期化
   - 以下のセクションのサンプルを参照して DuckDB のスキーマを作成してください。

注意: 自動環境変数ロードはプロジェクトルートの存在（.git または pyproject.toml）を基に決定されます。CI やテストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトからの基本的な操作例です。

- DuckDB スキーマ初期化

from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（J-Quants からデータ取得して保存）

from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

- 特徴量構築（features テーブルの作成／更新）

from kabusys.strategy import build_features
from datetime import date

# 既に conn は init_schema 等で作成済みとする
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

- シグナル生成（signals テーブルの作成／更新）

from kabusys.strategy import generate_signals
from datetime import date

num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {num_signals}")

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → news_symbols 紐付け）

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

# known_codes は既知の銘柄コードセット（例は空）
known_codes = set()  # または DB から銘柄一覧を取得してセット化
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

- カレンダー更新バッチ

from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market calendar saved: {saved}")

注意点:
- 多くの機能は DuckDB のテーブル存在と適切なデータ前提で動作します（先に init_schema→ETL を実行して必要なテーブルとデータを揃えてください）。
- J-Quants API を利用する機能は JQUANTS_REFRESH_TOKEN の設定が必要です。

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理と自動 .env ロード、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・再試行）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - news_collector.py
      - RSS 収集・前処理・保存・銘柄抽出
    - calendar_management.py
      - market_calendar の管理・営業日判定
    - features.py
      - data.stats の再エクスポート
    - audit.py
      - 監査ログ用スキーマ定義
    - (その他: quality などは参照されるがここには含まれない場合があります)
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー 等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features を構築して features テーブルへ保存
    - signal_generator.py
      - features と ai_scores を統合して signals を生成
  - execution/
    - __init__.py
    - （発注・execution に関する実装スケルトンや別モジュール）
  - monitoring/
    - （監視 / メトリクス関連の実装場所）

（実際のリポジトリではさらに細分化されたファイルが存在します。上は主要モジュールの概観です。）

---

## 開発上の注意・設計メモ

- 冪等性を重視した設計:
  - API の保存関数は ON CONFLICT DO UPDATE / DO NOTHING を利用し、再実行しても重複を作らないようにしています。
- ルックアヘッドバイアス対策:
  - 特徴量・シグナル生成は target_date 時点のデータのみを使用する設計（将来情報を使わない）。
  - jquants_client は fetched_at を UTC で保存して「いつデータが取得可能になったか」を記録します。
- セキュリティ:
  - news_collector は SSRF と XML 攻撃対策を実装しています（リダイレクト検査・ホストのプライベートアドレス検出・defusedxml 利用）。
- ロギングとエラーハンドリング:
  - 各処理は例外を捕捉してロギングし、可能な限り他処理を継続する方針（Fail-Fast ではない）。
- テストについて:
  - 環境依存部分（HTTP 呼び出し、ファイル読み書き）は注入やモックがしやすい設計（例: id_token 注入、_urlopen の差し替え）です。

---

## よくある操作例（まとめ）

1. スキーマ初期化:
   - conn = init_schema(settings.duckdb_path)
2. 市場カレンダー更新:
   - calendar_update_job(conn)
3. 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）:
   - run_daily_etl(conn)
4. 研究用ファクター計算 → 特徴量構築:
   - build_features(conn, target_date)
5. シグナル生成:
   - generate_signals(conn, target_date)

---

## 貢献 / ライセンス

- ここでは明示的な CONTRIBUTING や LICENSE は含めていません。実際のリポジトリには LICENSE / CONTRIBUTING を追加してください。

---

README は簡易版です。さらに詳しい仕様（StrategyModel.md / DataPlatform.md / SecurityGuidelines.md など）のドキュメントがあれば合わせて参照してください。必要であれば、README に実行例や CI / デプロイ手順、テスト手順を追加します。