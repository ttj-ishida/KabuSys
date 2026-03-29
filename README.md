# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）・ニュース収集・NLP（OpenAI）によるセンチメント集約・ファクター算出・ETL・監査ログなど、バックテスト／運用のための共通ユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような用途を想定したモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別スコア化・マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）

設計上の特徴として、バックテストでのルックアヘッドバイアスを避けるために "現在時刻に依存しない" 実装方針が徹底されています。

---

## 機能一覧

主な公開機能（モジュール／代表関数）

- kabusys.config
  - settings: 環境変数から設定を取得（J-Quants リフレッシュトークン等）
  - 自動 .env / .env.local ロード（プロジェクトルート検出）。無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data
  - jquants_client: J-Quants API の取得／保存関数
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
    - get_id_token（リフレッシュ）
  - pipeline: run_daily_etl（市場カレンダー→株価→財務→品質チェック）
  - news_collector: fetch_rss（RSS 取得・前処理・記事ID生成）
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - quality: run_all_checks（欠損・重複・スパイク・日付不整合）
  - audit: init_audit_schema / init_audit_db（監査テーブル初期化）
  - stats: zscore_normalize（Zスコア正規化）

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): マクロ + MA を合成して market_regime に書き込む

- kabusys.research
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量・IC 計算等）

---

## 前提・依存関係

- Python 3.10+
  - 型アノテーションで PEP 604（A | B）を利用しているため 3.10 以上を推奨します。
- 必要パッケージ（代表例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワーク接続（J-Quants / RSS / OpenAI）

（プロジェクトに requirements.txt がある場合はそちらを利用してください。無ければ下記の例でインストールしてください）

例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# そのほか必要なパッケージがあれば追加
```

---

## 環境変数（必須 / 推奨）

主要な環境変数（README で扱う最低限）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード（運用時）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）

- 任意（デフォルトあり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite path（監視等に使用、デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env/.env.local の自動読み込みについて:
- プロジェクトルート（.git または pyproject.toml を起点）から .env を自動で読み込みます。
- .env.local は上書き（override=True）されます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .        # パッケージ化されている場合
# または必要パッケージを個別インストール
pip install duckdb openai defusedxml
```

2. 環境変数を用意（.env をプロジェクトルートに置く例）

プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD が未設定の場合）。

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

3. データベース用ディレクトリの作成（必要に応じて）

```bash
mkdir -p data
```

---

## 使い方（基本的なコード例）

以下は Python REPL / スクリプトから直接呼ぶ例です。

- DuckDB 接続を作成して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（銘柄別）を生成する（OpenAI API キーが環境変数にある場合、api_key 引数は省略可）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key=None)
print("ai_scores に書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20))  # OPENAI_API_KEY が環境変数に設定されている想定
```

- 監査ログ用 DB の初期化

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、接続が返されます
```

- calendar 更新ジョブ実行

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

注意点:
- OpenAI 呼び出しは API レート・課金が発生します。テスト時はモックを推奨します。
- ETL やデータ保存処理は冪等（ON CONFLICT DO UPDATE）を意識して実装されていますが、実際の運用前にローカルで十分に検証してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py (パッケージ公開名・バージョン)
  - config.py: 環境変数／.env ロード・設定ラッパー（settings）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースを銘柄ごとに集約して OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py: ETF(1321) の MA とマクロニュースを合成して market_regime を生成
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API との通信・保存ロジック（レート制御・リトライ・ID トークン更新）
    - pipeline.py: 日次 ETL（run_daily_etl 他）
    - etl.py: ETLResult の再エクスポート
    - news_collector.py: RSS フィード取得・前処理・記事ID生成
    - calendar_management.py: マーケットカレンダー操作・営業日判定
    - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査ログ（テーブル DDL、初期化）
  - research/
    - __init__.py
    - factor_research.py: Momentum/Value/Volatility などのファクター計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー等
  - (その他)
    - strategy/, execution/, monitoring/ は __all__ に含まれています（プロジェクト上で実装される戦略・発注・監視モジュールとの統合を想定）

---

## 注意事項 / 運用メモ

- OpenAI の呼び出しは外部 API に依存するため、テストでは _call_openai_api をモックして振る舞いを制御してください。
- J-Quants API のレート制限（120 req/min）はクライアント側で管理されていますが、運用時はさらに注意してバッチ化してください。
- ETL は部分失敗を許容し、品質チェックは結果を返すのみで処理を止めない設計です。呼び出し側でエラー／品質問題に応じた処理を行ってください。
- 監査ログは削除しない前提（トレーサビリティ確保）。スキーマ変更や後方互換性に注意してください。
- 日時は設計上 UTC で扱うことが多く、またバックテスト時にルックアヘッドが入らないように意図的に実装されています。target_date を明示的に渡す設計を心がけてください。

---

## よくある質問 (FAQ)

Q: .env が読み込まれない／テストで読み込みを抑制したい  
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

Q: OpenAI が応答しない場合は？  
A: 各 AI モジュールは API エラー時にフェイルセーフ（スコア 0 など）で続行する実装です。詳細はログを確認してください。テストでは API 呼び出しをモックしてください。

---

もし README に追加したい「実行スクリプト例」「.env.example のテンプレート」「CI/デプロイ手順」などがあれば教えてください。必要に応じて追記します。