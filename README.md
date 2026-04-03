# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、AI ニュース分析、監査ログ、及び市場レジーム判定を含む日本株自動売買／研究用ライブラリです。DuckDB をデータストアに用い、J-Quants / OpenAI 等の外部 API と連携してデータ取得・品質チェック・特徴量計算・AI スコアリングを行います。

バージョン: 0.1.0

---

## 概要

主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL（差分・冪等保存）
- RSS を用いたニュース収集と OpenAI を利用した銘柄別センチメント（ai_scores）算出
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- リサーチ用のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定などの監査ログ（監査テーブル／初期化ユーティリティ）
- 環境変数ベースの設定管理（.env 自動ロード対応）

設計上の特徴として、Look‑ahead バイアス回避のため日付参照を慎重に扱う点や、API 呼び出しに対するリトライ／バックオフ、冪等保存、フェイルセーフ（API 失敗時のフォールバック）等を重視しています。

---

## 機能一覧

- data
  - jquants_client: J-Quants からのデータ取得（株価 / 財務 / カレンダー）と DuckDB への保存関数
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実装（run_daily_etl 等）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集用ユーティリティ（URL 正規化・SSRF 防御・パース）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: 汎用統計関数（zscore_normalize 等）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI によって算出し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（探索・評価）
- 設定管理: kabusys.config.Settings（.env 自動読み込み、各種環境変数）

---

## 必要な環境・依存

（実行環境に応じ適宜調整してください）

- Python 3.10+
- 主要依存パッケージ（ソース内 import を参照）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime, 等）

pip インストール例（プロジェクトに setup がある想定）:

- 仮想環境を作成・有効化
- pip install -e . あるいは最低限:
  - pip install duckdb openai defusedxml

---

## 環境変数（主要）

設定は .env または環境変数から読み込まれます。プロジェクトルート検出は .git または pyproject.toml に基づきます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須 / 重要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）
- KABU_API_BASE_URL: kabu API 基本 URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知関連（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

例 (.env.example):

    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=your_openai_api_key
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
     - （requirements.txt がない場合）pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに .env を作成（上の例参照）
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB データベースの準備
   - デフォルトでは settings.duckdb_path = data/kabusys.duckdb
   - 必要に応じて初期スキーマを作成する（スキーマ定義ユーティリティは別モジュールに存在する想定）

注意: J-Quants / OpenAI の API キーは必ず設定してください。AI 機能やデータ ETL の一部はこれらに依存します。

---

## 使い方（主要な API の例）

以下は Python REPL かスクリプト内での基本的な使い方例です。

- DuckDB 接続を作成

    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価／財務／カレンダーの差分取得＋品質チェック）

    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント算出（OpenAI 必須）

    from datetime import date
    from kabusys.ai.news_nlp import score_news

    count = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {count}")

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）

    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    score_regime(conn, target_date=date(2026, 3, 20))
    # market_regime テーブルに書き込まれます

- 監査 DB を初期化（監査用専用 DB を作る）

    from kabusys.data.audit import init_audit_db

    audit_conn = init_audit_db("data/audit.duckdb")
    # 監査テーブルが作成されます（UTC タイムゾーン固定）

- ファクター計算・リサーチ関数の呼び出し

    from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

    m = calc_momentum(conn, date(2026, 3, 20))
    v = calc_value(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))

各関数は DuckDB 接続と対象日付を受け取り、結果を Python のリスト / dict で返します。返値の形式は各関数の docstring を参照してください。

---

## 注意点 / 設計上の考慮

- Look‑ahead バイアス対策: 多くの関数は内部で date.today() を参照せず、呼び出し側が target_date を明示することを前提としています。
- 冪等性: J-Quants から取得したデータは DuckDB に ON CONFLICT DO UPDATE で保存する設計です（重複挿入を防ぐ）。
- API エラー対策: OpenAI・J-Quants 呼び出しにはリトライ・バックオフが実装されており、致命的でない場合はフェイルセーフ（既定値やスキップ）で継続します。
- セキュリティ: news_collector では SSRF 対策、XML の defusedxml 使用、受信サイズ制限 等を実装しています。
- テスト時の環境変数ロード停止: テストからの .env 自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数管理・.env 自動ロード・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント算出（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py              — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
  - news_collector.py   — RSS 収集と前処理ユーティリティ
  - quality.py          — データ品質チェック（QualityIssue）
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログスキーマ定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py  — ファクター計算（モメンタム / ボラティリティ / バリュー）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- research/* その他のユーティリティやエクスポート

---

## よくある利用フロー (例)

1. .env を作成して J-Quants / OpenAI のキーを設定
2. データベースパス（DUCKDB_PATH）を確認・作成
3. 日次バッチで run_daily_etl を実行してデータを蓄積
4. news_collector.fetch_rss を用いて raw_news を収集（または RSS の収集ジョブ）
5. score_news で ai_scores を更新
6. regime_detector.score_regime で market_regime を更新
7. research モジュールで因子を計算・評価、戦略シグナル生成へ接続
8. audit テーブルでシグナル→発注→約定のトレーサビリティを保持

---

## 最後に

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。各モジュールの詳細な仕様やパラメータ、戻り値等はモジュール内の docstring を参照してください。追加の CLI、ユーティリティやテスト、CI 設定はプロジェクトのルートにある他ファイルで管理する想定です。必要があれば README を機能別に分割して追記できます。