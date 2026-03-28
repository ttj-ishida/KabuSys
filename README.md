# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）等の機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得と冪等保存（DuckDB）
- RSS ベースのニュース収集と前処理、記事と銘柄の紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄別スコア / マクロセンチメント）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 注文／約定までの監査ログ用スキーマ（DuckDB）

設計方針として、Look-ahead バイアス対策・冪等処理・フェイルセーフ（API失敗時の継続）・テスト容易性を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・リトライ・トークン自動更新）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: fetch_rss, 前処理、SSRF対策、トラッキングパラメータ削除
  - 品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 汎用統計: zscore_normalize
- ai
  - ニュース NLP: score_news — 銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - レジーム判定: score_regime — ETF(1321)のMA乖離とマクロセンチメント合成で market_regime を書き込み
- research
  - factor 計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を探索し読み込み）
  - settings オブジェクト経由で設定値を取得

---

## セットアップ手順

以下は開発・実行環境を用意する最低限の手順例です。

1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai（新しい OpenAI SDK を使用。OpenAI クライアントとして OpenAI クラスを利用）
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。
   - pip install -r requirements.txt
   - または開発インストール: pip install -e .

4. 環境変数を設定
   - 必須（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD — kabuステーション用パスワード（使用する場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 監視通知等に使用する場合
   - DB パスは環境変数で上書き可能（デフォルトは `data/kabusys.duckdb` 等）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - .env / .env.local をプロジェクトルートに置けば自動で読み込まれます（優先度: OS 環境 > .env.local > .env）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（代表的な例）

以降の例は Python スクリプトからモジュールを直接利用する方法です。DuckDB はファイルベースなので簡単に開始できます。

- DuckDB 接続を作る例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次パイプライン）を実行する:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント（ai_scores）を算出する:
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    n = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY から取得

  - 関数は取得した銘柄数（書込数）を返します。API 呼び出しはバッチ / リトライ制御があります。

- 市場レジーム判定:
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込み

- 研究用ファクター計算:
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    mom = calc_momentum(conn, date(2026, 3, 20))
    volatility = calc_volatility(conn, date(2026, 3, 20))
    value = calc_value(conn, date(2026, 3, 20))

- 監査ログスキーマを初期化する:
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 設定値の参照:
  - from kabusys.config import settings
    token = settings.jquants_refresh_token
    print(settings.env, settings.log_level)

注意:
- score_news・score_regime は内部で OpenAI SDK（OpenAIクラス）を使います。api_key は関数引数で渡すこともできます（テストや複数キー運用時に便利）。
- 多くの関数は Look-ahead Bias を避ける設計（target_date を明示することで安全に再現可能）です。

---

## .env の取り扱い

- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env 例（.env.example を参考に作成）:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## ディレクトリ構成

概要（主要ファイル / モジュール）:

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                        — 銘柄別ニュースセンチメント算出（score_news）
    - regime_detector.py                 — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント（fetch/save/認証/リトライ）
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - etl.py                             — ETL の公開インターフェース（ETLResult）
    - calendar_management.py             — 市場カレンダー管理
    - news_collector.py                  — RSS 収集・前処理（SSRF対策等）
    - quality.py                         — 品質チェック（QualityIssue 等）
    - stats.py                           — 統計ユーティリティ（zscore_normalize）
    - audit.py                           — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py                 — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py              — 将来リターン / IC / 統計サマリー 等
  - ai/... , research/... の他に strategy/ execution/ monitoring などのパッケージを公開する設計（__all__ 指定）

各ファイルにはモジュールレベルのドキュメント文字列と詳細な実装方針やフェイルセーフ/テストフレンドリなフック（例: _call_openai_api をモック置換）があります。

---

## テスト / 開発メモ

- OpenAI 呼び出し周りやネットワーク I/O 部分はユニットテストでモック可能な設計になっています（内部関数を patch して差し替え）。
- DuckDB をインメモリで使えば外部副作用が少なくテストしやすい（":memory:" を渡す）。
- 自動 .env ロードを無効にしてテスト環境を明示的に設定することを推奨します:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 参考 / 注意事項

- J-Quants API のレート制限や OpenAI API の利用料金に注意してください。実運用では API キー管理とコスト管理を行ってください。
- DB スキーマや監査ログは削除しない運用を前提としています。テーブル作成やマイグレーションは注意して実行してください。
- 本パッケージはバックテストなどで使用する際にも Look-ahead バイアスに配慮した設計になっていますが、ユーザー側でも target_date を明示する等の運用ルールを守ってください。

---

何か特定の機能の使い方（例: ETL の細かいオプション、OpenAI のレスポンス仕様、ニュース収集のソース追加方法）について詳細が必要であれば教えてください。具体的なコード例や設定例を追記します。