# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ説明書です。  
本パッケージはデータ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査/スキーマ管理等の機能を提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを持つ日本株自動売買向けプラットフォームのライブラリです。

- データ収集（J-Quants API 経由で株価・財務・市場カレンダー取得）
- ETL パイプライン（差分取得、保存、品質チェック）
- DuckDB ベースのデータスキーマ管理・初期化
- 研究（research）用ファクター計算・解析ユーティリティ
- 戦略（strategy）層：特徴量正規化・シグナル生成
- ニュース収集（RSS）と銘柄抽出
- 監査（audit）・実行（execution）用テーブル群

設計上のポイント：
- 冪等性（DB への保存は ON CONFLICT / DO UPDATE 等で重複防止）
- ルックアヘッドバイアス回避（各処理は target_date 時点のデータのみを参照）
- レート制限・リトライ・トークン自動更新を備えた API クライアント

---

## 主な機能一覧

- データ（data/）
  - J-Quants クライアント（レート制限、リトライ、トークンリフレッシュ）
  - raw/processed/feature/execution 各レイヤーの DuckDB スキーマ初期化（init_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース取得 / 保存（RSS パース、URL 正規化、SSRF 対策、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Z スコア正規化）
- 研究（research/）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ
- 戦略（strategy/）
  - 特徴量作成（build_features: 生ファクター統合・正規化・features テーブルへUPSERT）
  - シグナル生成（generate_signals: final_score 計算、BUY/SELL 生成、signals テーブルへ保存）
- 監査/実行（audit / execution）
  - 監査用テーブル・発注ログなど（監査設計に基づくテーブル群）

---

## 要件

- Python 3.10 以上（型注釈の `X | Y` 記法を使用）
- 必要なパッケージ（一部抜粋）:
  - duckdb
  - defusedxml

依存はプロジェクトの setup/requirements に従ってください（本 README はコードベースからの要点を記載しています）。

---

## 環境変数

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（Settings）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

主な任意 / デフォルトあり:
- KABUSYS_ENV : 開発モード（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロード無効化フラグ
- KABUSYS_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : 監視用 sqlite パス（デフォルト `data/monitoring.db`）

設定が不足していると Settings プロパティが ValueError を投げます。`.env.example` を参考に `.env` を作成してください。

---

## セットアップ手順（ローカル）

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - またはプロジェクトの requirements / setup に従う
4. 環境変数を設定（例 .env をプロジェクトルートに配置）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
5. データベーススキーマ初期化
   - 下記「使い方」を参照して DuckDB を初期化

注意:
- テスト時・CI で自動 .env 読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（抜粋サンプル）

以下は基本的な操作フロー（Python REPL / スクリプト）例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルト path は data/kabusys.duckdb
```

2) 日次 ETL（株価・財務・カレンダーの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得・保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 抽出に使う有効銘柄コードセット
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # 各ソースごとの新規保存件数
```

6) カレンダー更新（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

その他:
- J-Quants へ直接アクセスしたい場合は jquants_client の fetch_* / save_* を利用できます。
- ETL の戻り値（ETLResult）は品質チェック結果やエラーを含みます。

---

## 開発・デバッグのヒント

- 自動 .env 読み込みを無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- settings で環境値が無効な場合は ValueError が投げられる（KABUSYS_ENV / LOG_LEVEL 等）
- J-Quants API 呼び出しはモジュール内でレートリミッタとリトライを実装。ユニットテストでは jquants_client._request や _urlopen 等をモックしてください。
- ニュース取得は defusedxml を使い、SSRF/サイズ上限等の保護が入っています。外部ネットワーク呼び出しを切る場合は fetch_rss をモック。

---

## ディレクトリ構成

（重要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動ロード、Settings クラス
  - data/
    - __init__.py
    - schema.py
      - DuckDB スキーマ定義、init_schema(), get_connection()
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 系 + 認証）
    - pipeline.py
      - ETL パイプライン (run_daily_etl, run_prices_etl, ...)
    - news_collector.py
      - RSS 取得・正規化・DB 保存、銘柄抽出
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day, next_trading_day, ...）
    - audit.py
      - 監査ログ用テーブル定義（signal_events, order_requests, executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features：生ファクター合成・正規化・features への保存
    - signal_generator.py
      - generate_signals：final_score 計算・BUY/SELL 生成・signals への保存
  - execution/
    - (発注/実行レイヤー。今回の抜粋では空の __init__ がある)
  - monitoring/
    - (監視・メトリクス等のためのモジュール群を想定)

---

## ライセンス / 貢献

この README はコードベースに基づく概要説明です。実際の運用・商用利用時は適切なライセンス条項・利用規約・API 利用条件に従ってください。貢献方法（PR や Issue）についてはリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

---

必要であれば、README にサンプル .env.example のテンプレやより詳細な開発フロー（テストの実行方法、CI 設定、依存一覧）を追加できます。どの情報を補完すればよいか教えてください。