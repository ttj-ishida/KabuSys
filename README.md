# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレース）などの機能を提供します。

---

## 概要

KabuSys は以下の機能群を組み合わせ、バックテストや本番運用で使える堅牢なデータ基盤と意思決定支援を提供することを目的としています。

- J-Quants API を用いた株価・財務・カレンダーの差分取得（レートリミット・リトライ対応）
- DuckDB を使ったローカルデータストア（ETL と冪等保存）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（銘柄別）とマクロセンチメントの評価
- 市場レジーム判定（ETF + マクロセンチメントの重み付け合成）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注から約定までトレース可能な監査ログスキーマ（監査 DB 初期化ユーティリティ）

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない等）
- 冪等性を重視（DB 保存は ON CONFLICT / DO UPDATE など）
- 外部 API 呼び出しに対する堅牢なリトライとフォールバック（LLM の失敗はゼロスコアで継続する等）
- ネットワーク安全性（RSS の SSRF 対策、レスポンスサイズ制限など）

---

## 機能一覧 (主なモジュール)

- kabusys.config
  - 環境変数 / .env 自動ロード（プロジェクトルート検出）
  - settings（J-Quants, OpenAI, Slack, DB パスなど）

- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存（fetch_*, save_*）
  - pipeline / etl: 日次 ETL 実行 run_daily_etl、個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS フィード収集・正規化・raw_news への保存ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）DDL & 初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF + マクロセンチメントで market_regime を更新

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（研究用ユーティリティ）

---

## セットアップ手順

※ 以下は一般的な手順です。実際に使用する環境や依存パッケージはプロジェクトの別ファイル（requirements.txt / pyproject.toml）を確認してください。

1. リポジトリをクローンし、開発環境へ移動
   - git clone ... && cd <repo>

2. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール（開発モード）
   - pip install -e .

   ※ 実行に必要な主要依存例:
   - duckdb
   - openai
   - defusedxml
   - その他（標準ライブラリのみで実装されている箇所も多いですが、network/HTTP 関連の動作確認で urllib 等を利用します）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にしたいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略時のデフォルト)
   - OPENAI_API_KEY=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env の書き方: KEY=VALUE、引用符・コメント等をサポート（config._parse_env_line を参照）

5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単なコード例）

以下は基本的な使い方のサンプルです。適宜 import と日付を調整して実行してください。

- DuckDB 接続の作成
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのセンチメントスコア計算（OpenAI を使用）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定（ETF + マクロ）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_schema, init_audit_db
  - # 既存の DuckDB 接続へスキーマ追加
  - init_audit_schema(conn, transactional=False)
  - # 監査専用 DB を初期化
  - audit_conn = init_audit_db("data/audit.duckdb")

- リサーチ用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - recs = calc_momentum(conn, target_date=date(2026, 3, 20))

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  - for i in issues: print(i)

注意点:
- LLM を呼ぶ関数は API キーを引数で注入可能（テスト容易性）。環境変数 OPENAI_API_KEY を設定しておくと便利です。
- J-Quants API はレート制限があるため jquants_client は内部でスロットリング・リトライを行います。ID トークンは get_id_token() で取得され自動キャッシュされます。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py       — ニュースセンチメント（銘柄別） + ユーティリティ
  - regime_detector.py — 市場レジーム判定（ETF + マクロ）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETLResult 再エクスポート
  - news_collector.py  — RSS 収集 & 正規化
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - quality.py         — データ品質チェック
  - stats.py           — 統計ユーティリティ（zscore_normalize 等）
  - audit.py           — 監査ログスキーマ定義 & 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ公開されているが本コードベースに含まれる機能に応じて配置)
- その他モジュール（strategy, execution, monitoring などの名前が __all__ に含まれるが、用途に合わせて実装を参照）

---

## 重要な設計・運用上の注意

- 環境分離: KABUSYS_ENV による環境区分（development / paper_trading / live）。is_live フラグ等で運用分岐が可能。
- セキュリティ:
  - RSS 収集には SSRF 対策、XML の defusedxml を利用、受信サイズチェックあり。
  - J-Quants のトークンは環境変数で管理。401 発生時は自動リフレッシュを試行します。
- 再現性・フェイルセーフ:
  - LLM 呼び出し失敗時はゼロやスキップで継続（例: macro_sentiment=0.0）。ETL は部分失敗でも他処理を続けます。
- テスト容易性:
  - OpenAI 呼び出しや URL オープンなどは内部関数をモック可能（unittest.mock.patch で差し替え）

---

## よくある操作（CLI 等が無い場合のワンライナー）

- simple ETL 実行（対話式 / スクリプト）
  - python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, target_date=datetime.date.today()).to_dict())"

- news scoring（OpenAI 必要）
  - python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,3,20)))"

---

## 追加情報 / 開発者向け

- .env の自動ロードはプロジェクトルートを .git または pyproject.toml から検出して行われます。自動ロードの挙動は `src/kabusys/config.py` を参照してください。
- DuckDB の executemany に関する互換性考慮（空パラメータの扱い等）や、DDL の transactional フラグなど、実運用で遭遇しやすい制約に対応する実装が含まれています。
- モジュール間の結合を避ける設計（例: regime_detector は news_nlp の内部 _call_openai_api を直接参照しない）により、ユニットテストやモックが容易です。

---

README は以上です。実行時の詳細な API レスポンス形式やテーブルスキーマ等は各モジュール（特に jquants_client.py / data/*.py / ai/*.py）内の docstring を参照してください。必要であれば README に使い方のスクリプト例や .env.example のテンプレートも追加します。どの情報を追記しますか？