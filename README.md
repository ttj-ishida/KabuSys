# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ構築などの機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部処理で datetime.today() を直接参照しない設計）
- DuckDB をデータ格納に利用（ETL・分析はローカル DB 接続で完結）
- OpenAI を使ったニュース NLP はフェイルセーフ（API 失敗時はスコア 0 にフォールバック）
- 冪等性を重視（ETL/保存は upsert / ON CONFLICT を利用）
- セキュリティ考慮（ニュース収集での SSRF 対策等）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価（daily quotes）、財務データ、JPX カレンダーを差分取得し DuckDB に保存
  - 差分/バックフィルロジック、ページネーション、トークンリフレッシュ、レート制御、リトライ実装
- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比異常）、日付整合性チェック
  - QualityIssue のリストで検出内容を返却
- ニュース収集
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 防止、raw_news / news_symbols への保存（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - JSON Mode を活用した安全なレスポンスパース、リトライ/バックオフ実装
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB データベース初期化（UTC タイムスタンプ固定）
- ユーティリティ
  - 日付（営業日）判定、次/前営業日の算出、カレンダーの夜間更新ジョブ

---

## 必要環境 / 推奨依存

- Python 3.10 以上（型注釈に union 演算子（|）等を使用）
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリを多数使用（urllib, json, datetime, logging 等）

インストール例（仮想環境推奨）:
- venv 作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb openai defusedxml

（プロジェクト化されている場合は pip install -e . でインストール可能な想定）

---

## 環境変数 / 設定 (.env)

kabusys/config.py が自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（優先順位: OS 環境変数 > .env.local > .env）。  
自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- OPENAI_API_KEY（score_news / score_regime で使用）
- KABU_API_PASSWORD（kabuステーション API 用）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（monitoring 用、デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, memory/disk 閾値
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

簡単な .env の例:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb

注意: Settings の必須変数が未設定だとアクセス時に ValueError が発生します。

---

## セットアップ手順（ローカルでの最小手順）

1. リポジトリをクローン
   - git clone <repo_url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他の依存を追加）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB の格納先ディレクトリを作成（例: data/）
   - mkdir -p data
6. 監査 DB の初期化（任意）
   - python で以下を実行:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な API とサンプル）

以下は最小限の利用例。実際はログ設定や例外処理を追加してください。

- DuckDB 接続準備:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl は kabusys.data.pipeline に定義）:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコアリング（score_news）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OpenAI API キーは環境変数 OPENAI_API_KEY または引数 api_key で指定
  scored_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {scored_count} symbols")

- 市場レジームを判定（score_regime）:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーを環境変数で提供

- 監査ログ用 DB 初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- カレンダー夜間更新ジョブ:
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)

注意点
- score_news / score_regime は OpenAI API を呼び出すため API キーが必要です。
- run_daily_etl は J-Quants API を呼ぶため JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token を通じて取得）。
- それぞれの処理は DB に特定のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, etc.）を期待します。ETL 実行でこれらが作成・更新される設計になっています。

---

## ディレクトリ構成（主要ファイルと簡単説明）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス（.env 自動読み込み、自動保護）
- ai/
  - __init__.py
  - news_nlp.py        — ニュースのセンチメントスコア生成（score_news）
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL の公開型（ETLResult）
  - calendar_management.py— 市場カレンダー管理（is_trading_day, next_trading_day など）
  - news_collector.py     — RSS ニュース収集（SSRF 対策・前処理）
  - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログテーブル定義 / 初期化（init_audit_db）
- research/
  - __init__.py
  - factor_research.py    — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py— 将来リターン、IC、統計サマリー等
- research.* re-export ユーティリティ（zscore_normalize など）

補足
- 多くのモジュールは duckdb.DuckDBPyConnection を引数に取り、DB を直接操作します。
- OpenAI 呼び出しは openai.OpenAI クライアントを使用（response_format に JSON mode を使う実装）。

---

## トラブルシューティング / 注意事項

- 環境変数未設定時:
  - settings.jquants_refresh_token のような必須キーにアクセスすると ValueError が発生します。`.env.example` を参照して .env を準備してください。
- OpenAI のレスポンスパース失敗や APIエラーはライブラリ側で警告ログにフォールバックする設計ですが、呼び出し側でもログや再試行を設けてください。
- DuckDB バージョンによる executemany の振る舞い差異に対応する実装があります（空リストの扱い等）。使用する duckdb バージョンでの挙動確認を推奨します。
- ニュース収集時のネットワーク / RSS のフォーマット差異により記事が取得できない場合があります。news_collector は堅牢化のため多くの防御を入れていますが、運用監視を行ってください。

---

この README はコードベースの実装に基づいて作成しました。詳細な API（引数・戻り値）の挙動は各モジュール内の docstring を参照してください。必要であれば利用例や運用手順、CI / schema 初期化スクリプトなどの追加ドキュメントを作成します。