# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（発注/約定トレース）などを含むモジュール群を提供します。

---

## 特徴（概要）
- J-Quants API による差分 ETL（株価 / 財務 / マーケットカレンダー）と品質チェック
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別 ai_score）とマクロセンチメントの評価
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量解析ツール（IC, forward returns 等）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ（DuckDB）
- Look-ahead バイアス対策、冪等保存、フェイルセーフ設計

設計方針は README 内の各モジュール docstring に記載のとおり、バックテスト用にルックアヘッドを避ける実装や、API 呼び出しの堅牢性を重視しています。

---

## 機能一覧（主な公開 API）
- ETL / データ管理
  - run_daily_etl(...) : 日次 ETL（calendar / prices / financials）を実行し品質チェックを行う
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL ジョブ
  - jquants_client.fetch_* / save_* : J-Quants からの取得と DuckDB への保存
  - data.news_collector.fetch_rss(...) : RSS 取得・前処理
  - data.calendar_management.* : 営業日判定 / next/prev_trading_day / calendar_update_job など
- NLP / AI
  - ai.news_nlp.score_news(conn, target_date, api_key=None) : 銘柄別ニューススコアを ai_scores テーブルへ書き込む
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) : 市場レジーム（bull/neutral/bear）判定と market_regime への保存
- 研究（Research）
  - research.factor_research.calc_momentum / calc_value / calc_volatility
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査ログ（Audit）
  - data.audit.init_audit_schema(conn, transactional=False)
  - data.audit.init_audit_db(db_path) : 監査用 DuckDB の初期化と接続返却
- 設定管理
  - config.settings : 環境変数経由の設定取得（自動で .env / .env.local を読み込み）

---

## 必要要件（主な依存）
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装されている箇所も多いです）

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布用に setup/pyproject があれば `pip install -e .` を使用
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・依存のインストール（上記参照）

3. 環境変数 / .env の準備  
   プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（ただし tests 等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主要な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4.（オプション）データディレクトリの作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（コード例）

以下はライブラリをインポートして使う最小例です。DuckDB 接続を作成して各 API を呼びます。

- 日次 ETL の実行（例）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores テーブルへ書き込み
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

- 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI 呼び出しはコストがかかるため、テスト時は環境変数の注入や API 呼び出し部分をモックしてください（モジュール内での _call_openai_api を unittest.mock.patch で差し替え可能）。
- run_daily_etl 等はログ出力や DuckDB の既存データに依存します。初回は最小データから実行してください。

---

## 環境変数の自動読み込み
- パッケージロード時に自動でプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し `.env` / `.env.local` を読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途向け）。

---

## 設計上の注意点（要点）
- ルックアヘッドバイアス回避: 多くの関数で date.today() / datetime.today() を直接参照しない設計。必ず target_date を与えて利用してください。
- 冪等性: DuckDB 保存関数は ON CONFLICT / INSERT ... DO UPDATE等で重複書き換えを行い、再実行可能にしています。
- フェイルセーフ: OpenAI や外部 API の失敗時はデフォルト値やスキップで継続するよう実装されています（ログに警告を出します）。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査・プライベートホスト拒否）、defusedxml を利用した XML パース等の防御を実装しています。

---

## ディレクトリ構成（主なファイル）
（パッケージルート: src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数・設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py        : 銘柄別ニュースセンチメント算出（score_news）
  - regime_detector.py : マクロ＋ETF MA200 から市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント + 保存処理
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - etl.py                 : ETL 用の再エクスポート（ETLResult）
  - news_collector.py      : RSS 取得・前処理
  - calendar_management.py : マーケットカレンダー、営業日ユーティリティ、calendar_update_job
  - quality.py             : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py               : zscore_normalize 等汎用統計
  - audit.py               : 監査ログスキーマ定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py     : Momentum/Value/Volatility 等のファクター算出
  - feature_exploration.py : forward returns / IC / summary / rank
- monitoring, strategy, execution, など（パッケージ __all__ に含める想定のサブパッケージが参照されますが、このコードベースでの主要実装は上記）

---

## よくある操作例 / トラブルシューティング
- OpenAI エラーでスコアリングが進まない：
  - OPENAI_API_KEY が設定されているか確認。テスト時は _call_openai_api をモックしてください。
- J-Quants の認証エラー：
  - JQUANTS_REFRESH_TOKEN を .env に設定し、jquants_client.get_id_token() が正常に動くか確認。
- DuckDB にテーブルがない / スキーマエラー：
  - ETL 実行前にスキーマ初期化処理（別途用意されている schema 初期化関数があればそれを実行）または監査テーブルの init_audit_db を確認。

---

## 開発・テスト
- テスト・開発時は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します。
- 環境変数の自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからテストを実行してください。

---

この README はコードベース内の docstring を元に要点を抜粋しています。さらに詳細な使用方法や運用手順は各モジュールの docstring を参照してください（例: ai/news_nlp.py, data/pipeline.py, data/jquants_client.py, data/news_collector.py）。