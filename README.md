# KabuSys — 日本株自動売買システム（README）

本ドキュメントはリポジトリ内のコードベースに基づき、プロジェクト概要、機能、セットアップ手順、基本的な使い方、およびディレクトリ構成を日本語でまとめた README です。

注意: 実際に稼働させるには各種 API キー（J-Quants / OpenAI / kabuステーション / Slack 等）が必要です。まずはローカル環境で動作確認し、十分な理解の上で実運用してください。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買の基盤を提供する Python パッケージです。J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）、ニュース収集／NLP による銘柄センチメント評価、ファクター計算・リサーチ、監査ログ（オーダー・約定のトレーサビリティ）など、バックテスト／実運用に必要な基盤機能群を含みます。

設計上の要点:
- Look-ahead bias を避ける（日時の扱いに注意）
- DuckDB を用いたローカルデータベース中心の処理
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（オプション）
- J-Quants API の取得・保存は冪等・リトライ・レート制御を備える

---

## 主な機能一覧

- 環境設定管理（.env 自動読込、必須設定チェック）
- J-Quants クライアント
  - 株価日足（OHLCV）取得・保存（fetch / save）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・リトライ・トークン自動更新
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル対応
  - ETLResult による結果集約
- データ品質チェック
  - 欠損、スパイク、重複、日付整合性チェック
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、サイズ制限、冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを統合して ai_scores へ書込
  - レート制限 / リトライ / バッチ処理
- 市場レジーム検出（ETF + マクロニュース + LLM）
  - ma200 と マクロセンチメントの重み合成でレジーム判定
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL・初期化
  - 監査用 DuckDB DB 初期化ユーティリティ
- 研究用ユーティリティ（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン、IC、統計サマリー、Zスコア正規化

---

## 要求環境（推奨）

- Python 3.10+（型アノテーションに基づく互換性）
- パッケージ（主なランタイム依存）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで賄われている部分も多いですが、OpenAI や DuckDB は個別に必要です。

requirements.txt がない場合は手動でインストールしてください。例:
pip install duckdb openai defusedxml

（プロジェクト固有の追加依存があれば別途 requirements を用意してください）

---

## 環境変数（主要）

KabuSys は .env / .env.local もしくは OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git もしくは pyproject.toml を探す）基準で行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（README 用の代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル・開発向け）

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository-root>

2. Python 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージのインストール
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトでパッケージ化されている場合）
   pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env を作成（上記の例を参照）
   - または必要な環境変数をシェルに設定する

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

6. DuckDB 初期化（任意）
   Python からテーブル作成用のスクリプトやマイグレーションを用意している場合は実行してください。
   例: 監査ログ用 DB 初期化（簡易）
     python - <<'PY'
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db('data/audit.duckdb')
     print('audit DB initialized')
     PY`

---

## 使い方（例）

以下は最小限の使用例です。実行前に DuckDB パスや API キー等の設定が正しいことを確認してください。

- 日次 ETL を実行する（Python スクリプトから）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントをスコア化（ai_scores テーブルへ書き込み）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {n_written}")

- 市場レジームのスコア計算:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API key は環境変数 OPENAI_API_KEY を参照

- 監査ログ用 DB を初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- Zスコア正規化ユーティリティ:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

注意点:
- OpenAI 呼び出しは API 呼出しにコストがかかります。API キーの管理・利用量に注意してください。
- ETL / API 呼び出しはネットワークや API の利用制限に依存します。ログを確認しながら実行してください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理（.env 自動ロード、settings）
- ai/
  - __init__.py                  — score_news のエクスポート
  - news_nlp.py                  — ニュース NLP（OpenAI）／score_news
  - regime_detector.py           — 市場レジーム判定（ETF MA + マクロ NLP）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch / save / auth）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 他）
  - etl.py                       — ETLResult を公開
  - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - quality.py                   — データ品質チェック
  - news_collector.py            — RSS ニュース収集（SSRF 対策等）
  - audit.py                     — 監査ログ（テーブル DDL / 初期化）
- research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum/value/volatility）
  - feature_exploration.py       — 将来リターン・IC・統計サマリー等

（上記以外に strategy / execution / monitoring 等のモジュールも想定されていますが、本 README は現行コードベースの主要部分に基づいています）

---

## 運用上の注意／設計意図（抜粋）

- Look-ahead bias を避けるため、モジュールの多くは datetime.today() / date.today() を直接参照しない設計になっています。ETL やスコア計算は明示的な target_date を受け取ります。
- J-Quants クライアントはレート制限（120 req/min）を守るための RateLimiter と、リトライ／トークン自動リフレッシュを実装しています。
- ニュース収集では SSRF 対策、サイズ制限、XML の安全パース（defusedxml）等に配慮しています。
- OpenAI 呼び出しはリトライとバックオフ処理を実装し、失敗時はフェイルセーフ（スコア 0.0 など）で継続するよう設計されています。
- audit（監査ログ）は冪等で初期化可能。order_request_id を冪等キーとして二重発注を防止する設計になっています。

---

## よくある質問（Q&A）

Q: .env はどこに置けば良いですか？
A: プロジェクトルート（.git または pyproject.toml があるディレクトリ）に置いてください。.env と .env.local が読み込まれます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI を使いたくない場合は？
A: NEWS NLP / regime 判定など OpenAI に依存する機能は API キーがないとスキップまたはエラーになります。API を使わないワークフローに切り替えるか、モック実行を用いてテストしてください。

Q: DuckDB の初期スキーマはどこで作成しますか？
A: 実際のスキーマ作成用ユーティリティ（schema init）を用意している場合はそちらを使ってください。audit.init_audit_db は監査ログ専用の初期化を行います。raw_prices などのテーブルは ETL やスキーマ初期化スクリプトで作成してください。

---

## 貢献・拡張

- 新しいデータソースや戦略（strategy）を追加する際は、Look-ahead bias に注意してください（target_date を明示的に渡す設計を推奨）。
- テストを書く際は、外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックしてユニットテストを行ってください。コード内ではテスト容易性のため一部関数（_call_openai_api、_urlopen 等）を差し替え可能にしています。
- 実運用では paper_trading / live 環境の分離、注文冪等性、監査ログの厳密管理を徹底してください。

---

以上がコードベースに基づく README の概要です。必要であれば、実行例やスキーマ初期化スクリプト、requirements.txt、Dockerfile、CI 設定などの追加ドキュメントを作成します。どの部分を詳しく書くか指示をください。