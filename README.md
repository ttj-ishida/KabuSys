# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB をデータレイヤに用い、J-Quants / RSS / OpenAI（LLM）等と連携してデータ収集（ETL）・品質チェック・特徴量算出・ニュースセンチメント評価・市場レジーム判定・監査ログ管理を行います。

---

## 概要

- ETL：J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存（冪等）。
- データ品質：欠損・スパイク・重複・日付不整合の検出。
- ニュースNLP：OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores へ保存）。
- レジーム判定：ETF（1321）の200日MA乖離とマクロニュースのLLMセンチメントを合成して市場レジーム判定。
- 研究ツール：モメンタム/バリュー/ボラティリティ等のファクター計算・将来リターン・IC計算・統計サマリー。
- 監査ログ：シグナルから約定までトレースできる監査テーブルの初期化・運用支援。
- ニュース収集：RSS フィードの取得と前処理、raw_news / news_symbols への保存支援。

想定用途：データパイプラインの夜間バッチ、戦略リサーチ、新聞記事を使ったセンチメント補助、監査可能な発注フローの記録。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・レートリミット・保存関数）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理）
  - 監査ログ（監査テーブル定義・初期化ユーティリティ）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)：ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None)：市場レジームを market_regime に保存
- research/
  - calc_momentum, calc_value, calc_volatility（ファクター算出）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・統計）
- config
  - 環境変数管理（.env 自動読み込み、必須キーチェック）
- monitoring / execution / strategy モジュール群（README のコードベース参照）

---

## セットアップ

前提
- Python 3.10+（PEP 604 の | 型注釈等を利用）
- インターネット接続（J-Quants / OpenAI / RSS）

推奨手順（プロジェクトルートで実行）:

1. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 必要パッケージをインストール（例）
   - 必要なパッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際の requirements はプロジェクトの packaging に合わせて用意してください。

3. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注周りで利用想定）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（監視/通知モジュール用）
- SLACK_CHANNEL_ID       : Slack チャンネルID

任意 / 推奨
- OPENAI_API_KEY         : OpenAI 呼び出しに利用（ai.score_news / regime_detector が参照）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG / INFO / ...（デフォルト INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）

.env 例（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL からの基本的な利用例です。

- DuckDB 接続を作って ETL を実行（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY または引数で渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- 研究向けファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
```

- RSS の取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url=url, source=source)
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- AI（OpenAI）呼び出しには API キーが必要です（OPENAI_API_KEY）。
- DuckDB 内のスキーマはプロジェクトのスキーマ初期化コード（別モジュール）を用いて作成してください（audit.init_audit_schema など）。
- ETL / API 呼び出しはネットワーク依存・API レート制限に従います。id_token / rate limiting の動作は jquants_client に組み込まれています。

---

## 設定と自動 .env 読み込みについて

- config.Settings は実行時に環境変数を参照します。
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。読み込み順は:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（上書きはしない）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソース配置（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート module)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*.py (factor/feature utilities)

各サブパッケージの役割
- ai/: OpenAI を使った NLP / レジーム判定処理
- data/: データ取得・保存・品質チェック・カレンダー管理・ニュース収集
- research/: ファクター計算と統計解析用ユーティリティ
- config.py: 環境変数のロード・必須チェック（Settings）

---

## 注意事項 / 運用上のヒント

- OpenAI・J-Quants の呼び出しはそれぞれレート制御とリトライを実装していますが、実運用時はキー管理・コスト管理を必ず行ってください。
- ETL の差分取得はバックフィル日数を用いることで API の後出し修正に対応します（デフォルト backfill_days=3）。
- news_collector は SSRF 対策、レスポンスサイズ制限、XML パースの安全対策を組み込んでいますが、外部フィードを長期運用する際は監視を行ってください。
- DuckDB のスキーマ（テーブル作成）は別の schema 初期化モジュール等で管理してください（audit.init_audit_schema は監査スキーマのみ作成します）。

---

## ライセンス / 貢献

本 README はコードベースの要約です。実際のライセンスはリポジトリの LICENSE ファイルを参照してください。  
バグ報告・改善提案は Issue を作成してください。

--- 

この README はコード内のドキュメント文字列と実装に基づいて作成しています。細かい利用方法や追加の CLI / スクリプトが存在する場合は、プロジェクト内の他のドキュメントやスクリプトを参照してください。