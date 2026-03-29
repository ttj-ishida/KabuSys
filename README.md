# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
DuckDB をデータレイクとして使用し、J-Quants / RSS / OpenAI (LLM) 等と連携して以下を実現します。

- ETL（株価・財務・カレンダー）の差分取得・保存・品質チェック
- ニュースの収集と銘柄別 NLP（LLM）スコアリング
- マーケットレジーム判定（ETF + マクロニュースの合成）
- 監査ログ（signal → order → execution）のスキーマ初期化・管理
- 研究用途のファクター計算・特徴量解析ユーティリティ

README ではプロジェクト概要、機能一覧、セットアップ、利用例、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は「データ収集 (ETL)」「品質チェック」「AI によるニューススコアリング」「ファクター計算」「監査ログ管理」を一貫して行うライブラリ群です。  
設計上の主な方針は次の通りです。

- Look-ahead bias の排除を重視（内部で date.today() や datetime.now() を不用意に参照しない実装）
- DuckDB を中心としたローカルデータレイク
- J-Quants API のレート制限・認証リフレッシュ・リトライを考慮した実装
- OpenAI 呼び出しに対するリトライ / JSON モードの検証
- DB 書き込みは冪等（ON CONFLICT 等）で安全に保存

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（J-Quants 連携）
  - market calendar 管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF / gzip / サイズ制限対策）
  - jquants_client: API コール、認証（id_token）取得、保存（raw_prices/raw_financials/market_calendar）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄別にまとめて LLM に投げ、ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)の MA とマクロニュース LLM 結果を合成して market_regime に書き込む
  - OpenAI 呼び出しは gpt-4o-mini を想定（JSON mode を利用）
- research/
  - factor 計算: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10+
- DuckDB を利用可能
- ネットワーク経由で J-Quants / OpenAI にアクセスできること（必要に応じて）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な環境変数を設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。  
   必要な主要環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu API (kabuステーション等)
   KABU_API_PASSWORD=your_password
   # KABU_API_BASE_URL を変更する場合のみ指定
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...

   # OpenAI (AI モジュールが必要な場合)
   OPENAI_API_KEY=sk-...

   # データベースパス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境（development|paper_trading|live）
   KABUSYS_ENV=development

   # ログレベル（DEBUG|INFO|...）
   LOG_LEVEL=INFO
   ```

   .env と .env.local の読み込み優先:
   - OS 環境変数 > .env.local > .env
   - .env.local は .env の上書き（override）を想定

3. DuckDB 用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

4. （任意）監査ログ用 DB 初期化
   Python から監査スキーマを初期化できます:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（簡易例）

ここでは代表的な利用例を示します。実運用ではログ・例外処理を適切に追加してください。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュース NLP スコアリング（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored:", count)
  conn.close()
  ```

- マーケットレジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  conn.close()
  ```

- 監査スキーマを既存接続に追加（トランザクション指定可）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect('data/kabusys.duckdb')
  init_audit_schema(conn, transactional=True)
  ```

- ETL 結果 (ETLResult) を確認する
  - ETLResult.to_dict() を使うと品質チェックの要約やエラー一覧が得られます。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuAPI パスワード
- KABU_API_BASE_URL — kabuAPI のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI 呼び出しに使用（ai モジュールで必要）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

設定が不足している場合、Settings クラスのプロパティは ValueError を投げます。

---

## ディレクトリ構成

主要ファイル／モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                  # news -> ai_scores（LLM）
    - regime_detector.py           # ETF + マクロニュース合成で market_regime
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API client / 保存関数
    - pipeline.py                  # ETL パイプラインの実装（run_daily_etl 等）
    - etl.py                       # ETL の公開型再エクスポート
    - news_collector.py            # RSS 取得・前処理・保存
    - calendar_management.py       # market_calendar 管理・営業日判定
    - quality.py                   # データ品質チェック
    - audit.py                     # 監査ログスキーマ（signal/order/execution）
    - stats.py                     # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py           # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py       # forward returns, IC, summary, rank

（上記は主要モジュールを抜粋したものです。詳細はソースツリーを参照してください）

---

## 動作上の注意 / 設計上のポイント

- Look-ahead bias: 多くの関数は target_date を明示的に受け取り、内部で date.today() を直接参照しない設計になっています。バックテスト用途では取得日より未来のデータが混入しないよう注意してください。
- 冪等性: DB への保存は ON CONFLICT や DELETE/INSERT の組合せで冪等に実装されています。
- レート制限: J-Quants は 120 req/min の制限を守るため内部でスロットリングを行います。大規模に API を叩く場合は注意してください。
- OpenAI 呼び出し: gpt-4o-mini を想定し JSON mode を利用しています。429・タイムアウト・ネットワーク断・5xx はリトライします。APIキーは OPENAI_API_KEY 環境変数か各関数の api_key 引数で指定可能です。
- セキュリティ: news_collector は SSRF 対策（スキーム検証・プライベートホスト検査・リダイレクト検査）やレスポンスサイズ上限、XML パーサの安全実装を行っています。
- テスト: モジュール内で API 呼び出し部分を分離してあり、ユニットテスト時にモック差替えが可能です（例: _call_openai_api のパッチ等）。

---

## 追加情報 / よくある質問

- 自動で .env を読み込みたくない場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト時に便利）。
- ログの管理:
  - Settings.log_level で処理の詳細度を制御します。実際のアプリケーションでは logging.basicConfig 等でログ出力先を設定してください。
- 監査DBの別管理:
  - 監査ログ用に独立した DuckDB を作成することを推奨します（init_audit_db を利用）。

---

必要であれば README に次の内容も追記できます:
- .env.example ファイルのテンプレート
- CI / デプロイ手順（systemd / container での運用例）
- 具体的な SQL スキーマ定義（full DDL）
- さらに詳細な使用例（ニュース収集ジョブの scheduling 例など）

追記したい項目があれば指示してください。