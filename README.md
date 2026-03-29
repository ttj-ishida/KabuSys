# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
ETL（J-Quants）による市場データ収集、ニュース収集・LLMによる記事センチメント分析、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含む一連のユーティリティ群を提供します。

主な設計方針:
- ルックアヘッドバイアスを避けるため、内部で datetime.today() / date.today() を不用意に参照しない実装
- DuckDB を利用したローカルデータ格納（冪等保存・ON CONFLICT）
- 外部API呼び出しはリトライ・バックオフやレート制御を実装
- OpenAI（gpt-4o-mini）を利用したニュース/マクロ分析をサポート（JSON Mode）
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化機能を提供

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存（jquants_client, data.pipeline）
  - ETL の品質チェック（欠損、スパイク、重複、日付不整合）を実行（data.quality）
  - calendar の夜間更新ジョブ（data.calendar_management）

- ニュース収集 / NLP
  - RSS からニュースを収集して raw_news に保存（news_collector）
  - OpenAI を用いた銘柄別ニュースセンチメント算出（news_nlp.score_news）
  - マクロ + MA200 による市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（data.audit.init_audit_schema / init_audit_db）

- 設定管理
  - 環境変数 / .env の読み込み・管理（config.Settings, 自動.env読み込み機能あり）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに | を用いているため）を推奨
- DuckDB を使用
- J-Quants API トークン、OpenAI API キー、kabu API（発注）情報、Slack トークン等が必要になる機能があります

1. リポジトリをクローン
   - git clone ... （適宜）

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - 必要な主要ライブラリの例:
     - duckdb
     - openai
     - defusedxml
     - typing-extensions（古い Python の場合）
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がない場合は上記を参考に必要な依存を追加してください）

4. パッケージとしてインストール（開発モード）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（module: kabusys.config）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注を行う場合）
- KABU_API_BASE_URL: kabu API のベースURL（省略時: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- SLACK_BOT_TOKEN: Slack Bot Token（通知等）
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視や一部機能で使用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（省略時: development）
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

例（.env の内容）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意:
- config モジュールは OS 環境変数を優先し、.env → .env.local の順で読み込みます（.env.local が .env を上書き）。
- .env のパースはシェル風のコメント/クォートに対応しています。

---

## 使い方（代表的な API / スニペット）

以下は Python インタプリタやスクリプトから利用する例です。適宜 logging の設定や環境変数を準備してください。

1) DuckDB 接続と日次 ETL 実行
- ETL は jquants_client を経由してデータを取得して DuckDB に保存します。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

戻り値: ETLResult オブジェクト（取得件数・保存件数・品質チェック結果・エラーの一覧）

2) ニュースセンチメントの算出（AI）
- news_nlp.score_news は raw_news / news_symbols テーブルを前提とし、
  OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を利用して ai_scores を更新します。

例:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")

3) 市場レジーム判定
- ETF（1321）200日MA乖離 + マクロニュース（LLM）を合成して market_regime テーブルに書き込みます。

例:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAIキーは環境変数で渡す

4) 監査スキーマ初期化（発注監査用）
- 監査テーブルを DuckDB に作成します（冪等）。

例:
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマを追加:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn)

5) news_collector を用いた RSS 取得（単体）
- fetch_rss を利用して記事リストを取得可能（内部でSSRF対策・gzip制限などを実装）

例:
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])

---

## よくある操作 / 注意点

- 自動 .env 読み込み:
  - kabusys.config はプロジェクトルート（.git か pyproject.toml がある位置）を基準に .env / .env.local を自動読み込みします。
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI を使う処理:
  - news_nlp / regime_detector は gpt-4o-mini（JSON Mode）を前提にプロンプト設計されています。API 応答のパース失敗や API エラーはフェイルセーフとしてスコアに 0 を使う等の挙動をとります（例外を上げず継続する設計が多い）。

- J-Quants API:
  - rate limit（120 req/min）に合わせた固定間隔のレートリミッタを実装しています。
  - 401 時の自動トークンリフレッシュ、429/408/5xx に対する指数バックオフを実装しています。

- DuckDB executemany の注意:
  - 一部処理では DuckDB の executemany が空リストを受け付けない点を考慮してガードを入れています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py        — ニュースの LLM ベースセンチメント処理
  - regime_detector.py — マクロ＋MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（fetch/save）
  - pipeline.py        — ETL パイプラインと run_daily_etl
  - etl.py             — ETLResult の再エクスポート
  - news_collector.py  — RSS 収集（SSRF 対策・XML 安全化）
  - calendar_management.py — 市場カレンダー管理（is_trading_day等）
  - quality.py         — データ品質チェック
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - audit.py           — 監査テーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ算出
  - feature_exploration.py — 将来リターン計算・IC・summary
- research/…（他モジュール）
- その他（strategy / execution / monitoring）用プレースホルダは __all__ に含まれますが、今回のコード一覧では data / research / ai を中心に実装されています。

---

## 開発・テストに関するメモ

- モジュール内の外部 API 呼び出し（OpenAI / J-Quants / RSS fetch 等）は単体テストでモックしやすい設計（内部の _call_openai_api や _urlopen を差し替え可能）になっています。
- DuckDB を利用するため、テストは ":memory:" を渡してインメモリ DB を使うことが可能です（data.audit.init_audit_db などは ":memory:" に対応）。

---

## ライセンス / 貢献

- （ここにプロジェクトのライセンス情報や貢献ガイドラインを追加してください）

---

不明点や README に追加したい情報（具体的な実行例、CI 設定、requirements.txt の内容、サンプル .env.example など）があれば教えてください。必要に応じて README を拡張します。