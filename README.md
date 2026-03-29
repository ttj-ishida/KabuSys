# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム検出、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを包括的に提供します。

注意: この README はコードベース（src/kabusys/*）に基づく概要・セットアップ・使い方をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤と研究プラットフォームのためのモジュール群です。主な責務は次の通りです。

- J-Quants API を用いた株価 / 財務 / 市場カレンダーの差分取得と DuckDB への永続化（ETL）
- RSS によるニュース収集とニュース前処理（SSRF 対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別スコア）およびマクロセンチメントを組み合わせた市場レジーム判定
- 監査ログ（信号 → 発注 → 約定）を格納する監査スキーマの初期化ユーティリティ
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）・特徴量探索・統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上のポイント:
- ルックアヘッドバイアス回避（多くの処理で date.today() を直接参照しない）
- DuckDB を中心としたローカル DB 主導のワークフロー
- 冪等性（ETL の保存は ON CONFLICT DO UPDATE 等で上書き）
- フェイルセーフ: 外部 API エラー時は適切にフォールバック（例: LLM 失敗でスコア 0.0）

---

## 機能一覧（抜粋）

- 設定管理
  - kabusys.config.Settings（環境変数・.env 自動読み込み、必須パラメータ取得）
- データ ETL / API クライアント
  - kabusys.data.jquants_client: J-Quants API クライアント（取得・保存関数、トークン管理、レート制御）
  - kabusys.data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL パイプライン）
- ニュース収集 / NLP
  - kabusys.data.news_collector: RSS 収集、前処理、記事ID生成、SSRF 対策
  - kabusys.ai.news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - kabusys.ai.regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に保存
- 研究（Research）
  - kabusys.research.factor_research: calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize: Zスコア正規化ユーティリティ
- データ品質／運用
  - kabusys.data.quality: 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
  - kabusys.data.calendar_management: 市場カレンダー取得・営業日判定・next/prev_trading_day 等
- 監査ログ（Audit）
  - kabusys.data.audit: 監査スキーマ初期化（init_audit_schema / init_audit_db）

---

## 必要な環境変数

主に次の環境変数が使用されます。必須のものは Settings のプロパティで _require() によりチェックされます。

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込み無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env の書式やパース規則は kabusys.config._parse_env_line を参照してください（export プレフィックス、クォート、コメントの扱いなどに対応）。

---

## セットアップ手順

1. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合 .venv\Scripts\activate）

2. パッケージと依存関係のインストール
   - このリポジトリのルートで:
     - pip install -e .   （パッケージが pyproject.toml / setup.cfg を持つ想定）
   - 必須ライブラリ（抜粋）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成し、上記の必須変数を設定してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

4. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb に DuckDB を作成します。
   - 必要なら手動でディレクトリを作成:
     - mkdir -p data

5. DuckDB スキーマ初期化（監査ログ等）
   - 監査用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 基本的な使い方（コード例）

- 設定の取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live などを参照可能

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクト（fetched/saved/quality_issues/errors を観察可能）

- ニューススコアリング（銘柄別、OpenAI 使用）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  - 戻り値は書き込んだ銘柄数（ai_scores テーブルに挿入）

- 市場レジーム判定（MA200 と LLM 結合）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))

- 品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化（既存接続へ）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

注意点:
- OpenAI 呼び出しは network/レート問題で失敗する可能性があるため、API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数はルックアヘッドバイアスを避けるため target_date 引数を必須にしたり、date.today() を内部で参照しない実装になっています。バッチ実行時は明示的な target_date を渡すことが推奨されます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py        — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集 / 前処理
    - calendar_management.py— 市場カレンダー管理・営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank

各モジュールはドキュメント文字列で設計方針・処理フロー・想定表（テーブル）を詳細に記述しています。実運用では DuckDB のスキーマ（raw_prices / raw_financials / raw_news / ai_scores / market_regime / market_calendar / news_symbols など）が前提になります。

---

## 運用上の注意 / ベストプラクティス

- 秘密情報（API トークン等）は .env に置くかシークレット管理を使用して OS 環境変数に注入してください。`.env.example` を参照して .env を作成してください（コード内で未設定の必須変数は例外になります）。
- ETL は差分取得設計（最後の取得日からのインクリメンタル）になっています。初回は十分に過去の日付から取得する必要があります。
- OpenAI の API 呼び出しは料金・レートに注意してください。news_nlp はバッチ（最大 20 銘柄/コール）で呼び出す設計です。
- DuckDB への executemany に関する制約（空リスト不可など）を考慮する必要があります（コードはその点に対応済み）。
- ETL / AI 呼び出しのユニットテストでは、モジュール内の API 呼び出し関数（例: _call_openai_api, _urlopen, _get_cached_token など）をモックする設計になっています。

---

## 参考（よく使う API）

- 設定取得: from kabusys.config import settings
- ETL 実行: from kabusys.data.pipeline import run_daily_etl
- ニューススコア: from kabusys.ai.news_nlp import score_news
- レジーム判定: from kabusys.ai.regime_detector import score_regime
- 監査 DB 初期化: from kabusys.data.audit import init_audit_db / init_audit_schema
- J-Quants 直接利用: from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar

---

もし README に追加してほしい項目（例: サンプル .env.example、CI / デプロイ手順、テーブル DDL、ユニットテストの実行方法）があれば教えてください。必要に応じて README を拡張して具体的なコマンド・コード例・注意点を追記します。