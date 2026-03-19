# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
DuckDB を用いたデータレイヤ、J-Quants からのデータ収集、特徴量生成、シグナル生成、ニュース収集、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的に向けて設計された Python パッケージです。

- J-Quants API などから市場データ・財務データ・カレンダー・ニュースを収集して DuckDB に保存する ETL（差分更新）パイプライン
- 研究モジュールで計算した生ファクターを正規化・合成して strategy 用の特徴量テーブルを構築
- 正規化済み特徴量と AI スコア等を組み合わせて売買シグナルを生成
- ニュース RSS から記事を安全に収集・前処理・DB 保存し、銘柄紐付けを行う
- 発注／約定／ポジション等を記録するスキーマ（監査・トレーサビリティ）

設計方針の例:
- ルックアヘッドバイアスを防ぐため、target_date 時点の情報のみを用いる
- DuckDB を主要な永続層とし、冪等性（ON CONFLICT / トランザクション）を重視
- 外部 API 呼び出しはクライアント層に集約し、リトライ・レート制御・トークン自動更新を備える

---

## 主な機能一覧

- data/
  - jquants_client.py: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン管理）
  - schema.py: DuckDB スキーマ定義 & 初期化（raw / processed / feature / execution 層）
  - pipeline.py: 日次 ETL（差分更新、バックフィル、品質チェックの統合）
  - news_collector.py: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management.py: JPX カレンダー管理・営業日判定ユーティリティ
  - stats.py: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research.py: モメンタム / ボラティリティ / バリューなどのファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration.py: 将来リターン計算、IC 計算、ファクター統計
- strategy/
  - feature_engineering.py: raw ファクターを正規化・フィルタして features テーブルへ保存
  - signal_generator.py: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
- その他: audit（監査ログ用 DDL）、execution / monitoring（層のプレースホルダ）

---

## 要件

- Python 3.10 以上（型注釈に `|` を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```
（実運用では requirements.txt をプロジェクトに用意して pip install -r でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 自動読み込みはデフォルトで有効。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB スキーマを初期化
   下記「使い方」の例を参照して DB を初期化してください。

---

## 環境変数（主なもの）

以下の環境変数が使用されます（不足時は Settings._require により ValueError が発生するものがあります）。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- Kabuステーション API
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（省略時は http://localhost:18080/kabusapi）
- Slack（通知用）
  - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（省略時 data/monitoring.db）
- 実行環境
  - KABUSYS_ENV: one of {development, paper_trading, live}（省略時 development）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要なユースケース）

以下は Python REPL またはスクリプトでの簡単なサンプルです。事前に必要な環境変数を設定し、依存をインストールしてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# デフォルトパスは settings.duckdb_path（.env で変更可能）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants からデータ取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date=None で今日の処理
print(result.to_dict())
```

3) 特徴量の構築（strategy.features）
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, date(2025, 1, 15))
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得→raw_news に保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使用する有効コードの集合（省略可）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # ソース名ごとの新規保存件数
```

6) J-Quants クライアント直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings から refresh token を自動取得
quotes = fetch_daily_quotes(date_from=None, date_to=None)  # 全件取得は注意（ページング）
```

注意:
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ります。init_schema の戻り値または get_connection を使用してください。
- ETL / feature / signal などは target_date を基準に「その時点で知り得る」データのみを用いる設計です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - calendar_management.py
  - features.py
  - audit.py
  - audit/... (DDL とインデックス)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
- その他: monitoring（将来的な監視機能等）

（実際のリポジトリでは src 配下にさらにファイルが存在します。上は本 README に含まれる主要モジュール抜粋です）

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上推奨（型注釈に `X | Y` を使用）
- DuckDB: 大量データを扱うので適切なファイル配置・バックアップを行ってください
- J-Quants の API レート制限（120 req/min）をコード側で尊重していますが、大量取得・並列処理時は注意が必要です
- news_collector は外部 RSS を解析するため、SSRF・XML Bomb 等に対する防御（実装済み）がありますが、運用時は信頼できるフィードを設定してください
- 環境変数自動読み込みはプロジェクトルートの `.env` / `.env.local` を優先して読み込みします。テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます

---

## 参考（トラブルシュート / よくある確認点）

- .env が読み込まれない場合:
  - プロジェクトルートが検出されない（.git または pyproject.toml が見つからない）と自動ロードはスキップされます。
  - 自動ロードを無効化していないか（KABUSYS_DISABLE_AUTO_ENV_LOAD）を確認してください。
- DuckDB にテーブルが無い / ETL が失敗する場合:
  - init_schema() を呼んでテーブルを初期化してから ETL を実行してください。
- J-Quants 認証エラー:
  - JQUANTS_REFRESH_TOKEN が正しいか確認。get_id_token は失敗時に例外を返します。

---

必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、CI / デプロイ例（systemd / cron / Airflow での日次実行）などを追記できます。どの情報を追加しますか？