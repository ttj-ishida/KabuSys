# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータ取得・ETL・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ管理を含む、アルゴリズム取引プラットフォーム向けライブラリ群です。本リポジトリはバックテスト/リサーチ用のデータ処理パイプラインと、運用時に利用する監査・発注周りの基盤処理を提供します。

主な設計方針：
- Look-ahead バイアス回避（内部で date.today()/datetime.now() を不用意に参照しない）
- DuckDB をデータ層に利用（SQL + Python）
- J-Quants / OpenAI 等の外部 API 呼び出しはレート制御・リトライ・フェイルセーフ実装
- 冪等性（ON CONFLICT / idempotent な保存）と監査トレースを重視
- セキュリティ配慮（RSS の SSRF 対策、defusedxml 利用など）

---

## 機能一覧

- データ収集 / ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄情報、JPX カレンダー）
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
  - RSS ベースのニュース収集（前処理・トラッキングパラメータ除去・SSRF 対策）
- データ品質チェック
  - 欠損、重複、未来日付、スパイク検出などのチェック
- AI（OpenAI）を使った NLP
  - ニュース記事から銘柄別センチメントを算出（news_nlp）
  - マクロニュース + ETF MA 乖離を合成して市場レジーム判定（regime_detector）
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
  - 監査用 DuckDB 初期化関数
- ユーティリティ
  - 環境設定管理（settings）、Z スコア正規化など汎用ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+ を推奨（PEP 604 のユニオン演算子などを使用）
- システムにネットワークアクセスが必要（J-Quants / OpenAI など）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール
   このコードベースで利用する主な外部依存は以下です（プロジェクトに requirements.txt があればそちらを使用してください）。
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクト配布パッケージがある場合
   pip install -e .
   ```

4. 環境変数の設定
   .env（あるいはシステム環境変数）で下記を設定してください。プロジェクトルートに `.env` / `.env.local` があると自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須（ライブラリの主要機能を使う場合）：
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API 用パスワード（発注周り）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — 通知対象チャンネル ID
   - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

   任意 / デフォルトあり：
   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（値を1に）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下は最小限の利用例です。多くの関数は DuckDB コネクションを引数に取ります。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成される
  ```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可能
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored codes:", count)
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定される
  ```

- News RSS 取得（news_collector のユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点
- OpenAI や J-Quants を呼び出す関数は API キー（または refresh token）の設定が必須です。テスト時は API 呼び出し部分をモックできます（コード内に patch で差し替え可能な内部関数が用意されています）。
- ETL / 保存処理は冪等性を考慮して実装されています（ON CONFLICT 等）。

---

## 設計・実装上の主なポイント（抜粋）

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。
- J-Quants クライアントは固定間隔スロットリング（120 req/min）とリトライ（指数バックオフ）を実装しています。401 はリフレッシュトークンで自動的に再取得します。
- news_collector は SSRF 対策（リダイレクト検査、内部アドレス拒否）、Content-Length/最大受信バイト制限、defusedxml による XML パース安全化を行っています。
- news_nlp / regime_detector は OpenAI の JSON モードを使い、レスポンスのバリデーションやリトライを行います。API 失敗時はフェイルセーフとしてゼロやスキップで継続します。
- データ品質チェックは全件収集方式（Fail-Fast しない）で、呼び出し元が severity に応じて処理を判断できます。
- 監査ログ（audit）スキーマは発注フローを UUID 階層で完全トレースできるように設計されています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` 下を抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント算出（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS ベースのニュース収集（SSRF 対策）
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック群
    - audit.py              — 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py— 将来リターン / IC / サマリー 等
  - ai/*, data/*, research/* の他、strategy/, execution/, monitoring/ を公開する設計（各モジュールは __all__ 等で制御）

---

## 開発・テストについて

- 外部 API 呼び出し部分（OpenAI / J-Quants / HTTP ネットワーク）はユニットテストで差し替え（モック）可能な設計になっています。内部の API 呼び出しヘルパーをパッチすることでテスト容易性を確保しています。
- DuckDB を使うため、テストはインメモリ DB（":memory:"）や一時ファイルを使って独立して実行できます。
- .env の自動読み込みを無効にして、テスト固有の環境変数を注入することも可能です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 追加情報 / 注意事項

- 本プロジェクトは実運用の発注ロジックや実際の口座接続（kabuステーション）を含む可能性があります。実口座で運用する際は十分な検証とリスク管理を行ってください。
- API キー・トークン類は秘匿情報です。絶対に公開リポジトリやログに残さないでください。
- ライセンスや貢献方法、CI/CD 設定が別途ある場合はリポジトリルートのファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

---

もし README に含めたいサンプルスクリプト（例: ETL の cron 用 wrapper、ニュース収集のバッチ例、監査 DB 初期化スクリプト）や、requirements.txt / dev setup の追記を希望される場合は、用途（production / development / testing）を指定して教えてください。必要に応じて具体的な .env.example や systemd / cron のサンプルも作成します。