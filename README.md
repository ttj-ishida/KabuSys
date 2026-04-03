# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（監視・約定トレーサビリティ）、研究用のファクター計算などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究基盤向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ニュース収集 + OpenAI を用いたニュースセンチメント（銘柄別 ai_score）生成
- マクロと ETF（1321）移動平均乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- DataQuality チェック・カレンダー管理・監査テーブル初期化などのデータ基盤機能
- 研究用にファクター（モメンタム/バリュー/ボラティリティ）計算と探索ユーティリティ

設計上の注意点として、ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を参照しない等）や冪等性（DuckDB への ON CONFLICT 処理）、API のリトライ/バックオフ、SSRF 対策などを組み込んでいます。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の明示的チェック

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（fetch / save 関数）
  - 差分取得・バックフィル・品質チェック

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策・サイズ制限・XML 安全パース（defusedxml）

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄別センチメントを評価して ai_scores に書き込み
  - バッチ処理・リトライ・レスポンスバリデーション

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントの合成
  - market_regime テーブルへの冪等書き込み

- 研究ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ計算
  - 将来リターン計算、IC 計算、ファクター統計、Z-score 正規化

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar の更新・営業日判定・next/prev/get_trading_days 等

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ツール

---

## セットアップ手順

前提: Python 3.9+ 推奨（型注釈に union 型や Annotated を使用しているため最新の安定版を推奨）

1. リポジトリをクローン / コピーしてプロジェクトルートへ移動

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 必須: duckdb, openai, defusedxml
   - その他（ユーティリティや用途に応じて）: requests 等を追加する場合あり

   開発中はプロジェクトを editable インストールしておくと便利です:
   ```
   pip install -e .
   ```

4. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動で読み込みます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須): J-Quants 用リフレッシュトークン
     - OPENAI_API_KEY (または引数で直接渡す): OpenAI API キー
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要時）
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト development)
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト INFO)
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
   - .env のパースはシェル風（export プレフィックス対応、引用符、コメント処理あり）です。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方

ここでは代表的な利用例を示します。すべての API は主に DuckDB 接続を受け取る設計です。

- DuckDB 接続の作成例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別スコア）を生成する
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # APIキーを env に設定している場合、api_key 引数は不要
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored: {count} codes")
  ```

- 市場レジーム判定を行う
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB を初期化する（監査専用 DB を分ける場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダーの夜間更新ジョブを実行する
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

- 研究用: モメンタムファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意:
- OpenAI を呼ぶ関数は api_key を受け取る（引数優先）か、環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError が発生します。
- J-Quants を使う関数は settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）を参照します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env の自動読み込みと Settings
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・バッチ/バリデーション）
      - regime_detector.py     — 市場レジーム判定（ETF + マクロ LLM 合成）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント・保存ユーティリティ
      - pipeline.py            — ETL パイプライン / run_daily_etl など
      - etl.py                 — ETLResult 再エクスポート
      - news_collector.py      — RSS 収集・前処理
      - calendar_management.py — 市場カレンダー管理・判定ユーティリティ
      - quality.py             — データ品質チェック
      - stats.py               — Z-score など共通統計ユーティリティ
      - audit.py               — 監査ログテーブル定義・初期化
    - research/
      - __init__.py
      - factor_research.py     — momentum/value/volatility 計算
      - feature_exploration.py — forward returns / IC / summary / rank
    - monitoring/ (※実装ファイルがある場合)
    - strategy/  (戦略層の実装)
    - execution/ (発注・ブローカー連携)
- pyproject.toml (想定)
- .env.example (想定)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

---

## トラブルシューティング（よくある問題）

- ValueError: OpenAI API キー未設定  
  → OPENAI_API_KEY を環境変数に設定するか、score_news/score_regime に api_key を渡してください。

- ValueError: J-Quants refresh token 未設定  
  → JQUANTS_REFRESH_TOKEN を設定してください（settings.jquants_refresh_token が参照されます）。

- DuckDB にテーブルがない / 初期スキーマが必要  
  → 使用するモジュールに応じて初期化関数（例: init_audit_schema）を呼ぶか、ETL を実行して必要テーブルを作成してください。ドキュメント内の各モジュールに DDL や保存関数が含まれています。

- RSS 取得で内部アドレスに対するエラー（SSRF 検出）  
  → news_collector はプライベート IP / リダイレクト先検査を行います。外部公開の RSS を使用してください。

---

## 開発・貢献

- コードは src/ 配下に配置されています。開発環境では editable install を行い、ユニットテストやモックで外部 API を差し替えて検証してください。
- OpenAI / J-Quants 呼び出し周りは再試行・バックオフ・フェイルセーフが組み込まれています。テスト時は該当関数（_call_openai_api や _urlopen など）をパッチしてモックすることを推奨します。

---

README は以上です。追加で README に含めたい使用例や CI 設定、ライセンス、貢献ガイド等があれば追記します。必要な箇所を教えてください。