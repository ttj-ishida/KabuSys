# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（部分実装）。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ等のユーティリティを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ初期化など、量的アルファ開発と運用に必要な基盤機能をまとめた Python モジュール群です。  
設計上のポイントは以下の通りです。

- DuckDB を用いたローカルデータストア中心の設計（Look-ahead バイアス対策済み）
- J-Quants API 経由の差分 ETL（レートリミット・リトライ・トークン自動更新対応）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（JSON Mode）をバッチ評価
- ニュース収集時の SSRF/サイズ/XML 脆弱性対策
- 監査ログ（シグナル -> 発注 -> 約定）の冪等・トレーサビリティ設計

注: このリポジトリは「取引執行（証券会社 API での実際の注文送信）」を含む実装の一部を含む設計を想定していますが、配布コードでは主にデータ・研究・監視系のユーティリティが実装されています。実環境でのライブ注文・資金管理を行う際は十分なレビューを行ってください。

---

## 機能一覧

主要な機能（モジュール）と代表 API:

- kabusys.config
  - 自動 .env ロード（OS 環境変数優先、.env.local が上書き）
  - settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save / id token 管理）
  - pipeline: 日次 ETL 実装（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得・正規化・保存ユーティリティ（SSRF 対策、XML 安全処理）
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - calendar_management: 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - stats: 汎用統計（zscore_normalize）
  - ETLResult 型
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースから銘柄ごと ai_score を生成して ai_scores テーブルに保存
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF(1321) の MA 乖離 + マクロニュースで市場レジームを判定して market_regime テーブルに書き込み
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 監視・システム設定
  - PID / kill flag / CPU/Mem/Disk 閾値などを environment で設定可能

---

## セットアップ手順

1. Python のバージョン確認（推奨: 3.10+）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. ソースを editable install（プロジェクトルートが .git / pyproject.toml を含むことを想定）
   - python -m pip install -U pip
   - python -m pip install -e ".[dev]"  （pyproject がある場合）
   - もし requirements が別ファイルなら:
     - python -m pip install duckdb openai defusedxml
     - 他の依存があれば追加でインストールしてください
   - 最低依存:
     - duckdb, openai, defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必要に応じて) — OpenAI API キー（news_nlp / regime_detector 実行時）
     - KABU_API_PASSWORD (kabu ステーション利用時)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite、デフォルト: data/monitoring.db）
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL（DEBUG|INFO|...）
   - 自動ロードは OS 環境変数 > .env.local > .env の優先順で行われます。
   - 自動ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成
   - 一部処理はデフォルトで data/ 配下にファイルを作成します:
     - mkdir -p data

6. DuckDB スキーマ等の初期化（監査ログ等）
   - 監査用 DB 初期化の例:
     - python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 使い方（簡単な例）

以下は基本的な使い方の抜粋例です。各関数は DuckDB 接続を受け取り、テーブル群（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を参照・更新します。

1) DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# 今日を対象に ETL 実行（settings.jquants_refresh_token が .env にあること）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI のキーを直接渡すか、環境変数 OPENAI_API_KEY を .env に設定してください
count = score_news(conn, target_date=date(2026, 3, 19), api_key=None)
print(f"書き込んだ銘柄数: {count}")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19), api_key=None)
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 必要なテーブル群が作成され、UTC タイムゾーンが設定されます
```

5) calendar_update_job を夜間ジョブで走らせる
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存したカレンダーレコード数: {saved}")
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API レスポンスが想定外の場合はフェイルセーフで一部をスキップし、0.0 等でフォールバックする設計です。
- run_daily_etl は ETL の各ステップで例外を捕捉しつつ続行するため、result.errors を確認して問題の有無を確認してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。kabusys.data.jquants_client.get_id_token() が使用します。

- OPENAI_API_KEY  
  - news_nlp / regime_detector 実行時に使用。関数に api_key を直接渡すことも可能。

- KABU_API_PASSWORD, KABU_API_BASE_URL  
  - kabu ステーション連携用（未使用・将来の執行連携向け）。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  
  - 通知用（未実装の箇所で使用想定）。

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)  
- SQLITE_PATH (デフォルト: data/monitoring.db)  
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START  
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT  
- KABUSYS_ENV (development | paper_trading | live)  
- LOG_LEVEL (DEBUG | INFO | ...)

自動 .env 読み込み:
- プロジェクトルートにある `.env` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能）。優先順位: OS 環境変数 > .env.local > .env。

---

## ディレクトリ構成

プロジェクト内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存処理
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — 市場カレンダー管理
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログ（テーブル定義 / init）
    - etl.py                       — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank

その他:
- .env / .env.local / .env.example（プロジェクトルート: 自動ロード対象）
- data/（デフォルトの DB や PID/flag を格納するディレクトリ）

---

## 補足・運用上の注意

- Look-ahead バイアス防止: モジュールの多くは実行時に date 引数で対象日を受け取り、datetime.today() を内部ロジックで直接参照しない設計になっています。バックテストに流用する際は date を明示してください。
- API キーや機密情報は .env / OS 環境変数で管理してください。`.env` をリポジトリに含めないように注意。
- OpenAI / J-Quants の呼び出しはコスト・レート制限がかかります。テスト時はモックするか小さな対象で試してください。
- DuckDB の executemany に対する注意（空パラメータは一部バージョンでエラーになる）など、コード内に互換性対策があります。DuckDB のバージョンが古い/新しい場合は挙動が異なることがあるので適宜調整してください。

---

必要であれば、README に CI / テスト実行方法やデプロイ手順、さらに詳しい API リファレンス（個別関数の引数・返り値の詳細）を追加できます。どの情報を優先して追加しますか？