# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ収集・特徴量生成・シグナル生成・監査・ETL を含むモジュール群。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に特化した自動売買システムのライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、四半期財務、JPX カレンダー）
- DuckDB を用いたデータ保存・スキーマ管理（Raw / Processed / Feature / Execution 層）
- 研究（research）で算出されたファクターの正規化・統合（feature engineering）
- 戦略シグナル生成（features と AI スコアを統合して BUY/SELL を判定）
- ニュース収集（RSS）と銘柄紐付け
- ETL パイプライン、品質チェック、カレンダー管理、監査ログ

設計上のポイント:
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点の情報のみを使用
- DuckDB への書き込みは冪等（ON CONFLICT）で設計
- ネットワーク呼び出しはレート制御/リトライ/トークンリフレッシュを備える

---

## 機能一覧

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 関数で DuckDBへ冪等保存
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
- ETL パイプライン（差分取得・保存・品質チェック）（data.pipeline.run_daily_etl）
- マーケットカレンダー管理（カレンダー更新／営業日判定）
- RSS からのニュース収集と前処理・DB保存（data.news_collector）
- ファクター計算（momentum / volatility / value）（research.factor_research）
- 特徴量生成（Zスコア正規化、ユニバースフィルタ、features テーブル更新）
- シグナル生成（final_score 計算、Bear フィルタ、BUY/SELL の出力）
- 統計ユーティリティ（zscore_normalize、IC、forward returns、統計サマリー）
- 実行／監査用テーブル群（signals, orders, executions, audit 等）

---

## セットアップ手順

前提
- Python 3.10 以上（ソースで | 型注釈を使用しているため）
- ネットワーク接続（J-Quants API、RSS 等）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. リポジトリルートに .env を作成（または環境変数で設定）
   - 自動ロードは kabusys.config により .env → .env.local を読みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL を変更する場合のみ設定
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化
   - Python コンソールやスクリプトで init_schema を実行してください（親ディレクトリを自動作成します）。

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。実運用では各処理をジョブ化してスケジューラ（cron / Airflow 等）で実行してください。

1) DB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（features と ai_scores を統合）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758", "9984"}  # 例: 有効銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) J-Quants から生データを取得して保存（個別）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 環境変数

主要な環境変数（kabusys.config.Settings から参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

未設定の必須変数があると Settings のプロパティ参照時に ValueError が発生します。

---

## 推奨ワークフロー（運用の概略）

1. 夜間に calendar_update_job（カレンダー更新）
2. 当日早朝に run_daily_etl（market calendar → prices → financials）を実行
3. feature_engineering.build_features を呼び出して features を更新
4. 必要に応じて AI スコアを ai_scores テーブルに投入
5. strategy.signal_generator.generate_signals でシグナルを作成
6. execution 層で signals をキュー化して発注（本コードベースでは execution 部分は別実装や外部連携を想定）
7. 実行・約定情報を監査テーブル（audit）に記録

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の要約）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ロジック
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義と init_schema
    - stats.py                      — zscore_normalize 等統計ユーティリティ
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - features.py                   — data.stats の再エクスポート
    - calendar_management.py        — カレンダー管理（営業日判定等）
    - audit.py                      — 監査ログ用 DDL
    - (その他: quality, monitoring など想定)
  - research/
    - __init__.py
    - factor_research.py            — momentum/volatility/value の計算
    - feature_exploration.py        — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py        — features テーブル生成（Zスコア正規化・フィルタ）
    - signal_generator.py           — final_score 計算と signals 生成
  - execution/
    - __init__.py                   — （発注実装のフック）
  - monitoring/                      — 監視系モジュール（場所だけ存在）

---

## 注意点 / 運用上の留意事項

- J-Quants の API レート制限（120 req/min）を respect する設計になっています。大量取得や並列化時は注意してください。
- DuckDB のトランザクションは各モジュールで BEGIN/COMMIT/ROLLBACK を使用して整合性を保っています。ロールバックの失敗ログなどは注意して監視してください。
- features の生成・signal の作成は target_date ベースで冪等（既存行は削除して再挿入）するため、バッチを再実行しても安全です。
- ニュース RSS の取得は SSRF 対策・レスポンスサイズ上限・gzip 解凍上限などを組み込んでいますが、未知のソースを追加する際は慎重に行ってください。
- execution（ブローカ接続）周りは別途実装が必要です。本リポジトリの execution パッケージは発注インターフェースや監査連携の受け口を想定しています。

---

## 追加情報

- テストにおいて .env の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルを :memory: にするとインメモリ DB で動作します（テスト用途に便利）。

---

問題や拡張要望があれば、利用ケース（ETL頻度・取引フロー・AI スコア投入方法など）を教えてください。README の例コードを実運用スクリプト用に調整できます。