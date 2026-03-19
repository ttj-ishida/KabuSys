# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本ドキュメントはプロジェクト概要、主要機能、セットアップ手順、使い方の簡単な例、ディレクトリ構成をまとめています。

注意: 本リポジトリは取引システムの一部または研究用モジュール群を含みます。実運用前に十分な検証・リスク管理を行ってください。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォームのコアライブラリです。  
主に以下のレイヤー／機能を提供します。

- データ取得・ETL（J-Quants API 経由で株価・財務・市場カレンダーを取得）
- DuckDB を用いたデータスキーマ定義と保存（Raw / Processed / Feature / Execution 層）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントを統合した final_score による BUY/SELL 判定）
- ニュース収集（RSS 取得、前処理、銘柄抽出、DB 保存）
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- 発注/監査ログ用のスキーマ（Execution / audit 層）
- 研究用ユーティリティ（将来リターン計算・IC・統計サマリ等）

設計上のポイント:
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみを参照する設計。
- DuckDB をデータレイクとして使用し、SQL と最小限の Python で処理を表現。
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ等を備え冪等性を考慮。

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、トークンリフレッシュ）
  - pipeline: 日次 ETL（run_daily_etl、run_prices_etl、run_financials_etl 等）
  - news_collector: RSS フィード取得と raw_news 保存、銘柄抽出
  - schema: DuckDB テーブル定義と init_schema()
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Zスコア正規化など汎用統計ユーティリティ
- research/
  - factor_research: mom/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン / IC / 統計サマリ等
- strategy/
  - feature_engineering.build_features: ファクター結合・正規化・features テーブル更新
  - signal_generator.generate_signals: final_score 計算・BUY/SELL シグナル生成・signals テーブル更新
- execution/ (発注層の実装用スペース)
- config.py: 環境変数設定読み込み（.env 自動ロード、必須設定チェック）
- monitoring/（監視用・Slack 通知等を想定）

---

## 前提 / 必要要件

- Python 3.9+（ソースは型ヒントに pathlib/typing などを使用）
- duckdb パッケージ
- ネットワーク接続（J-Quants API、RSS 等）
- J-Quants API のリフレッシュトークン等の環境変数

推奨: 仮想環境（venv / poetry / pipenv 等）を利用してください。

---

## 環境変数（主なもの）

以下はアプリケーションから参照される代表的な環境変数です（config.Settings にて取得）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須、通知等）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...、デフォルト INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env → .env.local の順で自動読み込みします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb
   - （その他必要なライブラリがある場合は requirements.txt / pyproject.toml の指示に従ってください）
   - 開発時は editable install:
     - pip install -e .
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example があれば参照）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 必要に応じて DUCKDB_PATH 等を設定
5. データベース初期化
   - Python REPL またはスクリプトで DuckDB スキーマを初期化:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 基本的な使い方（コード例）

注意: ここでは簡単な実行手順例を示します。運用ではログ設定や例外処理を適切に追加してください。

1) DB を初期化する（最初の一度だけ）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から株価・財務・カレンダーを取得して保存）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3) 特徴量作成（features テーブル更新）
```
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

4) シグナル生成
```
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, target_date=date.today(), threshold=0.60)
print("signals generated:", n)
```

5) ニュース収集ジョブ（RSS を取得して raw_news に保存）
```
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出で有効なコード集合（prices_daily などから取得）
known_codes = {"6758", "7203", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新バッチ
```
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("market_calendar saved:", saved)
```

---

## よく使う API（関数一覧, 短縮）

- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- kabusys.data.calendar_management.calendar_update_job(conn)

---

## ディレクトリ構成（主要ファイル / モジュールの説明）

- src/kabusys/
  - __init__.py (パッケージ定義、__version__)
  - config.py
    - 環境変数の自動読み込み、Settings クラス（必須変数取得のヘルパ）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）
    - schema.py : DuckDB スキーマ定義と init_schema()
    - news_collector.py : RSS 取得・前処理・保存・銘柄抽出
    - calendar_management.py : 市場カレンダー管理（営業日判定、更新ジョブ）
    - features.py : zscore_normalize の再エクスポート
    - stats.py : zscore_normalize 等の統計ユーティリティ
    - audit.py : 監査ログ（signal_events / order_requests / executions の DDL）
  - research/
    - __init__.py
    - factor_research.py : モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリ / rank
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py : raw ファクターをマージ・正規化して features テーブルへ
    - signal_generator.py : features + ai_scores 統合による シグナル生成（BUY/SELL）
  - execution/
    - __init__.py （発注実装用のエントリ）
  - monitoring/
    - （監視・Slack 通知等の実装箇所想定）

その他:
- docs/ または *.md（設計文書: DataPlatform.md, StrategyModel.md など）を参照する設計が示唆されています（リポジトリに存在する場合はそちらを参照してください）。

---

## 運用上の注意 / セキュリティ

- 本コードは実際の発注系（ブローカー連携）を含む可能性があるため、テスト環境（paper_trading）と live の環境分離を厳密に行ってください（KABUSYS_ENV）。
- API トークン等のシークレットは .env ファイルや環境変数で安全に管理し、ソース管理にコミットしないでください。
- news_collector は外部 URL を取得するため SSRF 対策（ホスト検査等）を含みますが、運用環境でのネットワークポリシーに注意してください。
- DuckDB ファイルはローカルに保存されます。バックアップやアクセス権限管理を行ってください。

---

## 貢献 / 開発フロー（簡易）

- ブランチを切って機能追加／修正 → プルリクエスト
- 重要な変更はユニットテスト／統合テストを追加（テストフレームワークを導入している場合）
- 環境変数の扱い・機密情報取り扱いに注意

---

必要であれば、README に次の内容を追記できます:
- 実行例のより詳細なスクリプト（cron/systemd/ジョブスケジューラ向け）
- テスト方法（モックを使った jquants_client のテスト例）
- CI / CD 設定例
- 詳細なテーブルスキーマ説明（DataSchema.md の要約）

追記や特定セクションの拡充を希望される場合は、その箇所を指定してください。