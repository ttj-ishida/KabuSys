# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）です。  
J-Quants や RSS、OpenAI（LLM）を活用してデータ収集・品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などを行うことを目的としています。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心としたオンディスク/インメモリ処理
- 冪等性（ETL / 保存処理は ON CONFLICT / upsert を使用）
- ネットワーク呼び出しはリトライ/バックオフやレートリミットを実装
- テスト時に差し替え可能な呼び出しポイント（モックを想定）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API 経由で株価日足（OHLCV）、財務データ、上場リスト、JPX カレンダーを取得（pagination/認証/リトライ対応）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損 / 重複 / 将来日付 / スパイク検出などの品質チェック（quality モジュール）

- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策・レスポンスサイズ制限・URL 正規化）と raw_news への冪等保存ロジック（news_collector）

- ニュース NLP（LLM）
  - 銘柄単位のニュース統合センチメント（news_nlp.score_news）
  - マクロ記事に基づく市場レジーム判定（regime_detector.score_regime）

- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等

- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定の監査テーブル定義・初期化（audit モジュール）
  - 監査DBの初期化ユーティリティ（init_audit_db）

- 設定管理
  - .env または環境変数からの設定読み込み（自動ロード機能・無効化オプションあり）

---

## 必要条件 / 依存ライブラリ（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib 等）

※ 実際の requirements はリポジトリに合わせて pip requirements ファイルを用意してください。

---

## 環境変数（主なもの）

以下はライブラリ内で参照される主な環境変数です（Settings クラス参照）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

OpenAI:
- OPENAI_API_KEY — LLM 呼び出しに使用（関数呼び出し時に api_key を明示して上書き可能）

その他（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト data/monitoring.db）

自動 .env 読み込み:
- リポジトリルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージのインストール（プロジェクトに requirements.txt がある想定）
   ```bash
   pip install -r requirements.txt
   ```
   代表的には:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の準備
   - リポジトリのルートに `.env` を作成し、上記の必須変数を設定します（例は .env.example を参考にしてください）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. データベースディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API と実行例）

以下は Python REPL やスクリプトから呼び出す基本的な例です。

- DuckDB 接続を開いて ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しないと今日が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）を生成:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数または api_key 引数で指定
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # もしくは init_audit_schema(conn) を既存接続へ適用
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))
  ```

注意:
- OpenAI 呼び出しを行う関数（score_news, score_regime 等）は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。失敗時はフェイルセーフでスコア0やスキップする実装箇所が多いです。
- テスト時には内部の API 呼び出し関数をモックすることが想定されています（例: news_nlp._call_openai_api の patch）。

---

## よく使うユーティリティ / API の説明（抜粋）

- kabusys.config.settings
  - アプリケーション設定を提供するシングルトン。環境変数のラップ。

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への保存）

- kabusys.data.pipeline
  - run_daily_etl: 日次の ETL（calendar → prices → financials → 品質チェック）

- kabusys.data.quality
  - run_all_checks: 欠損・重複・スパイク・日付不整合の一括チェック

- kabusys.data.news_collector
  - fetch_rss: RSS 取得と前処理ユーティリティ

- kabusys.ai.news_nlp
  - score_news: ニュースを LLM で評価して ai_scores テーブルへ書き込み

- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA とマクロ記事センチメントを合成して market_regime を書き込み

- kabusys.data.audit
  - init_audit_schema / init_audit_db: 監査ログテーブルを初期化

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py (再エクスポート)
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (コードの一部が monitoring 用 DB を想定、README には詳細記載なし)

（上記は主なモジュールの一覧です。実際はさらにユーティリティ関数等を含みます。）

---

## 初期化・運用のポイント / 注意事項

- DuckDB のファイルパスは settings.duckdb_path で管理されます。バックテストや CI では ":memory:" を利用可能です。
- J-Quants の ID トークンは自動取得・キャッシュされますが、get_id_token を直接呼ぶこともできます。
- ニュース取得では SSRF 対策・レスポンスサイズ制限が実装されていますが、外部フィードの信頼性に依存します。
- OpenAI 呼び出しはレート制限やエラーに対してリトライ/フォールバックを備えています。API のコストに注意してください。
- ETL は個々のステップで例外を捕捉して処理を継続する設計です。result.errors や result.quality_issues を確認して運用判断してください。
- 自動 .env ロードを無効化したいテストなどのケースでは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## トラブルシューティング

- 「環境変数が設定されていません」とエラーが出る
  - 必須環境変数（JQUANTS_REFRESH_TOKEN など）が未設定です。.env を確認してください。

- DuckDB に書き込めない / ファイルが作成されない
  - パスの親ディレクトリが存在するか確認してください。init_audit_db は必要に応じて親ディレクトリを自動作成しますが、他の部分では事前作成が必要な場合があります。

- OpenAI API 呼び出しで 401/429 等が出る
  - API キーが正しいか、使用制限に達していないかを確認してください。ライブラリ内でもリトライとフォールバック実装がありますが、キー自体が無効だと処理が進みません。

---

## テスト戦略（簡単な示唆）

- ネットワーク依存箇所（OpenAI 呼び出し、J-Quants、RSS 取得）はモック（unittest.mock）で差し替えてテストする設計になっています（例えば news_nlp._call_openai_api を patch）。
- DuckDB は ":memory:" でインメモリ DB を使うと高速に単体テストが可能です。
- ETL の部分は run_daily_etl の戻り値（ETLResult）を検査して期待するフィールド値を検証します。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、またはより詳細な CLI 起動・デプロイ手順（systemd / cron のジョブ設定例や Dockerfile）も作成できます。どの部分を拡張しますか？