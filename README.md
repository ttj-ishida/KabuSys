# KabuSys

KabuSys は日本株のデータパイプライン、ニュースNLP、市場レジーム判定、リサーチ用ファクター計算、監査ログ等を備えた自動売買／研究プラットフォームのコアライブラリです。本リポジトリは主に DuckDB を用いたデータ管理、J-Quants API 経由のデータ取得、OpenAI を用いたニュースセンチメント評価などを含みます。

主な目的は「データ取得（ETL）→ 品質チェック → ニュースからのAIスコアリング → ファクター算出 → 戦略／発注実行（監査付き）」というワークフローのための基盤機能を提供することです。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須設定に対する検証
- データ ETL（J-Quants 経由）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - ETL 実行結果（ETLResult）と品質チェックの統合
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS フィード収集（SSRF 対策、サイズ制限、URL 正規化、トラッキング除去）
  - raw_news / news_symbols への冪等保存設計
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合してセンチメント（ai_scores）を算出・保存（batch + JSON mode）
  - マクロ記事を用いた市場センチメント算出（regime_detector）
  - API 呼び出し時のリトライ・フォールバック設計
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター算出（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリ
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブルの DDL と初期化ユーティリティ
  - UUID によるトレーサビリティ、トランザクション対応

---

## セットアップ手順

前提:
- Python 3.10+（typing の union などを使用）を推奨
- DuckDB を使用するためネイティブライブラリが必要（pip でインストールされます）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - ここでは代表的な依存を記載します（プロジェクトの requirements.txt / pyproject.toml があればそちらを参照してください）
   ```
   pip install duckdb openai defusedxml
   ```
   - その他、システムに応じて追加パッケージ（例: slack SDK）を入れてください。

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 自動ロードはデフォルトで有効です。テスト時に無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例（.env.example）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu ステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # Slack (通知等で使用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベースパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的なサンプル）

以下はライブラリ関数を直接利用する方法の例です。実運用ではジョブスケジューラ（cron, Airflow 等）やエントリポイントスクリプトを用いて定期実行します。

- DuckDB 接続の作成例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しないと今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査データベース初期化（監査ログ用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 返り値は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
  ```

注意:
- OpenAI API を呼ぶ機能は `OPENAI_API_KEY` を環境変数で渡すか、各関数の `api_key` 引数で明示的に指定してください。
- J-Quants API 呼び出しはレートリミット（120 req/min）やトークン期限切れ対策を内包していますが、ID トークン（リフレッシュトークン）を `.env` に設定する必要があります。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID

推奨 / 任意:
- OPENAI_API_KEY : OpenAI API キー（ニュースNLP / レジーム判定で必要）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : データ保存用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development | paper_trading | live）
- LOG_LEVEL : ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を自動ロードします。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（銘柄別スコアリング）
    - regime_detector.py          — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py      — 市場カレンダー管理（営業日判定等）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py           — J-Quants API クライアント（fetch/save）
    - news_collector.py           — RSS ニュース収集（SSRF 対策等）
    - quality.py                  — 品質チェック（欠損/重複/スパイク/日付不整合）
    - stats.py                    — 統計ユーティリティ（Zスコア等）
    - audit.py                    — 監査ログスキーマ定義 / 初期化
    - pipeline.py                 — ETL の実行ロジック & ETLResult
    - etl.py                      — ETLResult の再エクスポート（軽ラッパー）
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Value/Volatility 等の計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリ
  - ai/, data/, research/の他に strategy/, execution/, monitoring/ 用の名前空間が使える設計（__all__ に登録）

（実際のファイルは src/kabusys 以下にまとまっています。上記は主要モジュールの説明です。）

---

## 運用上の注意

- Look-ahead バイアス回避:
  - 各モジュールは基本的に date / target_date を明示して扱います。内部で datetime.today() による参照を避ける設計がされている箇所が多く、バックテストでの利用に配慮されています。
- フォールバック / フェイルセーフ:
  - ニュース・レジーム判定や OpenAI 呼び出しで失敗した場合、スコアをゼロにフォールバックするなど安全側に倒す実装がされています（例: macro_sentiment=0.0）。
- J-Quants レート/認証:
  - get_id_token() はリフレッシュトークンから ID トークンを取得します。HTTP 401 時の自動リフレッシュや 429/5xx への再試行ロジックを備えています。
- セキュリティ:
  - RSS 取得では SSRF 対策（リダイレクト検査、プライベートIPブロックなど）や XML の defusedxml を使用して安全化しています。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが検出できない場合、自動ロードはスキップされます（プロジェクトルートは __file__ の親を .git または pyproject.toml を基準に探索）。手動で環境変数をエクスポートするか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを止め、明示的にロードしてください。
- OpenAI レスポンスのパースエラー
  - 返却が厳密 JSON でない場合や予期しない形式のとき、ログに警告を出してスコアをスキップ/ゼロにします。テスト時は内部の _call_openai_api をモックすると良いです。
- DuckDB の executemany に関する注意
  - DuckDB のバージョンによっては executemany に空リストを渡すとエラーになるため、ライブラリ内では空リストチェックを行っています。

---

## 貢献・拡張

- 新しい ETL ソース（別 API）を追加する場合は `kabusys.data.jquants_client` と同等の fetch/save インターフェースを実装し、pipeline に組み込んでください。
- 監査ログスキーマは冪等で初期化できるので、新しいイベント型を追加する際も既存テーブルとの整合を考慮して DDL を拡張してください。
- テスト: 各モジュールは外部依存（ネットワーク・OpenAI・J-Quants）を分離しやすい設計になっています。ユニットテストでは HTTP 呼び出しや OpenAI クライアントをモックしてください。

---

必要であれば README にサンプルスクリプト（cron 用のラッパー、Dockerfile、systemd unit など）や、詳細な API ドキュメント（関数一覧、戻り値の構造）を追加します。どの情報を優先して追加するか教えてください。