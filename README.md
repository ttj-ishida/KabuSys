# KabuSys

日本株向けのデータプラットフォーム兼自動売買 (バックエンド) ライブラリ。  
DuckDB を用いたデータパイプライン、J-Quants API 統合、ニュース収集・NLP、LLM を用いた市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目標とした Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント / マクロセンチメント評価
- 市場レジーム判定（MA200 と LLM センチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）およびリサーチ用ユーティリティ
- データ品質チェック、監査ログスキーマ（発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み機能あり）

設計上の重要ポイント:
- ルックアヘッドバイアス防止（内部で date.today() を安易に参照しない）
- ETL・保存処理は冪等性を重視（ON CONFLICT / INSERT ... DO UPDATE等）
- 外部 API 呼び出しにリトライ・バックオフ・レート制御を導入
- セキュリティ考慮（RSS の SSRF 対策、defusedxml など）

---

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult で集約
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（リフレッシュトークン → id_token）
  - 日足・財務・カレンダー・上場情報の取得
  - レートリミット管理・リトライ
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、前処理、raw_news へ保存
  - SSRF 対策、受信サイズ制限、XML パースの安全化
- ニュース NLP / LLM（kabusys.ai.news_nlp）
  - ニュースを銘柄別に集約して LLM へ送信し ai_scores を作成
  - バッチ処理、リトライ、レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュース LLM スコアでレジーム判定（bull/neutral/bear）
  - 結果を market_regime テーブルへ冪等書込
- 研究・ファクター群（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / zscore_normalize 等
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL と初期化ユーティリティ
  - init_audit_schema / init_audit_db

---

## セットアップ手順

以下はローカル開発環境向けの基本手順例です。

前提:
- Python 3.10+（typing | 標準の型注釈に依存）
- DuckDB を利用可能
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- J-Quants のリフレッシュトークン

1. リポジトリをクローン、仮想環境作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   (プロジェクトに requirements.txt がなければ次の主要パッケージをインストールしてください)
   ```bash
   pip install duckdb openai defusedxml
   ```
   追加で logging 等の標準パッケージは不要です。必要に応じて pytest 等を追加してください。

3. 環境変数設定
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=sk-...
   任意:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  (デフォルト: INFO)
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   例 (.env):
   ```env
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

4. 初期 DB 準備（監査DB 例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

下記は簡単な Python スニペット例です。適切な環境変数が設定されている前提です。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("written:", n_written)
  ```

- 市場レジーム判定の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルへ書き込む
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records))
  ```

- 監査スキーマ初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しはネットワークやレート制限で失敗するケースがあるため、score_news / score_regime はフェイルセーフ（失敗時はスコア 0.0 や該当銘柄スキップ）で設計されています。
- ETL は冪等に設計されているため、同一期間で再実行しても重複を生じないよう保存処理が組まれています。

---

## ディレクトリ構成

主要なファイル・モジュールの構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP / LLM スコアリング
    - regime_detector.py               — MA200 + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py           — マーケットカレンダー管理（営業日判定等）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py                — J-Quants API クライアント（取得 + 保存）
    - news_collector.py                — RSS 収集・前処理
    - stats.py                         — Zスコア正規化等
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログ DDL / 初期化
    - etl.py                           — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py               — Momentum / Value / Volatility
    - feature_exploration.py           — 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ など多数の実装ファイル

（上記はリポジトリの主要モジュールを抜粋したものです。）

---

## 実運用・運用上の注意

- KABUSYS_ENV を `live` にすると実際の発注等と結びつく箇所（将来的に実装される部分）での挙動を切り替える想定です。現行実装では多くがデータ処理・スコア計算に留まりますが、環境フラグの整合性に注意してください。
- OpenAI の API 呼び出しを行う箇所は API キーの保護・レートの管理（リトライ方針）に注意してください。
- J-Quants API の利用にあたっては利用規約・レート制限を守ってください（jquants_client に RateLimiter 実装あり）。
- DuckDB のファイルはバックアップ・取り扱いに注意してください（ファイル破損・同時書き込み等）。

---

## 貢献・拡張

- 新しいデータソースの追加、ニュースソースの拡張、研究用ファクターの追加はモジュール単位で実装できます。
- テストは各モジュールを個別にモックして行う方針（例: OpenAI 呼び出しはモック可能）。
- 自動ロードされる .env の挙動を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利です）。

---

ご不明点や README に追加してほしい細部（例: 特定の API 使用方法、より詳しい DB スキーマ、運用手順）などがあれば教えてください。README を補強して反映します。