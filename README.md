# KabuSys

日本株向け自動売買プラットフォームのライブラリ群。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ（約定トレーサビリティ）など、バックテスト・運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム構築のための基盤コンポーネント群です。主な機能は以下の通りです。

- J-Quants API からのデータ取得（株価日足・財務・上場情報・市場カレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF・サイズ制限・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 研究用のファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）のための監査スキーマ初期化・DB管理
- 環境変数管理と自動 .env ロード（プロジェクトルート検出）

設計上の重点点:
- ルックアヘッドバイアス回避（明示的な target_date 指定・当日参照の回避）
- 冪等性を重視（DB 保存は ON CONFLICT / DO UPDATE 等）
- フェイルセーフな外部 API 呼び出し（失敗時はスキップ/フォールバックして継続）
- 外部ライブラリの使用を限定（標準ライブラリ + 必要最小限の依存）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline: 日次 ETL の実装（run_daily_etl 等）
  - news_collector: RSS 取得と raw_news への保存ロジック
  - calendar_management: 市場カレンダーの判定・更新ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査スキーマ定義と初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントのスコアリング（OpenAI 使用）
  - regime_detector.score_regime: マクロ + ETF (1321) MA200 を合成した市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - 環境変数読み込み（.env/.env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクトを介して設定取得

---

## セットアップ手順

以下はローカルで開発・実行するための最低限の手順です。

1. Python 環境（推奨: 3.10+）を用意する
   - 仮想環境を作成する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストールする（必要に応じて requirements.txt を用意してください）
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは additional の HTTP / logging ライブラリ等を requirements に追加してください。

3. リポジトリルートに .env を作成（または環境変数を設定）
   - 自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行われます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（API 用）
   - KABU_API_PASSWORD : kabuステーション API パスワード（発注層で使用）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（通知実装を利用する場合）
   - SLACK_CHANNEL_ID : Slack チャンネル ID
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 実行時）
   - （任意）KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - （任意）LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）
   - （任意）DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - （任意）SQLITE_PATH : 監視 DB などの SQLite パス（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベース初期化（監査ログ用 DB の初期化例）
   - Python スクリプトで:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の conn に対してスキーマ作成:
     ```
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（簡単な例）

以下は代表的なユースケースのサンプルコード例です。すべて DuckDB 接続を受け取る設計なので、テストやバッチで容易に呼び出せます。

1. 日次 ETL を実行する
   - run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェックを順に実行します。
   ```
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースの AI スコアリング（銘柄別）
   ```
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
   print(f"書き込み銘柄数: {written_count}")
   ```

3. 市場レジーム（マクロ + ETF MA200 合成）
   ```
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用
   ```

4. 監査ログ DB 初期化
   ```
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 以降 conn を使って監査テーブルへアクセスできます
   ```

5. 研究用ファクター計算
   ```
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

   conn = duckdb.connect("data/kabusys.duckdb")
   date0 = date(2026, 3, 20)
   mom = calc_momentum(conn, date0)
   val = calc_value(conn, date0)
   vol = calc_volatility(conn, date0)
   ```

注意点:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。api_key 引数で明示的に渡すことも可能です。
- ETL/AI 実行時はデータの存在（raw_news, prices_daily, news_symbols 等）を確認してください。
- datetime.today() / date.today() を直接参照しない実装方針のため、バックテストや再現性のあるバッチ処理が容易です（常に target_date を明示することが推奨されます）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (placeholder in package __all__ — 実装に応じて追加)
    - execution/ (発注・ブローカー連携用の層、実装に応じて追加)
    - strategy/ (戦略ロジック、実装に応じて追加)

パッケージ公開時は top-level の __all__ に data, strategy, execution, monitoring が含まれます。

---

## 実運用上の注意・運用メモ

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。CIやユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にできます。
- J-Quants のレート制限や OpenAI のレート制限に注意。各クライアントはリトライ・スロットリングを実装していますが、バルク実行時はバックオフやスループット管理を行ってください。
- DuckDB の executemany はバージョン差による挙動差があるため、本実装では空パラメータの executemany を回避するガードを入れています。
- ニュース収集は SSRF 対策や受信サイズ制限、XML パースの安全化（defusedxml）を行っていますが、運用時はフィード元の信頼性も確認してください。
- 監査ログは削除を想定していないため注意（FK は ON DELETE RESTRICT）。監査 DB のバックアップ運用を検討してください。

---

## 開発・テスト

- ローカルで DuckDB を使ったテストが可能です（:memory: も使用可）。
- OpenAI / J-Quants 呼び出しは外部 API へ依存するため、ユニットテストでは _call_openai_api や jquants_client._request 等をモックしてください（コード内にも patch しやすい設計になっています）。
- news_collector._urlopen や ai の _call_openai_api はテスト用に差し替え可能です。

---

必要があれば、README に以下の追加を行えます。
- 完全な requirements.txt（バージョン固定）
- CI / GitHub Actions のサンプルワークフロー
- より詳細な API リファレンス（各 public 関数の引数・戻り値の表）
- 実運用チェックリスト（トークン管理、監査 DB バックアップ、モニタリング設定 等）

ご希望の追加項目があれば教えてください。