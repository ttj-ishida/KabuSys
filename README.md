# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。J-Quants API・RSS・OpenAI を組み合わせてデータ収集、品質チェック、特徴量算出、ニュースセンチメント評価、監査ログ管理、ETL パイプラインを提供します。

---

## 概要

KabuSys は日本株のデータ基盤とリサーチ・自動売買のための共有ユーティリティ群を集めたパッケージです。主な目的は以下です。

- J-Quants から株価・財務・カレンダーを取得して DuckDB に格納する ETL
- RSS ニュースの収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント（ai_score）と市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- リサーチ用ファクター（モメンタム・バリュー・ボラティリティ等）計算
- 監査ログ（signal → order → execution のトレース）用スキーマ初期化
- J-Quants クライアント（認証・ページネーション・保存ユーティリティ）
- SSRF 対策やレート制御など運用を考慮した堅牢な実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API への安全な呼び出し、ページネーション、保存（DuckDB への冪等保存）
  - pipeline: 日次 ETL 実行（market calendar / prices / financials）と ETL 結果クラス
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 収集、前処理、SSRF 防御、raw_news/ news_symbols への保存支援
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ用テーブル定義と初期化ヘルパー
  - stats: z-score 正規化など共通統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して市場レジームを判定
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター算出
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等

その他：環境設定モジュール（kabusys.config）で .env の自動ロード、必要な環境変数管理を行います。

---

## セットアップ手順

前提: Python 3.9+（コードは 3.10/3.11 以降の構文を想定しています。typing 表記があるため新しいバージョンが望ましい）

1. リポジトリをクローンし、プロジェクトルートへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）
   - 基本的に以下が必要になります（requirements.txt がある場合はそちらを使用してください）
     - duckdb
     - openai
     - defusedxml
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトが pip パッケージ化されているなら:
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な主な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（使用する場合）
   - SLACK_CHANNEL_ID: Slack 通知用チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   ```

5. データベース用ディレクトリ（必要なら）を作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリの代表的な使い方例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続と ETL 実行（日次ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- J-Quants ID トークン取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を用いる
  ```

- ニュースセンチメントを生成して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))
  print("written codes:", count)
  ```

- 市場レジーム判定（regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- テストでの OpenAI 呼び出しの差し替え
  - テスト時は内部の _call_openai_api 関数を patch してレスポンスをモックできます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") など

---

## 環境設定（kabusys.config）について

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml がある場所）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local（override=True） > .env（override=False）
  - テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 主要なプロパティ（settings オブジェクト）
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path (デフォルト: data/kabusys.duckdb)
  - settings.sqlite_path (デフォルト: data/monitoring.db)
  - settings.env (development | paper_trading | live)
  - settings.log_level

---

## 主要 API の説明（抜粋）

- ETL / データ
  - run_daily_etl(conn, target_date, id_token=None, ...): 日次 ETL を実行し ETLResult を返す
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: API 取得
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB 保存（冪等）
  - data.quality.run_all_checks(conn, ...): データ品質チェックを実行

- AI
  - ai.news_nlp.score_news(conn, target_date): ニュースセンチメントを計算して ai_scores に保存
  - ai.regime_detector.score_regime(conn, target_date): 市場レジームを判定して market_regime に保存

- Research
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

- Audit
  - data.audit.init_audit_db(db_path): 監査ログ専用 DB を初期化し接続を返す
  - data.audit.init_audit_schema(conn): 既存 conn に監査スキーマを追加

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント＆保存
    - pipeline.py                — ETL パイプライン / ETLResult
    - etl.py                     — ETL 公開インターフェース
    - news_collector.py          — RSS 収集・前処理・SSRF 対策
    - calendar_management.py     — 市場カレンダー管理・営業日判定
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化
    - stats.py                   — 統計ユーティリティ
    - (その他: schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py         — ファクター算出
    - feature_exploration.py     — 将来リターン・IC 等
  - research/...
  - monitoring/, execution/, strategy/ etc. (パッケージ公開名に含まれるが本ツリーでは抜粋)

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス対策
  - 多くの関数は内部で date.today() を直接参照しない、API 呼び出しやクエリにおいても target_date 未満のみ参照する等の配慮があります。バックテスト時は対象日を明示的に渡してください。

- OpenAI 呼び出し
  - gpt-4o-mini の JSON Mode を利用します。API エラーはリトライやフォールバック（スコア=0.0）で処理する設計です。テスト時は _call_openai_api をモックしてください。

- J-Quants API
  - レート制限 (120 req/min) を守る RateLimiter が実装されています。401 受信時は自動リフレッシュを試みます。

- セキュリティ
  - RSS 収集に SSRF 対策（リダイレクト検査、プライベート IP の拒否）を組み込んでいます。
  - .env に機密情報を置く場合は権限管理に注意してください。

---

## テスト・開発

- ユニットテストを書く際は、外部 API 呼び出し（J-Quants / OpenAI / ネットワーク）をモックしてください。
- news_nlp._call_openai_api や regime_detector._call_openai_api、news_collector._urlopen、jquants_client._request などを patch して副作用を抑えたテストが可能です。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うことでテスト環境で .env 自動読み込みを抑制できます。

---

README に不足している情報（パッケージ要件ファイル、CI 設定、実運用向けの runbooks、Slack 通知の仕組みなど）があれば、追記用に .env.example や CONTRIBUTING.md、運用手順を別途作成することを推奨します。必要であればテンプレートを作成しますので指示ください。