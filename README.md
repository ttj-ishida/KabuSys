# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量算出、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（注文→約定トレーサビリティ）など、アルゴリズムトレーディング実装に必要な主要機能を含みます。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
- ニュース収集・NLP
  - RSS からニュースを収集して `raw_news` / `news_symbols` に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（`score_news`）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して `market_regime` を算出（`score_regime`）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン・IC 計算・統計サマリ
- 監査（Audit）/ トレーサビリティ
  - signal_events / order_requests / executions の監査スキーマ初期化と DB 操作補助
- 環境・設定管理
  - .env / .env.local / OS 環境変数から設定読み込み。自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要条件（想定）

- Python 3.9+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

開発環境では pyproject.toml / requirements.txt を用意している前提です。パッケージをローカルにインストールする場合は以下のようにします。

例:
python -m pip install -e .

必要な依存パッケージを個別に入れる場合:
python -m pip install duckdb openai defusedxml

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL / jquants_client 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行/発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知連携を使う場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（テスト時など）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール
   - python -m pip install -e .
   - python -m pip install duckdb openai defusedxml
4. .env を作成（例を参考に）
   - 必須変数を設定する（JQUANTS_REFRESH_TOKEN など）
5. DuckDB ファイルの配置先ディレクトリを作成（必要に応じて）
   - mkdir -p data

例 .env（簡略）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API / 実行例）

下記はサンプルコードです。実行前に環境変数（特に API キー系）を正しく設定してください。

1) DuckDB 接続を開いて日次 ETL を実行する
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックの順で処理し ETLResult を返します。

2) ニュースセンチメントを算出して ai_scores に書き込む
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {count}")

- OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡してください。

3) 市場レジーム判定（market_regime テーブルへ書き込み）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB の初期化
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / signal_events / executions の操作が可能に

5) RSS フィード取得（ニュース収集）
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])

---

## 注意点 / 設計上のポリシー

- Look-ahead バイアス対策
  - 多くの関数（ETL・ニューススコア・レジーム判定・研究用計算）は内部で date.today() を不用意に参照せず、呼び出し側が対象日を明示する設計です。
- 冪等性
  - DB への保存は可能な限り ON CONFLICT（UPSERT）で実装し、再実行耐性を持たせています。
- フェイルセーフ
  - OpenAI や外部 API の失敗は致命的に停止させず、フォールバック（スコア 0 やスキップ）して処理継続する設計です（ログ出力あり）。
- セキュリティ
  - RSS 取得は SSRF 対策（ホスト検査、リダイレクト検査）、XML パースは defusedxml を使用しています。
- テスト性
  - 一部の内部 API 呼び出し（OpenAI 呼び出しやネットワーク I/O）は unittest.mock で差し替え可能なように実装されています。

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py — パッケージのエントリ（version 等）
- config.py — 環境変数 / 設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント算出（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集＆前処理
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - quality.py — データ品質チェック（各種 check_*）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（schema 作成 / init）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

テスト・ユーティリティ（存在する場合）や CLI スクリプトは別途配置されます。

---

## よくある運用フロー（例）

- 毎朝（夜間バッチ）:
  1. run_daily_etl を cron / Airflow 等で実行して DuckDB を更新
  2. news_collector で RSS を収集して raw_news に追加
  3. score_news（前日のニュース窓を対象）を実行して ai_scores を更新
  4. score_regime（前日基準）を実行して market_regime を更新
- トレード実行:
  - 戦略が生成した signal → order_requests に記録 → 約定を executions に記録（監査チェーン）

---

## トラブルシューティング

- 環境変数が見つからない:
  - settings のプロパティ（例: settings.jquants_refresh_token）は未設定時に ValueError を送出します。`.env` をプロジェクトルートに置くか OS 環境を確認してください。
  - 自動 .env 読み込みを無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認。
- OpenAI 呼び出しエラー:
  - ネットワーク/レート制限に応じて内部でリトライしますが、失敗するとスコアは 0.0 にフォールバックします。ログを確認してください。
- DuckDB への書き込みで失敗:
  - トランザクション処理（BEGIN/COMMIT/ROLLBACK）を用いています。例外発生時はログを確認し、DB ファイルの整合性をチェックしてください。

---

## 貢献 / 開発者向けメモ

- テスト時に自動 .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し等はモック差し替えが可能なように内部関数を分離しています（ユニットテストでの置き換えを推奨）。
- DB スキーマや DDL は data.audit.init_audit_schema 等で初期化できます。既存 DB へ安全にスキーマを追加する設計です。

---

README に載せてほしい追加情報や、運用で特に強調したい点があれば教えてください。READMEを用途（開発者向け/運用者向け/導入手順付き）に合わせて調整できます。