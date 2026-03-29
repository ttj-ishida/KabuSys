# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター算出、監査ログなど、アルゴリズムトレーディングに必要な各種ユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーするモジュール群を提供します。

- データ取得・ETL（J-Quants API との連携、DuckDB への永続化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄センチメント
- 市場レジーム判定（ETF の MA とマクロニュースのセンチメント合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定までのトレース可能なテーブル定義）
- 設定管理（環境変数 / .env の自動読み込み）

設計上の注意点（抜粋）:
- ルックアヘッドバイアスを避けるため、内部で `datetime.today()` / `date.today()` を不用意に参照しない設計
- DuckDB を用いた SQL ベースの高速処理
- 外部 API 呼び出しにはリトライ/バックオフ／レート制御を実装
- LLM 呼び出しは JSON mode を使い、失敗時は安全にフェール（例: スコア 0 にフォールバック）

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl（株価、財務、カレンダーの差分取得・保存・品質チェック）
  - J-Quants クライアント（ID トークン管理、ページネーション、レート制御、保存関数）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - ニュース収集（RSS -> raw_news、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化 / DB 作成ユーティリティ
  - 統計ユーティリティ（Zスコア正規化 等）
- ai
  - news_nlp.score_news: 複数銘柄に対するニュースセンチメントを取得して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して market_regime に保存
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- 設定
  - kabusys.config.settings: 環境変数ベースの設定取得（自動で .env/.env.local をロード）

---

## セットアップ手順

以下はローカルで開発／実行するための基本手順例です。

1. リポジトリをクローンする（既にソースがある前提）

2. 仮想環境を作成して有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要なパッケージをインストール
   - 本リポジトリに requirements / pyproject がある想定ですが、最低限以下が必要です:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

4. 開発インストール（パッケージとして使う場合）
   - pip install -e .

5. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。
   - 必須例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...           # kabuステーション API 用（必要な場合）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...              # AI 機能を使うときに必須
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

6. データディレクトリなど（デフォルト）
   - DuckDB: data/kabusys.duckdb（設定: DUCKDB_PATH）
   - 監視用 sqlite: data/monitoring.db（設定: SQLITE_PATH）

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。Python REPL / スクリプトから利用します。

- DuckDB 接続を作って ETL を実行する
  - 例:
    - python - <<'PY'
      import duckdb, datetime
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect('data/kabusys.duckdb')
      result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
      print(result.to_dict())
      PY

- ニュースセンチメントを生成して ai_scores に書き込む（OpenAI API キーが必要）
  - 例:
    - python - <<'PY'
      import duckdb, datetime, os
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect('data/kabusys.duckdb')
      # 環境変数 OPENAI_API_KEY を設定済みであること
      n = score_news(conn, target_date=datetime.date(2026,3,20))
      print("written:", n)
      PY

- 市場レジーム評価（ETF 1321 を基準）
  - 例:
    - python - <<'PY'
      import duckdb, datetime
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect('data/kabusys.duckdb')
      score_regime(conn, target_date=datetime.date(2026,3,20))
      PY

- 監査ログ用の DuckDB を初期化する
  - 例:
    - python - <<'PY'
      from kabusys.data.audit import init_audit_db
      conn = init_audit_db('data/audit.duckdb')
      print("audit db initialized")
      PY

- ファクター計算・解析（研究用途）
  - example:
    - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    - conn = duckdb.connect('data/kabusys.duckdb')
    - mom = calc_momentum(conn, target_date)
    - mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY (AI 機能で必須)  
  OpenAI API を呼ぶ際に使います。score_news / score_regime でも引数として渡すことが可能。

- KABU_API_PASSWORD  
  kabuステーション API を使う場合のパスワード。

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  
  Slack 通知を行う場合に必要。

- KABUSYS_ENV (任意)  
  development / paper_trading / live のいずれか。settings.is_live 等で環境判定に使用。

- LOG_LEVEL (任意)  
  DEBUG/INFO/WARNING/ERROR/CRITICAL

- DUCKDB_PATH, SQLITE_PATH (任意)  
  データベースファイルのパス。デフォルトは `data/kabusys.duckdb` / `data/monitoring.db`。

自動読み込み:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env`→`.env.local` の順で環境変数を読み込みます。OS 環境変数は保護され、`.env.local` は上書きします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースは以下の特徴があります:
- export KEY=val 形式を許容
- クォート（' または "）内のエスケープを正しく処理
- クォート無しでは `#` の前にスペースがある場合をコメントと認識

---

## 実装上の振る舞い（重要な注意点）

- ニュース NLP / レジーム検出は OpenAI の JSON Mode（gpt-4o-mini 等）を使う設計です。API レスポンスが不正な場合、関数は例外を投げるのではなく安全にフォールバック（例: スコア 0）するように設計されています（フェイルセーフ）。
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを実装しており、ページネーション処理にも対応しています。
- DuckDB への挿入は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を使用しており、ETL は既存データを上書きして最新化します。
- ETL / 品質チェックは個々のステップが独立して例外処理され、片方のステップ失敗で全体を止めない（結果にエラー情報を残す）実装です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                          # 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                       # ニュースセンチメント生成（score_news）
  - regime_detector.py                # マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                 # J-Quants API クライアント & 保存関数
  - pipeline.py                       # ETL パイプライン / run_daily_etl 等
  - etl.py                            # ETLResult 再公開
  - news_collector.py                 # RSS 収集（SSRF 対策等）
  - quality.py                        # データ品質チェック
  - stats.py                          # 統計ユーティリティ（zscore_normalize）
  - calendar_management.py            # 市場カレンダー管理（営業日判定等）
  - audit.py                          # 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py                # モメンタム/バリュー/ボラティリティ算出
  - feature_exploration.py            # 将来リターン / IC / summary / rank

上記以外にも strategy / execution / monitoring 用モジュール（README に示された __all__ 等）を用意する設計になっています。

---

## 開発・テスト

- 各モジュールは外部サービスとやり取りする部分（OpenAI / J-Quants / HTTP）を分離しており、ユニットテストではこれらをモックして検証できるように実装されています（例: _call_openai_api をパッチする等）。
- 自動.env 読み込みをテストから無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 参考・補足

- LLM を用いる機能はAPIコストが発生します。運用時はAPIキー・モデル・料金にご注意ください。
- live 環境での自動発注機能を組み込む場合、十分な検証（バックテスト・ドライラン・安全な冗長チェック）を実施してください。
- 監査ログ（audit）機能は発注の冪等性やトレーサビリティを重視しているため、実運用ではこれらのテーブルに書き込むフローを必ず経由することを推奨します。

---

作成・保守: KabuSys 開発チーム（コードベースの関数コメント・ドキュメントに基づいて README を作成しました）。追加の使い方や運用手順を README に追記したい場合は、目的（例: デプロイ手順、cron の設定、Slack 通知設定）を教えてください。