# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用のライブラリ群です。  
J-Quants / DuckDB を中心としたデータ ETL、ニュース NLP（OpenAI）、ファクター計算、監査ログ（約定トレーサビリティ）などを備え、取引戦略の研究から運用までをサポートします。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得・ETL
  - J-Quants API から株価（日足）、財務・上場情報、JPX カレンダーを差分取得し DuckDB に冪等保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行
  - 日次 ETL パイプライン（run_daily_etl）を提供

- ニュース NLP（OpenAI）
  - ニュース記事を銘柄ごとに集約して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に保存（score_news）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離と LLM センチメントの合成）（score_regime）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（監査・トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルの初期化・管理（init_audit_schema / init_audit_db）
  - order_request_id を冪等キーとして扱い二重発注を防止する設計

- ニュース収集
  - RSS フィードの安全な収集と前処理（SSRF 対策、トラッキング除去、XML 脆弱性対策）

- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）と環境変数経由の設定取得（kabusys.config.settings）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型アノテーションで `X | None` などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト内に requirements.txt / pyproject.toml があればそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用・テスト用の依存がある場合はプロジェクトの指示に従ってください（pyproject.toml / requirements.txt があればそちらを使用）。

4. 環境変数を設定
   - .env または環境変数で以下を設定します。リポジトリルートに `.env` / `.env.local` がある場合、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for ETL）
   - OPENAI_API_KEY: OpenAI の API キー（必須 for news_nlp / regime_detector）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルト `development`
   - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）
   - その他（LINE トークン、PID/KILL フラグパス等）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（抜粋・コード例）

基本的には DuckDB 接続を生成して各 API に接続を渡して使用します。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの AI スコア算出）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None → 環境変数 OPENAI_API_KEY を使用
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算 / 研究関数の呼び出し:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))

  fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 監査ログ（監査用 DB 初期化）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または既存の DuckDB 接続にスキーマを初期化
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- RSS の取得（ニュース収集の一部）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  # raw_news への保存ロジックはプロジェクトの ETL ワークフローに従って行ってください
  ```

---

## 設定（settings）についての注意

- 環境変数取得は `kabusys.config.settings` 経由で行います（例: `settings.jquants_refresh_token`）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `KABUSYS_ENV` は `development`, `paper_trading`, `live` のいずれかのみ有効です。`LOG_LEVEL` は標準ログレベル名を指定します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に主要モジュールを配置しています。代表的なファイルと簡単な説明は下記の通りです。

- src/kabusys/__init__.py
  - パッケージ初期化 / バージョン

- src/kabusys/config.py
  - 環境変数・設定管理（.env 読み込み、自動ロード、settings）

- src/kabusys/ai/
  - news_nlp.py : ニュース記事の LLM センチメントスコアリング（score_news）
  - regime_detector.py : マクロ + MA200 による市場レジーム判定（score_regime）
  - __init__.py

- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py : 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py : ETL ヘルパー（ETLResult の再エクスポート）
  - calendar_management.py : 市場カレンダー管理ロジック
  - news_collector.py : RSS ニュース収集（SSRF 対策・前処理）
  - stats.py : 汎用統計ユーティリティ（zscore_normalize）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログ（signal/order/execution テーブルの初期化）
  - __init__.py

- src/kabusys/research/
  - factor_research.py : モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク等
  - __init__.py

（上記は主なファイル群の抜粋です。詳細はソースを参照してください）

---

## 運用上の注意 / 設計上のポリシー

- ルックアヘッドバイアス対策:
  - 多くのモジュールは内部で datetime.today() や date.today() を直接参照せず、明示的な target_date を受け取る設計です。バックテスト実行や再現性の確保に有利です。

- フェイルセーフ:
  - OpenAI / J-Quants API 呼び出しでの一部エラーはフォールバック（0.0 スコア等）やリトライで処理を継続する設計です。致命的なエラーは上位に伝播します。

- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE（または個別 DELETE → INSERT）で冪等に実行されるよう設計されています。

- セキュリティ:
  - RSS 取得は SSRF 対策、defusedxml による XML パース、防御的な入力検証を行っています。

---

## 参考 / トラブルシューティング

- 環境変数が見つからない等の ValueError が発生した場合は `.env.example` を参考に `.env` を作成してください（プロジェクトルートに配置）。
- OpenAI のレスポンスに依存する処理は、APIキー・呼び出し回数制限に注意してください。news_nlp と regime_detector は JSON Mode（厳密な JSON 出力）を期待していますが、パース失敗時はログに警告を出しスコアをフォールバックします。
- J-Quants API のレート制限（120 req/min）は内部でスロットリングされていますが、大量取得時は処理時間がかかります。

---

README は以上です。実行例や追加の環境設定（CI / デプロイ / systemd サービス化等）が必要であれば、用途に応じたセクションを追加して作成します。どの部分を詳しく書くか指定してください。