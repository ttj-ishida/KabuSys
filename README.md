# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュース NLP・市場レジーム判定・監査ログなどを含む研究〜運用向けのコンポーネント群です。  
バックテストや自動売買システムの基盤処理（ETL、データ品質チェック、ファクター計算、LLM を用いたニュースセンチメント評価、監査ログ構築等）を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・JPX カレンダーを差分取得して DuckDB に保存（冪等）
  - 差分／バックフィル／ページネーション対応、レートリミットとリトライ実装
- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比急変）、日付不整合（未来日付・非営業日データ）検出
- ニュース収集・NLP
  - RSS 取得＋前処理（URL 正規化／トラッキング除去／SSRF 対策）で raw_news に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄・ニュース別センチメントスコアリング（ai_scores へ保存）
  - ニュース窓（JST ベースの前日 15:00 ～ 当日 08:30）を厳密に扱う（ルックアヘッド回避）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
  - LLM 呼び出しのリトライ・フォールバック（API 失敗時は中立扱い）を実装
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）やファクター統計サマリー、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions など監査用テーブルのDDL と初期化ユーティリティ（DuckDB）
  - order_request_id を冪等キーとして二重発注防止
- 設定管理
  - .env / .env.local と OS 環境変数から設定を自動読み込み（プロジェクトルート検出、無効化可能）

---

## 必要条件（推奨）

- Python 3.10+（ソースで | 型や型注釈を利用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, typing 等）

（プロジェクト配布に requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

   git clone <リポジトリ>
   cd <リポジトリ>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では別コマンド)

3. 必要パッケージをインストール

   pip install duckdb openai defusedxml

   （requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数 / .env を準備

   プロジェクトルートに `.env`（および必要なら `.env.local`）を配置します。主なキー:

   - JQUANTS_REFRESH_TOKEN=...    # 必須（J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD=...       # 必須（kabu API パスワード）
   - OPENAI_API_KEY=...          # 必須（LLM 呼び出し時に使用）
   - KABUSYS_ENV=development|paper_trading|live  # 任意（デフォルト development）
   - LOG_LEVEL=INFO|DEBUG|...    # 任意
   - DUCKDB_PATH=data/kabusys.duckdb  # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db    # 任意（監視用）
   - PID_FILE_PATH=...           # 監視／実行用
   - KILL_FLAG_PATH=...          # 監視／実行用

   注意:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）の検出を試み、そこから `.env` を自動読み込みします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（サンプル）

以下は Python REPL やスクリプトから各機能を呼び出す例です。すべての呼び出しは DuckDB 接続（duckdb.connect() の返り値）を受け取ります。

- 設定参照

  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- DuckDB 接続作成

  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

  （テスト等では `duckdb.connect(':memory:')` ）

- 日次 ETL の実行

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコア算出（ai_scores へ書き込む）

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を参照
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定（market_regime に書き込む）

  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ用 DB 初期化

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成

- カレンダー更新ジョブを実行（単体）

  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)

- 研究用ファクター計算

  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  momentum = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))

ログレベルや環境は settings.log_level / settings.env を参照します。実行中に .env を編集した場合はプロセス再起動が必要です。

---

## 設定の自動読み込み詳細

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- プロジェクトルート判定: 現モジュール位置から親ディレクトリを探索し、.git または pyproject.toml が見つかったディレクトリをルートとする
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 環境変数バリデーション:
  - KABUSYS_ENV は development / paper_trading / live のいずれか
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか
- 必須項目に未設定があると Settings のプロパティアクセス時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）

---

## ディレクトリ構成（主要ファイル）

src/kabusys
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュース NLU（OpenAI 呼び出し、ai_scores 書込）
  - regime_detector.py     # 市場レジーム判定（ETF 1321 + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py # JPX カレンダー判定・更新ジョブ
  - etl.py                 # ETL 公開用ラッパー
  - pipeline.py            # 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py               # 共通統計ユーティリティ（zscore_normalize）
  - quality.py             # データ品質チェック（QualityIssue）
  - audit.py               # 監査ログ DDL / 初期化
  - jquants_client.py      # J-Quants API クライアント（fetch / save 関数）
  - news_collector.py      # RSS 収集・前処理・保存
- research/
  - __init__.py
  - factor_research.py     # Momentum / Value / Volatility 等の計算
  - feature_exploration.py # 将来リターン / IC / 統計サマリー等

（上記以外に strategy / execution / monitoring といったモジュールを想定した公開はありますが、ここに示したのがコードベースの主要ファイルです）

---

## 運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス回避
  - 全モジュールで datetime.today()/date.today() を直接参照しない設計（関数引数で日時を渡す）
  - ETL / スコアリングは target_date を明示して呼ぶことを推奨
- 冪等性
  - DB への保存は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE や一意な ID により冪等化
  - 発注フローでは order_request_id を冪等キーとして使用（監査ログ）
- フォールバックとフェイルセーフ
  - LLM/API の失敗時にはフォールバック（例: macro_sentiment=0.0、スコア取得失敗はスキップ）
  - 重要な例外は上位へ伝播し、ETL では各ステップ毎にエラーハンドリングして継続する設計
- セキュリティ
  - RSS 収集は SSRF 対策（リダイレクト検査、プライベート IP 拒否）
  - XML パースには defusedxml を使用

---

## 開発・テストのヒント

- 環境変数の自動ロードはプロジェクトルート判定に依存するため、テスト実行時にカレントワークディレクトリを変更しても設定が読み込まれることに注意
- LLM/OpenAI 呼び出し部分は内部で関数抽象化しているため unittest.mock.patch で置き換えてテスト可能（例: kabusys.ai.news_nlp._call_openai_api をモック）
- DuckDB を使ったユニットテストは `duckdb.connect(':memory:')` を使うと高速に行える
- ETL の外部 API 呼び出しは jquants_client._request をモックするとテストしやすい

---

## ライセンス・貢献

（ここにライセンスや貢献方法を追記してください）

---

不明点や README に追加したい内容（例: 実行スクリプト、CI 設定、具体的な .env.example）などがあれば教えてください。必要に応じて README を拡張します。