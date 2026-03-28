# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ ETL、ニュース NLP（LLM を利用したセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、売買戦略構築・運用に必要な共通機能を提供します。

主な設計方針
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を用いたデータ基盤（冪等保存・トランザクション）
- 外部 API 呼び出し（J-Quants / OpenAI）に対する堅牢なリトライ・レート制御
- 部分失敗に耐えるフェイルセーフ設計（API失敗時はスキップして継続する等）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数チェック（Settings クラス）

- データ取得・ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API 経由で株価（日足）、財務、JPX カレンダー等を差分取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL 結果を表す ETLResult 型
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 翌営業日・前営業日の取得 / 期間内の営業日列挙
  - JPX カレンダーの夜間差分更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、gzip サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存に適した設計

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を利用した銘柄別ニュースセンチメント算出
  - タイムウィンドウ設計、バッチ処理、レスポンスバリデーション、リトライ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と LLM マクロセンチメント（重み 30%）を合成し
    日次で market_regime テーブルへ書き込み（'bull' / 'neutral' / 'bear'）

- 研究用ファクター群（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を定義する監査テーブル初期化関数
  - order_request_id による冪等キー、UTC タイムスタンプ運用、インデックス定義

---

## セットアップ手順

以下はローカル開発環境の一例です。実装上の依存はプロジェクトの packaging / requirements に合わせて調整してください。

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（例）

   pip install duckdb openai defusedxml

（実際の requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime にも引数で渡せます）

   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 自動 .env 読み込みの無効化（テスト時など）
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config モジュールによる自動ロードを無効化できます。

---

## 使い方（主要 API の例）

下記は最小限の使用例です。実際は logging 設定やエラーハンドリング、接続のライフサイクル管理を適切に実装してください。

- DuckDB 接続を作成して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を日次実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
# OpenAI API キーを関数引数で渡すことも可能:
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブル群が作成され、UTC タイムゾーンが設定されます
```

- RSS 取得の例（news_collector）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url=url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- OpenAI / J-Quants の API 呼び出しは課金やレート制限の対象です。API キーの管理と呼び出し頻度には注意してください。
- score_news / score_regime は OpenAI の JSON Mode を利用するため、実行時に OPENAI_API_KEY が必要です（関数引数で上書き可）。
- ETL / DB 書き込みは冪等設計ですが、事前にスキーマ（テーブル群）を用意しておく必要があります（data.schema モジュール等がある場合にはそれに従ってください）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールと役割は以下の通りです。

- src/kabusys/
  - __init__.py — パッケージ初期化、公開サブパッケージ列挙
  - config.py — 環境変数 / .env 読み込み・Settings 定義
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（センチメント計算・OpenAI 連携）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - quality.py — データ品質チェック群
    - calendar_management.py — マーケットカレンダー管理 / 判定ユーティリティ
    - news_collector.py — RSS ニュース収集（SSRF 対策、正規化）
    - audit.py — 監査ログ（信号→発注→約定のテーブル定義 / 初期化）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

その他
- パッケージ内で OpenAI と J-Quants API への堅牢な呼び出し（リトライ・レート制御・トークンリフレッシュ）を実装しています。
- DuckDB を前提とした SQL ベース処理が中心です。

---

## 注意事項 / ベストプラクティス

- 本ライブラリは実際の発注ロジック（ブローカー連携）とは独立して設計されています。実際の注文送信実装では別モジュール（execution 等）を組み合わせてください。
- 本リポジトリの関数群は基本的に「DuckDB 接続」を直接受け取る設計です。接続のライフサイクルとトランザクション境界は呼び出し側で管理してください（特に init_audit_schema の transactional フラグに注意）。
- OpenAI 呼び出しは JSON Mode を利用しています。API レスポンスのバリデーションを行いますが、LLM の不定性に備えたエラー処理を呼び出し側でも考慮してください。
- .env に機密情報（API トークン等）を置く場合は、リポジトリにコミットしないよう .gitignore を設定してください。

---

以上が KabuSys の概要と基本的な使い方です。  
必要であれば README にサンプル .env.example、スキーマ作成 SQL、あるいは CLI 実行例（cron / Airflow での ETL スケジュール例）などの追加も作成できます。どの情報を追記したいか教えてください。