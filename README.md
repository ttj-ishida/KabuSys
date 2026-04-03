# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants） → データ品質チェック → 研究用ファクター算出 → ニュース NLP / レジーム判定 → 発注監査ログ といった機能群をコンポーネント化して提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインと研究・運用用ユーティリティを集めたパッケージです。主な用途は以下です。

- J-Quants API からの差分取得（株価日足・財務・市場カレンダー）
- DuckDB を利用したデータ保存・品質チェック
- ニュース記事を LLM（OpenAI）でスコアリングして銘柄ごとの AI スコアを作成
- ETF（1321）を中心とした市場レジーム判定（MA とマクロニュースの混合スコア）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）の計算
- 発注監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- ニュース収集（RSS）と安全対策（SSRF 等）

設計上の特徴:
- ルックアヘッドバイアス対策（target_date ベースで日付を扱う）
- DuckDB を永続ストレージに利用（軽量・SQL ベース）
- API 呼び出しに対するリトライ・レート制御を組み込み
- フェイルセーフ設計（API 失敗時はゼロスコア等で継続）

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- データ品質チェック
  - 欠損 / スパイク / 重複 / 日付整合性（kabusys.data.quality）
- カレンダー管理
  - 営業日判定、next/prev_trading_day、calendar_update_job（kabusys.data.calendar_management）
- ニュース収集・前処理
  - RSS 取得、安全性検査、記事正規化（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores に保存（kabusys.ai.news_nlp）
  - マクロ記事を用いた市場レジーム判定（kabusys.ai.regime_detector）
- 研究（Research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research）
- 監査ログ（Audit）
  - 監査テーブル初期化・監査 DB 作成（kabusys.data.audit）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.9+（ソースは型注釈に Python 3.10 以上向けの構文が含まれる可能性がありますので 3.10+ を推奨）
- システムに duckdb がインストール可能であること

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必須パッケージのインストール（例）
   pip install duckdb openai defusedxml

   補足（必要に応じて）:
   - requests 等を追加する場合は requirements.txt を用意して pip install -r requirements.txt

4. パッケージを編集可能モードでインストール（任意）
   pip install -e .

5. 環境変数設定
   - 開発時はプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（kabusys.config が自動ロード）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数（主要）

kabusys.config.Settings で参照される主要変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。get_id_token で ID トークンを取得します。
- KABU_API_PASSWORD (必須)
  - kabuステーションなどの証券 API パスワード（プロジェクト内の execution 関連で使用想定）。
- OPENAI_API_KEY (任意だが多くの機能で必要)
  - OpenAI の API キー。news_nlp.score_news や regime_detector.score_regime に必要。
- KABUSYS_ENV (optional)
  - "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL (optional)
  - "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- DUCKDB_PATH (optional)
  - デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (optional)
  - デフォルト "data/monitoring.db"
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視用設定

.env の例（プロジェクトルート/.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env ファイルは自動で .env → .env.local の順に読み込まれます。OS 環境変数は上書きされません（.env.local は override=True になりますが OS 環境は protected）。

---

## 使い方（主要な呼び出し例）

下記は最小の利用例です。適宜ロギング設定や例外処理を行ってください。

- DuckDB 接続の取得（例）
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（J-Quants から差分を取得して保存）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースをスコアリングして ai_scores に保存（OpenAI 必須）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込み銘柄数:", n_written)

- 市場レジームを判定して market_regime テーブルへ書き込む
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 研究用ファクター計算（例: モメンタム）
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]

- 監査ログスキーマ初期化（監査専用 DB の作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn により signal_events / order_requests / executions テーブルが作成される

---

## 注意点 / 設計ポリシー

- Look-ahead bias を避けるため、内部ロジックは target_date パラメータを基準に処理を行います（datetime.today() を直接参照しない）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーションとリトライを実装しています。API 失敗時はフェイルセーフ（0.0）で継続することが多いです。
- J-Quants API 呼び出しは固定間隔レート制御と再試行・トークン自動リフレッシュを備えています。
- DuckDB の executemany は空リストを受け付けないバージョン差を考慮して保護されています。
- ニュース収集は SSRF 対策・XML ハードニングを行っています（defusedxml、URL 検査）。
- 監査ログは削除せずトレーサビリティを残す設計です（FK は ON DELETE RESTRICT）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメントの LLM スコアリング
  - regime_detector.py     # 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント + DuckDB 保存
  - pipeline.py            # 日次 ETL パイプライン
  - etl.py                 # ETLResult の再エクスポート
  - news_collector.py      # RSS 取得・前処理・raw_news 保存
  - calendar_management.py # 市場カレンダー管理・営業日判定
  - quality.py             # 品質チェックモジュール
  - stats.py               # 共通統計ユーティリティ（zscore 等）
  - audit.py               # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py     # Momentum / Value / Volatility ファクター
  - feature_exploration.py # 将来リターン・IC・統計サマリー等
- ai/, data/, research/ は公開 API を __all__ 等で整理しています。

---

## ログと監視

- 設定は環境変数 `LOG_LEVEL` で制御（DEFAULT: INFO）。
- 実行中の監視や PID / kill flag のサポート変数が設定可能（PID_FILE_PATH / KILL_FLAG_PATH 等）。

---

## ライセンス・責任範囲

この README はコードベースの説明です。実際の運用用途で使用する際は API 使用ポリシー、取引リスク、秘密情報（APIキー）の扱い、及び法的要件に十分注意して下さい。実取引を自動化する場合は十分な検証・監査を行ってください。

---

README に記載の使い方はライブラリの公開 API を例示したものです。詳細なパラメータや返り値の仕様は各モジュール（kabusys/data/*.py, kabusys/ai/*.py, kabusys/research/*.py）内の docstring を参照してください。