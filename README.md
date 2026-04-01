# KabuSys

KabuSys は日本株データ基盤と自動売買のためのライブラリ群です。  
DuckDB をデータレイク／監査データベースとして利用し、J-Quants からのデータ取得、ニュース収集・NLP、ファクター計算、ETL パイプライン、監査ログなどを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「ETL の冪等性」「ネットワーク/API 呼び出しの堅牢化（リトライ・レート制限）」「テスト可能性」です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成

---

プロジェクト概要
- 日本株向けデータ取得・前処理・解析・監査・簡易的な市場レジーム判定やニュース NLP を行う内部ライブラリ群。
- ETL（J-Quants からの株価・財務・カレンダー）を差分取得で実行し、DuckDB に保存。
- ニュースを収集して OpenAI（gpt-4o-mini）等で銘柄ごとのセンチメント（ai_scores）を算出。
- ファクター計算、特徴量探索（IC / forward returns 等）、監査テーブル（signal → order_request → execution のトレース）を備える。
- 環境変数管理は .env（自動読み込み）をサポートし、設定は kabusys.config.settings から取得可能。

---

機能一覧
- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルートを .git または pyproject.toml で検出）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（market calendar / daily prices / financial statements）の差分取得・保存
  - 保存は冪等（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - token refresh / レート制御 / リトライ / ページネーション対応
  - daily_quotes / financial_statements / market_calendar 等の取得と DuckDB への保存関数
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・ID 正規化・SSRF 対策・限界バイト数チェック
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出と ai_scores テーブルへの登録
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・エラー処理あり、失敗時はフェイルセーフにフォールバック
- 研究用ツール（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）、Z-score 正規化、ファクターサマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を作成・初期化可能

---

セットアップ手順（開発環境向け）
前提:
- Python 3.10+（typing の | union 表記を利用）
- DuckDB を使用（ライブラリ duckdb）
- OpenAI API を利用する場合は openai ライブラリ
- RSS パース等で defusedxml を使用

例: 仮想環境の作成と依存パッケージ（最低限）のインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクト固有の追加依存（slack SDK 等）がある場合はそれらもインストールしてください。

3. 編集中のソースをインストール（オプション）
   - pip install -e .

環境変数（最低限）
プロジェクトは以下の環境変数を参照します（kabusys.config.Settings）。
必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注等を行う場合）
- SLACK_BOT_TOKEN : Slack 通知を使う場合
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID

任意（デフォルト有り）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/... )

OpenAI:
- OPENAI_API_KEY は ai.score_news / regime_detector の引数で渡さない場合に利用されます（関数呼び出しで上書き可）。

例: .env（プロジェクトルートに配置）
（.env.example を作成する際の参考）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

自動ロードの制御:
- デフォルトでパッケージ import 時にプロジェクトルート（.git または pyproject.toml を基点）から .env/.env.local を読み込みます。
- テストや特殊な状況で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

使い方（主要 API 例）

1) DuckDB 接続を作って ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) 個別 ETL（株価・財務・カレンダー）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

3) ニューススコアリング（OpenAI API キーは環境変数または引数で渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None = env OPENAI_API_KEY
print(f"written {n_written} ai_scores")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

5) 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

mom = calc_momentum(conn, target_date=date(2026,3,20))
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- OpenAI / J-Quants など外部 API 呼び出しはレート制限・課金が発生するため適切なキー管理と使用量の監視を行ってください。
- News/NLP モジュールはレスポンスの JSON パース失敗や API エラーをフェイルセーフに扱い、失敗時は該当銘柄をスキップします（システムを止めない設計）。
- 各処理はルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を直接用いない等の配慮があります。バックテスト用途では過去データを正しく用意してから利用してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL 型の公開再エクスポート（ETLResult）
    - stats.py               -- 共通統計ユーティリティ（zscore_normalize）
    - quality.py             -- データ品質チェック
    - news_collector.py      -- RSS 収集（fetch_rss 等）
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - audit.py               -- 監査ログ定義と初期化
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- forward returns / IC / summary / rank
  - ai/、research/、data/ に属する多くの補助関数と設計ドキュメントは各モジュールの docstring にまとまっています。

---

サポート・貢献
- 追加機能やバグ修正は Pull Request を歓迎します。大きな設計変更を行う場合は Issue で事前相談してください。
- 外部 API キーや秘密情報はリポジトリにコミットしないでください。必ず .env や環境変数で管理してください。

---

ライセンス
- 本 README に記載のコードベースにはライセンスファイルが同梱されているはずです。配布・利用時はそちらを確認してください。

---

補足
- README はこのリポジトリの一部機能を要約したものです。各モジュールの docstring に詳細な設計方針・例外処理・戻り値仕様が記載されていますので、実装や運用時にはそちらも参照してください。