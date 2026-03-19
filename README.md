# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得／ETL、ファクター計算、特徴量生成、シグナル生成、監査・実行層の基礎機能を提供します。

---

## プロジェクト概要

KabuSys は日本株運用のためのオープンなコンポーネント群です。主な目的は以下です。

- J-Quants API などから市場データ・財務データ・カレンダーを取得して DuckDB に格納する（ETL）。
- 研究（research）で算出した生ファクターを整備・正規化して戦略用特徴量を構築する。
- 特徴量と AI スコアを統合して売買シグナルを生成する。
- ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）などのユーティリティを提供する。
- 発注／約定／ポジションのためのスキーマ（Execution 層）定義を含む。

設計上の特徴：
- DuckDB を中心にローカルでの高速な分析・永続化を想定。
- 冪等性（ON CONFLICT での更新）・ルックアヘッドバイアス回避・レート制御・堅牢なエラーハンドリングを重視。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、レートリミット）
  - ETL パイプライン（prices / financials / market calendar）
  - market_calendar のバッチ更新・営業日計算ユーティリティ
- データ格納スキーマ
  - raw / processed / feature / execution 層を含む DuckDB スキーマ定義と初期化
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（research/factor_research）
  - クロスセクション Z スコア正規化ユーティリティ
  - 特徴量構築（strategy/feature_engineering）
- シグナル生成
  - features / ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成（strategy/signal_generator）
  - エグジット判定（ストップロス、スコア低下等）
- ニュース収集
  - RSS 取得・前処理・記事ID生成・銘柄抽出・DB保存（data/news_collector）
  - SSRF・XML攻撃対策・サイズ制限などセキュリティ考慮
- 監査（Audit）
  - signal → order_request → execution までのトレーサビリティテーブル（audit モジュール）
- ユーティリティ
  - 環境設定読み込み（.env 自動ロード / settings）
  - 統計ユーティリティ（zscore_normalize など）

---

## セットアップ手順

前提
- Python 3.9+ を想定（typing の表記より）。プロジェクト内 pyproject.toml がある場合はそれを参照してください。
- DuckDB を使用するためネイティブライブラリが必要（pip で duckdb をインストール）。

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （追加で Slack やその他の外部ライブラリを使う場合は個別にインストールしてください）

3. 開発インストール（パッケージ配布用があれば）
   - pip install -e .

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（usage に必要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション等の API パスワード（発注関連）
- SLACK_BOT_TOKEN       : Slack 通知を使う場合
- SLACK_CHANNEL_ID      : Slack チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL   : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

---

## 使い方（簡単な例）

以下は最小限のワークフロー例です。実運用ではログ設定・エラーハンドリング・スケジューリングを行ってください。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# データベースファイルを作成して全テーブルを初期化
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行（J-Quants トークンは環境変数 JQUANTS_REFRESH_TOKEN を使用）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3. 特徴量を構築（研究モジュールが prices_daily / raw_financials を用意している前提）
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, date(2025, 1, 15))  # target_date に対して features を計算・保存
print(f"features upserted: {n}")
```

4. シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, date(2025, 1, 15))
print(f"signals written: {count}")
```

5. ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
# conn は init_schema で作成した接続を使う
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```

注意:
- 上記の関数群は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スクリプトやジョブランナーから直接呼ぶのが想定です。
- J-Quants API 呼び出しはレート制限や再試行ロジックを内包していますが、実行環境のネットワーク設定や認証情報は適切に管理してください。

---

## 環境変数詳細

主要なキーと意味:

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) : kabu API のパスワード（実行・発注機能で使用）
- KABUSYS_ENV : 環境。development / paper_trading / live（デフォルト development）
- LOG_LEVEL : ログレベル（デフォルト INFO）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
- DUCKDB_PATH : DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視・モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 : .env 自動ロードを無効化

.env ファイルのパースはシェル風の簡易フォーマットをサポートします（export プレフィックス、シングル/ダブルクォート、インラインコメント等）。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下に実装が入っています。主要なモジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings の定義。.env の自動読み込みロジックを含む。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ、rate limiter、リトライ）
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - pipeline.py
      - 日次 ETL ワークフロー（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
    - news_collector.py
      - RSS 収集・前処理・DB 挿入・銘柄抽出
    - calendar_management.py
      - 営業日判定・カレンダー更新ジョブ・next/prev trading day ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ用の DDL 定義（signal_events, order_requests, executions 等）
    - pipeline.py (ETL パイプライン)
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC（Spearman） / 統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターの合成・ユニバースフィルタ・Zスコア正規化→ features テーブルへ UPSERT
    - signal_generator.py
      - final_score の計算、BUY/SELL シグナル生成、signals テーブルへの保存
  - execution/
    - __init__.py
      - （発注・ broker 接続等の実装を想定するプレースホルダ）
  - monitoring/
    - （監視・アラート・Slack 通知等の実装が入る想定）

各モジュールには docstring と設計方針・処理フローが記載されており、内部コメントで仕様（例: StrategyModel.md, DataPlatform.md）への参照が多くあります。

---

## 開発・運用上の注意点

- DuckDB のバージョンや SQL の互換性に注意してください（特に外部キーや ON DELETE 挙動に関する注記がコード中にあります）。
- J-Quants API のレート制限（デフォルト 120 req/min）を守るため、クライアントは内部でスロットリングを行いますが、複数プロセスから同時に叩く環境ではさらに上位の制御が必要です。
- ルックアヘッドバイアス対策として各関数は target_date 時点までに使えるデータのみを参照する設計になっています。ETL と解析・シグナル生成の順序を守ってください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードを無効化できます。

---

必要であれば、インストール用の pyproject.toml / requirements.txt の例、より詳しい実行例、CI 用ジョブ定義、SQL スキーマの ER 図、API 認証手順（J-Quants）などの追加ドキュメントを作成します。どの部分を優先して詳述しますか？