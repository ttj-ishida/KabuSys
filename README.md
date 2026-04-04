# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の価格・財務・カレンダー収集）、ニュース収集・NLP スコアリング（OpenAI）、研究用ファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

## プロジェクト概要
- DuckDB をバックエンドにした時系列データ管理と ETL パイプライン
- J-Quants API 経由での株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS ニュース収集と OpenAI を用いた銘柄別／マクロセンチメント評価（gpt-4o-mini 想定）
- 研究用途のファクター計算・特徴量探索ユーティリティ（外部ライブラリに依存しない実装）
- 監査ログ（signal → order_request → execution の完全トレーサビリティ）用スキーマ初期化機能
- 各種データ品質チェック（欠損・重複・スパイク・日付不整合）

## 主な機能一覧
- 環境変数・.env 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - レートリミット・リトライ・ID トークン自動刷新
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による実行結果の集約と品質チェック統合
- ニュース収集
  - RSS フィードの正規化・SSRF 対策・記事ID生成（SHA-256）
  - raw_news / news_symbols への冪等保存ロジック（トランザクション）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - calc_news_window: ニュース収集ウィンドウ（JST ベース）を計算
  - レート制御／エクスポネンシャルバックオフ／レスポンスバリデーション
- 市場レジーム判定
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- 研究モジュール
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（audit）
  - init_audit_schema / init_audit_db：発注トレーサビリティ用テーブルの初期化

---

## 要求環境・依存
- Python >= 3.10（型注釈に `X | Y` を使用）
- 主要パッケージ
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging, hashlib など

（プロジェクトに pyproject.toml が含まれている想定のため、Poetry / pip 環境でインストールしてください）

例（pip 仮想環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb>=0.10" openai defusedxml
# パッケージを開発モードでインストール（プロジェクトルートで）
pip install -e .
```

---

## セットアップ手順（簡易）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env（または環境変数）を用意
   - 自動ロード順序: OS 環境 > .env.local > .env
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB 用ディレクトリ（デフォルト data/）を作成しておく（任意）

サンプル .env（プロジェクトルートに配置）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション（発注利用時）
KABU_API_PASSWORD=secret_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI（news_nlp / regime_detector）
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス（必要なら変更）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトでの利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続を作る（ファイル DB）
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新バッチ（J-Quants から差分取得）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査ログ DB を初期化（監査用専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema を使う場合は既存 conn を渡して初期化可能
```

注意点:
- OpenAI を呼ぶ関数は API キー未設定時に ValueError を投げます。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL/保存系は冪等（ON CONFLICT）を意識した実装です。部分失敗時も既存データの保護を試みます。

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）
リポジトリの主要ファイル構成（src/kabusys 配下の代表）:

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数 / .env 自動ロード設定
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュース NLP スコアリング
    - regime_detector.py            : 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - quality.py                    : データ品質チェック
    - news_collector.py             : RSS ニュース収集
    - calendar_management.py        : マーケットカレンダー管理・判定ユーティリティ
    - stats.py                      : zscore_normalize 等の統計ユーティリティ
    - audit.py                      : 監査ログ（テーブル定義・初期化）
    - etl.py                        : ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py            : Momentum/Value/Volatility 計算
    - feature_exploration.py        : 将来リターン / IC / 統計サマリー
  - research/...                     : 研究用ユーティリティ群
  - (strategy/, execution/, monitoring/ はエントリポイント/将来的な拡張想定)

---

## 開発メモ / 設計上の注意
- Look-ahead bias を防ぐ設計:
  - 各スコアリング／ETL 関数は内部で datetime.today() を直接参照しない（target_date を明示的に渡す）。
  - prices_daily のクエリは date < target_date などの排他条件を使用してルックアヘッドを回避。
- OpenAI 呼び出しはリトライとバリデーションを備え、不正応答時はフォールバック値（0.0）で継続する実装。
- J-Quants API はレートリミット（120 req/min）を守るため固定間隔スロットリングを実装。
- DuckDB に対する executemany の空リストバインドなど、実運用で遭遇する実装差分に注意（コード内で考慮済み）。

---

## よくある質問
Q: OpenAI のレスポンスが JSON 以外を返すことがあるのですがどう扱いますか？  
A: news_nlp / regime_detector では JSON モードの利用と追加のパースロジック（外側の {} を抽出する等）で復元を試み、最終的にパース失敗時はスコアを返さずログ警告の上でフォールバックします。

Q: ETL を cron や CI で実行したいのですが？  
A: run_daily_etl を適切にラップしたスクリプトを作成し、システム環境変数（OPENAI_API_KEY 等）を設定した上で実行してください。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で .env 自動読み込みを無効化できます。

---

この README はコードベースの主要機能と使用方法をまとめたものです。詳細な API 仕様や DB スキーマ、運用手順（発注連携、監視、ロギング設定など）は別ドキュメント（StrategyModel.md / DataPlatform.md 等）を参照してください。必要であれば README に追加したい例や、運用手順を追記します。