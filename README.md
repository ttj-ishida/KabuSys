# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ兼ツール群です。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP（OpenAI）、リサーチ向けファクター計算、監査ログ管理、カレンダー管理、品質チェックなどを含む、アルゴリズムトレーディング基盤のコア機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得（J-Quants API）および DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理と営業日判定ユーティリティ
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）および市場レジーム判定
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログスキーマ（signal → order_request → executions のトレース）と初期化機能
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 必要な環境変数

最低限必要な環境変数（用途）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（監視等）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合に必要

その他（デフォルトあり）:

- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live` のいずれか（デフォルト `development`）
- LOG_LEVEL — ログレベル（`DEBUG, INFO, WARNING, ERROR, CRITICAL`。デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視ログ等）パス（デフォルト `data/monitoring.db`）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視用設定

自動で .env / .env.local をプロジェクトルートから読み込む機能があります（無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## セットアップ（開発向け）

1. リポジトリをチェックアウト（任意）
2. Python 仮想環境を作成・有効化
   - python >= 3.9 推奨
3. 依存パッケージをインストール（例）

   pip install -r requirements.txt

   必要と思われる主要パッケージ例:
   - duckdb
   - openai
   - defusedxml

   （本サンプルコードでは標準ライブラリと上記を利用しています。requirements.txt をプロジェクトに追加して管理してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を配置することで自動ロードされます。
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

例: `.env`（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要なユースケース）

前提: DuckDB 接続オブジェクトは `duckdb.connect(path)` で取得して渡します。

- DuckDB 接続の取得例:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

### ETL（日次 ETL の実行）

kabusys.data.pipeline.run_daily_etl を使って、日次の ETL（カレンダー・株価・財務・品質チェック）を実行できます。

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

戻り値は `ETLResult` オブジェクト（取得数・保存数・品質問題・エラー概要 を含む）。

### ニュースセンチメント（銘柄別）をスコアする

OpenAI API キー（環境変数または引数）が必要です。

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

内部でニュース時間窓（前日 15:00 JST 〜 当日 08:30 JST）を計算し、raw_news と news_symbols を参照して銘柄別に記事をまとめ、OpenAI にバッチ送信して `ai_scores` テーブルへ書き込みます。

### 市場レジーム判定（ETF 1321 ベース + マクロニュース）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

1321（日経225 連動 ETF）の 200 日 MA 乖離とマクロニュースのセンチメントを重み合成し、`market_regime` テーブルへ書き込みます。OpenAI API キーが必要です。

### 監査ログ（Audit）スキーマの初期化

監査用のテーブル・インデックスを DuckDB に作成します。

```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

あるいは別 DB ファイルを初期化して接続を取得する:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

### ニュース収集（RSS フェッチ）

ニュースコレクタの低レベル関数 `fetch_rss` 等を利用できます。URL のスキーム検査・SSRF 対策・最大サイズ制限などを備えています。

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

取得した記事は `raw_news` テーブルへ保存するロジック（別関数）が用意されています（ETL ワークフローに組み込むことを想定）。

---

## 設定・設計上の注意事項（重要）

- Look-ahead バイアス対策: 多くの関数（ETL・news_nlp・regime_detector 等）は `datetime.today()` や `date.today()` を参照せず、呼び出し側が `target_date` を与える設計です。バックテスト時は過去データのみを参照することに注意してください。
- OpenAI 呼び出しは再試行ロジック・JSON Mode を使った厳密なパース・フォールバックを備えています。API 失敗時はスコアを 0 にフォールバックするなどフェイルセーフを設けています。
- J-Quants API へのリクエストはレートリミッタ・リトライ・401 リフレッシュ対応を実装しています。`JQUANTS_REFRESH_TOKEN` が正しく設定されていることを確認してください。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING など）になるよう実装されています。
- ニュース収集は SSRF 対策、受信サイズ制限、トラッキングパラメータ除去などの安全対策を備えています。

---

## 主要モジュールとディレクトリ構成

以下はパッケージ内のおもなファイルと役割（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード・必須チェック・settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの銘柄別センチメント解析と `ai_scores` への保存ロジック
    - regime_detector.py
      - ETF（1321）MA乖離 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + DuckDB への保存）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl など）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・保存支援（SSRF・サイズ対策等）
    - calendar_management.py
      - 市場カレンダー管理・営業日判定（is_trading_day, next_trading_day 等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py
      - 監査ログテーブル DDL / 初期化（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム／バリュー／ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、ランク関数等

（上記は主要部分の説明です。実装ファイルごとにさらに細かなユーティリティ関数が含まれます。）

---

## 開発・運用のヒント

- 自動的に `.env` を読み込むので、CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して制御すると良いです。
- OpenAI を利用する部分は外部 API に依存するため、テスト時は `_call_openai_api` をモックする設計になっています（news_nlp / regime_detector ともに_swap 可能）。
- DuckDB をローカルファイルで使う場合はパスの親ディレクトリ作成に注意（audit.init_audit_db は親ディレクトリを自動作成します）。
- 品質チェックは ETL の一部として任意に有効化できます。ETL 実行後の `ETLResult.quality_issues` を基に運用アクションを決めてください。

---

## ライセンス・貢献

（この README にライセンス情報・貢献方法があればここに記載してください。プロジェクトに合わせて補完してください）

---

以上がこのコードベースの概要と利用方法です。具体的な使い方や追加のユーティリティについては各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば README にサンプル .env.example や requirements.txt、簡易 CLI の使い方を追記できます。どの情報を優先して追記するか指示してください。