# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ ETL・品質チェック・ニュース NLU・市場レジーム判定・監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集と銘柄別ニュース集約
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄毎、マクロ）
- ETF ベースの移動平均とマクロセンチメントを組み合わせた市場レジーム判定
- 監査ログ（signal / order_request / executions）スキーマ初期化とトレーサビリティ
- 研究用ユーティリティ（ファクター算出、将来リターン、IC 計算、正規化 等）

設計上の特徴：
- ルックアヘッドバイアスに配慮した日付処理（datetime.today() に依存しない）
- DuckDB を中心としたローカルデータベース設計
- API 呼び出しはリトライ・バックオフ・レート制御を備える
- ニュース収集で SSRF / XML bomb 対策（URL 検証・defusedxml 等）
- ETL / 保存は冪等に設計（ON CONFLICT / DELETE→INSERT 等）

---

## 機能一覧（抜粋）

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数・自動トークン管理・レートリミット）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（fetch_rss / preprocess_text / URL 正規化 / SSRF 対策）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - マクロ＋MA を使った市場レジーム判定（score_regime）
  - OpenAI 呼び出しは gpt-4o-mini, JSON mode を利用
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・設定（自動 .env ロード、必須変数チェック）
  - Settings オブジェクト経由で値取得（settings.jquants_refresh_token 等）

---

## セットアップ手順

前提
- Python 3.10+（typing の union 型表記や match を使う場合は環境に合わせてください）
- DuckDB、OpenAI SDK、defusedxml 等の依存をインストールする必要があります。

例：ローカルで編集・開発する場合
1. リポジトリをクローンして package のセットアップ（開発モード推奨）:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"   # または requirements.txt に応じて pip install -r requirements.txt
   ```
   必要な主なパッケージ（例）:
   - duckdb
   - openai
   - defusedxml

2. 環境変数を設定（.env をプロジェクトルートに置くか OS 環境にセット）
   必須（アプリの機能によっては不要なものもありますが、少なくともETL/AI/Slack周りは以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知等に使用）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意 / デフォルトあり:
   - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）

   自動 .env 読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env と .env.local を自動的に読み込みます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. DuckDB 用ディレクトリを作成:
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から利用する基本例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

1) 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

2) DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

3) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュースセンチメントスコア（OpenAI API キー必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

5) 市場レジーム判定（ETF 1321 に基づく）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

6) 監査ログスキーマ初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn にスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

7) データ品質チェック（ETL 後）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- AI 機能（score_news / score_regime）は OpenAI API 呼出しを行います。環境に OPENAI_API_KEY を設定してください。関数は api_key 引数でもキーを受け取れます。
- J-Quants API 利用部分は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## ディレクトリ構成（主要ファイル）

概略ツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント（銘柄別）
    - regime_detector.py           # マクロ＋MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch/save 等）
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - etl.py                       # ETL 結果型 ETLResult を再エクスポート
    - calendar_management.py       # 市場カレンダー管理（営業日判定等）
    - news_collector.py            # RSS ニュース収集・保存ロジック
    - quality.py                   # データ品質チェック
    - stats.py                     # zscore_normalize 等ユーティリティ
    - audit.py                     # 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py           # ファクター算出（momentum / value / volatility）
    - feature_exploration.py       # forward returns / IC / summary / rank
  - researchパッケージは研究用途のユーティリティを提供します

---

## 環境変数一覧（主要）

必須（使う機能に依存）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

省略可能 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) - default: development
- LOG_LEVEL (DEBUG|INFO|...) - default: INFO
- OPENAI_API_KEY (AI 機能用)

自動 .env の読み込み:
- パッケージはプロジェクトルートにある .env, .env.local をデフォルトで読み込みます。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 動作上の注意 / 設計上のポイント

- ETL / AI / API 呼び出しは外部サービスに依存します。テスト時は各種内部関数（OpenAI 呼び出し・ネットワーク IO 等）をモックしてください（コード内に差し替えを想定した箇所があります）。
- jquants_client は 120 req/min のレート制限を守るよう実装されていますが、運用中の追加レート管理や分散環境での調整は必要です。
- ニュース収集は SSRF 対策や応答サイズ制限を実装していますが、実運用で追加のフィード制御が必要な場合があります。
- DuckDB のバージョンによっては executemany の挙動差異があるため、空リストバインドなどに注意（コード内でチェック済み）。
- 監査スキーマは削除を想定していません（トレーサビリティ保持）。DB のバックアップ運用を推奨します。

---

## 開発 / テスト

- OpenAI 呼び出しや HTTP 周りはユニットテストでモックしやすいよう、内部呼び出し関数（例: _call_openai_api, _urlopen 等）を差し替えられる実装になっています。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うとテスト環境で .env の自動ロードを無効化できます。

---

この README はコードベース（src/kabusys）に基づく概要ドキュメントです。詳細な API 仕様・運用手順・デプロイ手順は別途ドキュメント（Design/Operation.md 等）を参照してください。