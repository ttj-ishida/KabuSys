KabuSys — 日本株自動売買 / データ基盤ライブラリ
=====================================

概要
----
KabuSys は日本株向けのデータパイプライン、研究（ファクター/特徴量解析）、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ（トレース）などを包含した内部ライブラリ群です。DuckDB をデータストアに用いて、J-Quants API / RSS / OpenAI API 等と連携することで、日次 ETL → 品質チェック → 解析 → 戦略評価 までのワークフローをサポートします。

主な設計方針
- ルックアヘッドバイアスを避ける（date 引数ベースで処理）。
- DuckDB による SQL ベースの効率的な処理。
- OpenAI / J-Quants API 呼び出しに対する堅牢なリトライ・フォールバック。
- 冪等性（ETL 保存 / 監査ログ）を意識した実装。

機能一覧
--------
- データ取得 / ETL
  - J-Quants から株価（日足）・財務・上場銘柄情報・マーケットカレンダーを差分取得（jquants_client）。
  - 日次 ETL パイプライン（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを実行。
- データ品質チェック（quality）
  - 欠損・重複・スパイク（急騰・急落）・日付整合性（未来日や非営業日）検出。
- ニュース収集（news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news への冪等保存向けユーティリティ。
- ニュース NLP（news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント scoring（batch 処理・JSON mode）。
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）を合成して日次レジーム判定（bull/neutral/bear）。
- 研究（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC 計算、Z スコア正規化など。
- 監査ログ（audit）
  - signal → order_request → execution の階層的トレーサビリティ用テーブル定義・初期化（DuckDB）。
- 設定管理（config）
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート判定）。アプリ設定のラッパー（settings）。

前提（要件）
-------------
- Python 3.10 以上（型注釈: X | Y 構文、list[str] 等を使用）。
- 主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （その他: 標準ライブラリ以外の依存が追加される可能性あり）
- J-Quants API アカウント（リフレッシュトークン）
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- （オプション）kabuステーション API 情報、Slack トークンなど（監視・実運用用）

セットアップ手順
----------------
1. リポジトリをクローン / ワークディレクトリへ移動
   - 例: git clone ... && cd your-repo

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに setup.py / pyproject.toml があれば）pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
     - KABU_API_PASSWORD: kabu API パスワード（order 実装等で利用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, ...（監視用）
   - .env の書式は KEY=VALUE で、シングル／ダブルクォートやコメント（#）にも対応しています。

使い方（典型的な例）
------------------

基本的な DuckDB 接続例
- Python REPL やスクリプト内で duckdb に接続して各関数を呼びます。

例: 日次 ETL を実行する
- run_daily_etl を使うと、カレンダー → 株価 → 財務 → 品質チェックまでを実行します。

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

例: 監査 DB の初期化（order / execution 用）
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作る例
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb の接続オブジェクト
```

例: ニュースセンチメントを付与（score_news）
- raw_news / news_symbols / ai_scores テーブルがある DuckDB 接続を渡して使用します。

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 03, 20), api_key=None)  # OPENAI_API_KEY を環境で参照
print("書き込み銘柄数:", n_written)
```

例: 市場レジーム判定（score_regime）
- ETF 1321 の価格データと raw_news があることが前提です。

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 03, 20), api_key=None)  # OPENAI_API_KEY を環境で参照
```

注意点（API 呼び出し・レート制限）
- J-Quants: リクエスト制限を Respect する実装（RateLimiter）あり。認証トークンはリフレッシュされます。
- OpenAI: JSON mode を使って厳密な JSON レスポンスを期待しています。API エラー時はフォールバック（0.0）やリトライを行う設計ですが、API キーの管理・使用料に注意してください。

設定管理（.env の自動読み込み）
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して .env/.env.local を読み込みます。
- 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings オブジェクトから設定を参照できます: from kabusys.config import settings

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数 / 設定ラッパー（settings）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースセンチメント（OpenAI 経由）
    - regime_detector.py      - 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py             - ETL パイプライン（run_daily_etl など）
    - etl.py                  - ETL 結果型 ETLResult のエクスポート
    - stats.py                - 統計ユーティリティ（zscore_normalize）
    - quality.py              - データ品質チェック
    - news_collector.py       - RSS 収集 / 前処理 / 保存ユーティリティ
    - calendar_management.py  - 市場カレンダー取得 / 営業日判定
    - audit.py                - 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      - モメンタム/バリュー/ボラティリティ 等
    - feature_exploration.py  - 将来リターン / IC / 統計サマリー 等
  - ai, research, data サブモジュールが公開 API を提供

運用上の補足
-------------
- テーブル作成・スキーマ定義は各機能で想定されるテーブル（raw_prices, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, 監査用テーブル等）が必要です。ETL / init 関数を実行する前にそれらのスキーマを用意してください（プロジェクトでは schema 初期化ユーティリティが別途ある想定）。
- OpenAI / J-Quants の API 呼び出しはコストが発生します。テスト時はモック（unittest.mock.patch）を用いることを推奨します（コード中に差し替え可能な内部関数が用意されています）。

貢献 / 開発
------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化するとテストが安定します。
- OpenAI / HTTP 呼び出し部、外部 API をモックして単体テストを作成してください。

最後に
------
この README はコードの主要機能と典型的な使い方を簡潔にまとめたものです。追加のユーティリティや CLI、スキーマ初期化スクリプトなどはリポジトリの他のドキュメントを参照してください。質問や補足が必要であれば実行例や目的（ETL の自動化・バックテスト用データ整備など）を教えてください。