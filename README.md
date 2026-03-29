# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
データ収集（J-Quants / RSS）、ETL、品質チェック、特徴量・ファクター計算、ニュースのAIスコアリング、マーケットレジーム判定、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、JPXマーケットカレンダーをページネーション対応で取得
  - 差分取得・バックフィル・冪等保存（ON CONFLICT DO UPDATE）
  - ETL の一括実行（run_daily_etl）と結果クラス（ETLResult）
- ニュース収集・前処理
  - RSS フィード取得（SSRF対策、サイズ制限、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定した実装方針
- AI（LLM）を用いたニュースセンチメント
  - 銘柄ごとのニュースをまとめて gpt-4o-mini に投げ、スコアを ai_scores に保存（score_news）
  - マクロニュース + ETF（1321）200日MA乖離を合成して市場レジーム（bull / neutral / bear）を判定（score_regime）
  - 再試行やAPIエラー時のフォールバック実装あり
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出（QualityIssue を返す）
- カレンダー管理
  - market_calendar による営業日判定、次／前営業日取得、夜間バッチ更新ジョブ（calendar_update_job）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ設計
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のプロパティ経由参照（kabusys.config.settings）

---

## セットアップ手順

前提: Python 3.10+（typing | union 表記等を使用しています）、duckdb 等の依存が必要です。実際のインストール要件は packaging 側で管理してください。

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 開発環境インストール（例）
   - pip install -e .   （パッケージ化されている場合）

4. 必要な環境変数を設定
   - .env または OS 環境変数で設定します。自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）から行われます。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先 Slack チャネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要、引数で注入も可能）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUS_API_BASE_URL: kabuAPI のベースURL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - 自動ロードを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース用ディレクトリ作成（必要に応じて）
   - デフォルトの DUCKDB_PATH 親ディレクトリを作成しておくとよい（init_audit_db が自動作成も実施します）。

---

## 使い方（基本的な例）

以下はパッケージをインポートして主要機能を呼ぶ簡単な例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）を設定してください。

- DuckDB 接続を作成して ETL を実行（日次ETL）
  - Python スニペット:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=date(2026,3,20))
      print(result.to_dict())
  - ETL は calendar → prices → financials → 品質チェック の順に処理します。ETLResult に処理結果や検出された品質問題が格納されます。

- ニュースのAIスコアリング（銘柄ごとのスコアを ai_scores に書き込む）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"scored {n} codes")

  - api_key を省略すると環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM 評価）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化（発注ログ用の DuckDB）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")
    # conn を使って監査テーブルにアクセスできます

- J-Quants トークン取得 / API 呼び出し
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()
    records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,31))

注記:
- score_news / score_regime は OpenAI API を利用します。エラー時のフォールバックやリトライロジックが組み込まれていますが、実行にはキーとAPIの利用可能性が必要です。
- 各関数は duckdb.DuckDBPyConnection を引数に取る設計です。接続は呼び出し側で管理してください。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- OPENAI_API_KEY — OpenAI呼び出しに必要（score_news/score_regime）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化

.env ファイルの自動読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` → `.env.local` の順でロードされます。
- `.env.local` は上書き（override=True）されますが、OS 環境変数は保護されます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクト内 src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py   — マーケットカレンダー / 営業日判定 / calendar_update_job
    - etl.py                   — ETL インターフェース再エクスポート
    - pipeline.py              — ETL パイプライン（run_daily_etl 等、ETLResult）
    - stats.py                 — zscore_normalize 等
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py                 — 監査ログ（テーブルDDL、初期化関数）
    - jquants_client.py        — J-Quants API クライアント（取得・保存処理）
    - news_collector.py        — RSS 取得・前処理（SSRF対策、正規化）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー 等
  - (ほか strategy / execution / monitoring 等のパッケージ名が __all__ に含まれる想定)

---

## 開発・テストに関する補足

- env の自動読み込みを抑制したいユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部（_call_openai_api など）はテスト時にモック可能な設計（unittest.mock.patch などで差し替え）になっています。
- DuckDB の executemany に関する互換性（空リスト不可など）を考慮した実装がされています。

---

## ライセンス / 貢献

この README はコードベースから生成された概要をまとめたものです。実際のライセンス情報・貢献ガイドはリポジトリのトップレベルファイル（LICENSE / CONTRIBUTING.md 等）を参照してください。

---

不明点や README に追記したい利用シナリオ（例: バックテスト用のデータ準備、発注フロー統合例など）があれば教えてください。具体的なサンプルコードや運用手順を追加します。