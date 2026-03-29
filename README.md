# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買の基盤ライブラリです。  
J-Quants / kabu ステーション / OpenAI を利用したデータ取得・ETL、ニュースの NLP スコアリング、ファクター計算、監査ログなどを含むモジュール群を提供します。

## 特徴（概要）
- J-Quants API 経由で株価・財務・マーケットカレンダーを差分取得・保存（DuckDB）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ判定）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- 日次 ETL パイプライン（差分取得・品質チェック・保存）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計算・Z スコア正規化）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用のスキーマ初期化ユーティリティ

---

## 機能一覧
- data:
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証・リトライ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・保存ロジック（SSRF 防止、サイズ制限）
  - calendar_management: 営業日判定・次/前営業日取得・カレンダーアップデートジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.score_regime: マクロ + MA200 による市場レジーム判定
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定:
  - config.Settings: 環境変数ベースの設定読み出し、自動 .env ロード機構

---

## 前提条件
- Python 3.10+
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は setup に合わせてインストールしてください）

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境をつくる（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. パッケージをインストール
   - setup がある場合:
     ```bash
     pip install -e .
     ```
   - 直接必要パッケージをインストールする場合（例）:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数／.env ファイルを用意  
   プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（config モジュールによる自動ロード）。  
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector の引数でも指定可能）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な操作例）

以下の例はライブラリ API の利用方法です。実行前に必要な環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの銘柄別スコアを作成する（OpenAI API 必須）
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} symbols")
  ```
  note: api_key を直接渡すことも可能（score_news(..., api_key="sk-...")）

- 市場レジーム判定を行う
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records))
  ```

- 監査ログ用 DB を初期化する（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて conn をアプリ側で使用
  ```

---

## 注意点 / 動作方針
- ルックアヘッドバイアス対策:
  - 多くのモジュールは datetime.today() の直接参照を避け、関数呼び出し側で target_date を渡す設計です。
  - prices_daily などのクエリは target_date 未満／以下の条件でルックアヘッドを防ぎます。
- フェイルセーフ:
  - OpenAI 等の外部 API が失敗してもプロセス全体を停止せずにフォールバック（例: macro_sentiment=0）する箇所があります。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE / INSERT RETURNING 相当で重複を上書きする設計です。
- セキュリティ:
  - RSS フィード取得では SSRF 対策（ホストチェック／リダイレクト検査）や XML パースに defusedxml を使用しています。
- DuckDB のバージョンや SQL の互換性に注意してください（executemany の空リスト等は考慮済み）。

---

## ディレクトリ構成（主要ファイル）
リポジトリの主要なファイル・モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄別スコア）
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL の公開型再エクスポート
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — 市場カレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー

---

## 開発 / テスト
- 自動 .env 読み込みはプロジェクトルート（.git もしくは pyproject.toml を基準）を探索して行われます。テスト中に自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し等はユニットテストではモックして差し替えるよう設計されています（モジュール内部の _call_openai_api などを patch）。

---

必要であれば以下を追加で作成できます：
- .env.example（必須環境変数のテンプレート）
- 詳細な API ドキュメント（関数引数・戻り値の表）
- デプロイ / 運用手順（ETL スケジューリング、Slack 通知の設定方法 等）

ご希望があれば README に上記を追記します。