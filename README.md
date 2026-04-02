# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買 / リサーチ基盤のコアライブラリです。J-Quants API を用いたデータ ETL、ニュース収集と NLP による銘柄センチメント評価、ETF を用いた市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注 → 約定トレーサビリティ）などを含みます。

主な設計方針
- Look‑ahead バイアスを避ける（内部で date.today() を安易に参照しない）
- DuckDB を中心にした高速なローカル DB ストレージ
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- 冪等（idempotent）な保存処理（ON CONFLICT / DELETE→INSERT など）

---

## 機能一覧（主要機能）

- データ収集 / ETL
  - J-Quants からの株価（日次 OHLCV）、財務、JPX マーケットカレンダー取得（pagination 対応・レート制御・トークン自動リフレッシュ）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出・報告
- ニュース収集
  - RSS 取得（SSRF 対策、追跡パラメータ除去、最大サイズ制限）
  - raw_news / news_symbols の冪等登録
- ニュース NLP（OpenAI）
  - 銘柄ごとの記事集約 → LLM によるセンチメント付与（ai_scores へ保存）
  - LLM 呼び出しは JSON Mode を利用し、リトライ/バリデーションを実施
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）の合成による 'bull' / 'neutral' / 'bear' 判定
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン・IC 計算・Zスコア正規化など
- 監査ログ（Audit）
  - signal_events / order_requests / executions を中心とした発注から約定までのトレーサビリティ
  - 監査スキーマ初期化ユーティリティ含む

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈に union types などを使用）
- ネットワーク接続（J-Quants / OpenAI 等）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージのインストール（参考）
   - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt があればそれを使用してください。

3. 開発インストール（ソースがプロジェクトルートにある場合）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
   - 必須項目は Settings クラスのプロパティ参照に従います。未設定の場合はエラーが発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。

---

## 使い方（基本例）

以下はライブラリ API の代表的な呼び出し例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続の作成
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL の実行（J-Quants から差分取得 → 品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

3) ニュースセンチメント（AI）スコア付与
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
- print("scored:", n_written)

4) 市場レジーム判定（AI + MA200）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, date(2026, 3, 20), api_key="sk-...")

5) 監査 DB 初期化（監査テーブルを作成）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")
- # audit_conn を用いて監査ログ操作が可能

6) リサーチ用ファクター計算の利用例
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- from datetime import date
- mom = calc_momentum(conn, date(2026,3,20))
- val = calc_value(conn, date(2026,3,20))

注意点
- OpenAI 呼び出しは API キーを必要とします（api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定）。
- ETL / ニュース収集等は外部 API 依存のため、ネットワーク・認証トークンが必須です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして自動 env 読み込みを防ぎ、モックで外部呼び出しを差し替えて行ってください。

---

## ディレクトリ構成

以下は主要ファイル / モジュールの概観（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py  (パッケージ定義, __version__ = "0.1.0")
    - config.py    (環境変数・.env 読み込み、Settings)
    - ai/
      - __init__.py
      - news_nlp.py         (ニュースの LLM スコアリング：score_news)
      - regime_detector.py  (市場レジーム判定：score_regime)
    - data/
      - __init__.py
      - calendar_management.py  (市場カレンダー管理、営業日判定)
      - etl.py                  (ETL 公開インターフェース)
      - pipeline.py             (日次 ETL パイプラインの実装)
      - stats.py                (統計ユーティリティ、zscore_normalize)
      - quality.py              (データ品質チェック)
      - audit.py                (監査ログスキーマ初期化 / init_audit_db)
      - jquants_client.py       (J-Quants API クライアント、保存関数)
      - news_collector.py       (RSS ニュース収集)
    - research/
      - __init__.py
      - factor_research.py      (Momentum / Value / Volatility)
      - feature_exploration.py  (calc_forward_returns, calc_ic, rank, summary)
    - ai/ (前述)
    - research/ (前述)

重要テーブル（DuckDB 内で想定される名前）
- raw_prices / prices_daily
- raw_financials
- market_calendar
- raw_news / news_symbols
- ai_scores
- market_regime
- signal_events / order_requests / executions (監査ログ)

---

## 実運用・開発上の注意

- 自動環境読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動読み込みします。.env.local は .env を上書きします（OS 環境変数は保護されます）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 外部 API エラー処理
  - J-Quants & OpenAI 呼び出しはリトライ・指数バックオフを備えています。LLM の結果は厳密にバリデーションされ、失敗時は安全策（ゼロスコア等）で続行します。

- テスト容易性
  - news_nlp._call_openai_api や regime_detector/_call_openai_api は内部で分離実装されています。ユニットテストではそこを patch してレスポンスを差し替えてください。

- DB マイグレーション / 初期化
  - audit.init_audit_db() のようなユーティリティで監査スキーマを初期化できますが、他のテーブルスキーマ（raw_prices, raw_financials, raw_news 等）はプロジェクトのスキーマ定義に従って事前に作成してください（本ソースは保存/読み出しの実装を含みますが、テーブル DDL は別途管理される想定です）。

---

## ライセンス / 貢献

- この README はコードベースからの抽出に基づく簡易ドキュメントです。実プロジェクトでは README にさらに詳細なセットアップ手順（依存ファイル・DB スキーマ・運用スケジューリング等）を追加してください。

---

必要であれば、以下を追加して作成できます:
- .env.example のテンプレート
- 依存関係の requirements.txt
- テーブル DDL（raw_prices 等）の初期化スクリプト
- 実行スクリプト（CLI / systemd / cron 用の例）

上記のうちどれを追加希望か教えてください。