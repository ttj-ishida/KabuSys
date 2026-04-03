KabuSys
=======

日本株向けのデータ基盤・AI支援・リサーチ・監査を備えた自動売買／研究プラットフォームのコアライブラリです。  
本リポジトリは以下の主要コンポーネントを含み、DuckDB をデータレイクとして利用しつつ J-Quants / OpenAI / RSS 等と連携する設計になっています。

主な特徴
--------
- データETL（J-Quants からの日次株価・財務・マーケットカレンダー取得）
  - 差分取得、バックフィル、冪等保存（ON CONFLICT DO UPDATE）
  - レートリミット・リトライ・401 リフレッシュ対応
- ニュース収集（RSS）と前処理
  - URL 正規化・SSRF 防止・サイズ制限・XML セキュリティ対策
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア）
  - バッチ処理、JSON Mode、リトライ・エラーフォールバック
- 市場レジーム判定（ETF + マクロニュースを組み合わせたスコア）
  - MA200 と LLM センチメントの重み合成（ルックアヘッド対策あり）
- リサーチ（ファクター計算・将来リターン・IC・統計サマリー）
  - DuckDB 上で完結する純粋な計算ロジック
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
  - 監査テーブルの初期化ユーティリティを提供

設計上のポイント
- ルックアヘッドバイアス対策：target_date を明示的に渡す実装。datetime.today()/date.today() を内部処理で直接参照しない箇所が多い
- 冪等性：DB 書き込みは可能な限り ON CONFLICT / DELETE→INSERT などで冪等化
- フェイルセーフ：外部 API 失敗時は部分的にスキップ or デフォルト値で継続（致命的例外以外）
- セキュリティ：RSS の SSRF 対策、defusedxml の使用、受信サイズ制限など

セットアップ
----------

前提
- Python 3.10 以上（PEP 604 の | 型といった構文を使用）
- DuckDB（Python パッケージ）、openai、defusedxml 等のライブラリ

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（プロジェクトに requirements.txt がない場合は最低限）
   - pip install duckdb openai defusedxml

3. 環境変数
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（読み込み順は OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（最低限）環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token   # J-Quants API 用（必須）
- KABU_API_PASSWORD=your_kabu_station_password       # kabuステーション API パスワード（必須）
- OPENAI_API_KEY=sk-...                               # OpenAI を使う場合は必須

任意 / デフォルト
- KABUSYS_ENV=development | paper_trading | live (default: development)
- LOG_LEVEL=INFO (default)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH=data/kabusys.duckdb (default)
- SQLITE_PATH=data/monitoring.db (default)
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0 or 1
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

使い方（主要ユースケース）
------------------------

以下はライブラリを直接使う最小例です。実運用ではログ設定や例外処理を適宜追加してください。

1) DuckDB 接続（デフォルトファイルパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（prices, financials, calendar を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

4) 市場レジームの判定（ETF 1321 の MA200 とマクロ記事を組合せ）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ（テーブル）を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイルパスは :memory: も可。親ディレクトリがなければ自動作成される
audit_conn = init_audit_db("data/audit.duckdb")
```

6) リサーチ系ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
values = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

主な API / 関数一覧（抜粋）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
- kabusys.data.news_collector.fetch_rss / preprocess_text
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.quality.run_all_checks
- kabusys.data.audit.init_audit_schema / init_audit_db

ディレクトリ構成
----------------

リポジトリ内の主要ファイル・モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                             # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                          # ニュース NLP / OpenAI バッチ処理
    - regime_detector.py                   # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                    # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                          # ETL パイプライン・run_daily_etl 等
    - etl.py                               # ETLResult の公開
    - news_collector.py                     # RSS -> raw_news の収集ロジック
    - calendar_management.py               # 市場カレンダー管理 / 営業日判定
    - stats.py                             # 統計ユーティリティ（zscore_normalize 等）
    - quality.py                           # データ品質チェック
    - audit.py                             # 監査ログ（テーブル定義と初期化）
  - research/
    - __init__.py
    - factor_research.py                   # Momentum / Value / Volatility ファクター
    - feature_exploration.py               # forward_returns / IC / summary / rank
  - ai/
  - research/
  - その他ユーティリティ群…

補足 / 運用メモ
---------------
- 環境変数の自動ロードは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env/.env.local を読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を使用しています。API レスポンスのパースに堅牢性（JSON 抽出・クリップ等）を組み込んでいます。
- J-Quants クライアントは 120 req/min の制限を固定間隔スロットリングで守ります。大量のデータ取得はページネーションとトークンキャッシュで実装。
- NewsCollector は RSS の SSRF 対策（リダイレクト先検査、プライベート IP 検出）を行います。
- DuckDB のバージョン差異（executemany の空リスト等）に配慮した実装が多数あります。実運用時は使用する DuckDB のバージョン互換性を確認してください。

貢献 / 開発
------------
- コードはモジュール毎に分離されており、ユニットテスト時には外部 API 呼び出し関数（例: news_collector._urlopen、jquants_client._request、ai._call_openai_api 等）をモックしてテストすることを想定しています。
- 新しい ETL ジョブや品質チェックを追加する場合は、既存の ETLResult / QualityIssue 型を拡張して互換性を保つことを推奨します。

ライセンス
---------
（このリポジトリ上にライセンスファイルがない場合はプロジェクトポリシーに従って追加してください）

---

README の内容はコードベースの実装に基づいて作成しています。より詳細な使い方（例: SQL スキーマ定義、フルワークフロー、CI 設定）が必要であれば、必要箇所を指定してください。