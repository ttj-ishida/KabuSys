# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。J-Quants や RSS、OpenAI を活用したデータ取得・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・ETL パイプライン・監査ログなどを提供します。

## 主な特徴
- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得（ページネーション・レート制御・自動トークンリフレッシュ）
- DuckDB を用いたデータ保存（冪等保存：ON CONFLICT DO UPDATE）
- ニュース収集（RSS） → 前処理 → raw_news 保存、銘柄紐付け
- OpenAI (gpt-4o-mini) によるニュースセンチメント（銘柄別）およびマクロセンチメント評価（JSON Mode）
- 市場レジーム判定（ETF 1321 の 200 日 MA とマクロセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility）と特徴量探索（将来リターン・IC・統計サマリ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events, order_requests, executions）の初期化ユーティリティ
- 環境変数／.env 自動読み込み（プロジェクトルート探索、.env.local が .env を上書き）

---

## 機能一覧（概要）
- data/
  - jquants_client: J-Quants からの取得／保存、認証、レート制御、ページネーション、保存用ユーティリティ
  - news_collector: RSS フィード取得・前処理・SSRF 対策・raw_news 保存
  - pipeline / etl: 日次 ETL（calendar, prices, financials）と ETLResult
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day・calendar 更新ジョブ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore 正規化など統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを LLM で評価し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせて市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み・Settings（必須変数のラップ）

---

## 要件（推奨）
- Python 3.10+
- 主要依存（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API・RSS・OpenAI）
- DuckDB をファイルまたは :memory: で利用可能な環境

（実際の requirements.txt はリポジトリに合わせて作成してください）

---

## インストール例
ローカル開発用の一般的な手順例です。

1. 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate

2. 依存インストール（例）
   pip install duckdb openai defusedxml

3. パッケージを編集可能モードでインストール（開発時）
   pip install -e .

---

## 環境変数（必須 / 任意）
このライブラリは環境変数から設定を取得します。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（.git または pyproject.toml を基準にプロジェクトルートを探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な設定項目:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注などに必要）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
- 任意（デフォルト値あり）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OpenAI
  - OPENAI_API_KEY: OpenAI 呼び出しで使用（score_news / score_regime では引数で上書き可能）

例（.env）
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
OPENAI_API_KEY=sk-xxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（簡易）
1. 環境変数を設定（.env をプロジェクトルートに配置）
2. DuckDB データベースファイル作成（任意）
   - デフォルトでは data/kabusys.duckdb を使用します。初回はスキーマ初期化関数を実行する実装に応じてスキーマを作成してください（本リポジトリに schema 初期化用ユーティリティがある想定）。
3. 監査ログ用 DB を初期化する例:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # :memory: も可

---

## 使い方（代表的な利用例）

- DuckDB 接続と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って監査ログに書き込める
  ```

- ファクター計算（研究用途、DB の prices_daily / raw_financials を参照）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- score_news / score_regime は OpenAI 呼び出しを行います。テスト時は api_key を None にするか、内部の _call_openai_api をモックして差し替えてください。
- 関数群はルックアヘッドバイアス対策のため date.today() を直接参照しない設計です。target_date を明示して使ってください。
- DuckDB の executemany は空リストを受け取れないバージョンがあるため、内部実装は空チェックを行っています。

---

## ディレクトリ構成（要約）
以下は主要なモジュールと役割です（src/kabusys 配下）。

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - Settings クラス：環境変数読み込み・検証、.env 自動読み込みロジック、必須キー検査

- ai/
  - news_nlp.py: ニュースを LLM でバッチ評価し ai_scores に保存する
  - regime_detector.py: ETF 1321 の MA とマクロニュース（LLM）を合成して market_regime を算出

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py / etl.py: ETL パイプライン、run_daily_etl 等
  - calendar_management.py: 市場カレンダーの管理、営業日判定ユーティリティ
  - news_collector.py: RSS 取得・前処理・SSRF 対策・raw_news 保存ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログテーブル定義と初期化ユーティリティ
  - stats.py: zscore_normalize 等の共通統計ユーティリティ

- research/
  - factor_research.py: Momentum / Value / Volatility ファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ、ランク関数
  - __init__.py: 研究用 API の再エクスポート

---

## 開発・テストに関する注意
- ネットワーク依存（OpenAI / J-Quants / RSS）。ユニットテストでは外部呼び出しをモックしてください（例: _call_openai_api, kabusys.data.news_collector._urlopen, jquants_client._request など）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に依存します。CI 等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを無効にするとテストが安定します。
- DuckDB のバージョン差異（executemany の挙動など）に注意。ライブラリ内では既知の互換性対応が実装されています。

---

## ライセンス・貢献
本リポジトリのライセンス情報やコントリビュート手順はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、具体的な .env.example、requirements.txt、初期スキーマ作成スクリプト例なども作成します。どの形式で出力するか（日本語 / 英語、短縮版 / 詳細版）を教えてください。