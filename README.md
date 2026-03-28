# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP、LLM を用いた市場レジーム判定、ファクター計算、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムの基盤コンポーネント群をまとめた Python パッケージです。  
主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務、カレンダー）
- DuckDB を用いた日次 ETL パイプライン（差分取得・保存・品質チェック）
- RSS ニュース収集とニュースセンチメント（OpenAI）による銘柄単位スコア化
- ETF とマクロニュースを組み合わせた市場レジーム判定（LLM）
- ファクター算出・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ
- 環境設定管理（.env 自動ロード・保護）

設計上、バックテストでのルックアヘッドバイアスを避けるよう細心の注意が払われています（多くのモジュールで現在時刻を直接参照しない等）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline / etl: 日次 ETL（差分取得、保存、品質チェック）
  - news_collector: RSS 取得 → raw_news 保存（SSRF・サイズ制限・正規化）
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ（シグナル / 発注 / 約定）スキーマ作成・初期化
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを計算し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュース（LLM）を合成して market_regime を更新
- research/
  - factor_research: モメンタム、バリュー、ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、要約統計等
- config: 環境変数 / .env 自動ロード / 設定アクセス（settings オブジェクト）

---

## 必要条件

- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

※実行環境に応じて追加パッケージ（例: requests 等）が必要になりうるため、プロジェクトの requirements.txt を用意している場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   例（pip）:

   ```
   pip install duckdb openai defusedxml
   ```

   ※実運用では依存ロックファイルや requirements.txt を用意して pip install -r でインストールしてください。

4. 環境変数の設定

   プロジェクトルートに `.env` を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（本パッケージで参照される主なキー）:

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系統向け）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
   - KABUSYS_ENV: 環境（development / paper_trading / live）※デフォルト development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH: DuckDB 保存パス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）

   .env の簡易例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な例）

以下はパッケージ API を直接インポートして使う例です。実行はプロジェクトルートの Python コンソールや簡単なスクリプトから行えます。

- DuckDB 接続と ETL 実行（日次 ETL）

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）

  news_nlp.score_news は raw_news / news_symbols / ai_scores テーブルを参照します。例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date に対するウィンドウ（前日15:00 JST ～ 当日08:30 JST）の記事をスコアリング
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB 初期化

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 研究用 API（ファクター計算・IC 計算）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

注:
- ai モジュールは OpenAI API を呼び出します。API キーは `OPENAI_API_KEY` 環境変数、または関数引数 `api_key` で指定します。
- 多くの処理は DuckDB のスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar など）に依存します。実行前にスキーマを初期化しておく必要があります（スキーマ初期化ユーティリティは別途用意されている前提です）。

---

## 重要な挙動・設計上の注意点

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護されます。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト等で使用）。

- Look-ahead バイアス防止:
  - 多くの処理（ニュースウィンドウ計算、MA 計算、ETL 等）は未来情報を参照しないように実装されています。バックテスト/研究用途ではこの点に留意してください。

- フェイルセーフ:
  - LLM や外部 API が失敗した場合でもシステム全体が落ちないよう、適切にフォールバック（例: マクロスコアが取れない場合は 0.0）する設計です。ただし、結果の信頼性は低下します。

- レート制限とリトライ:
  - J-Quants クライアントはレート制御とリトライロジックを備えています。OpenAI 呼び出しもリトライを行います（設定済み）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルート / src/kabusys を基準）

- src/kabusys/
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
    - etl.py (re-export)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema init 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (公開 API に含まれる可能性あり)
  - strategy/, execution/ (パッケージエクスポートに含まれる旨の参照あり)

ファイルごとにモジュール説明や設計方針が豊富にコメントで記載されています。各モジュールのトップコメントを参照してください。

---

## 開発・運用のヒント

- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。運用環境ではバックアップやパーミッションに注意してください。
- OpenAI の出力は JSON mode を利用して厳密な JSON を期待するよう設計されていますが、レスポンスの前後に余計なテキストが混ざる場合に備えた復元ロジックがあります。
- news_collector は SSRF 対策・gzip サイズチェック・トラッキングパラメータ除去等の堅牢性対策を行っています。RSS ソース追加時は DEFAULT_RSS_SOURCES を編集してください。
- schema（テーブル定義）やマイグレーションは本 README に含めていません。初期スキーマ作成用ユーティリティ（data.schema.init_schema 等）を利用してください。

---

## ライセンス・貢献

（このリポジトリのライセンスと貢献ガイドラインをここに記載してください）

---

必要であれば、具体的な実行例（ETL フロー、news_nlp の詳細なパラメータ、unit test の例など）やスキーマ定義の README 追加を作成します。どの部分の詳細が欲しいか教えてください。