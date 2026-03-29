# KabuSys

KabuSys は日本株を対象とした自動売買 / データプラットフォームのライブラリです。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、特徴量計算、ETL パイプライン、監査ログ等を含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- DuckDB を中核データストアとして利用（冪等保存・トランザクション考慮）
- 外部 API 呼び出しに対してはリトライ・レート制御・フォールバックを備える
- 監査ログでシグナル→発注→約定のトレーサビリティを確保

---

## 機能一覧

- 環境設定管理（自動的にプロジェクトルートの `.env` / `.env.local` を読み込む）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得・DuckDB 保存（冪等）
  - レートリミット / リトライ / トークン自動更新
- ETL パイプライン（run_daily_etl）
  - カレンダー、株価、財務データの差分取得と品質チェック（quality モジュール）
- ニュース収集（RSS）と前処理（SSRF防止・トラッキング除去等）
- ニュース NLP（OpenAI）による銘柄別センチメント算出（ai.score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）（ai.score_regime）
- 研究用モジュール（factor 計算、forward returns、IC、zscore 正規化 など）
- 監査ログ（audit）モジュール：signal / order_request / executions テーブルの初期化とユーティリティ

---

## 要件

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外が必要な場合は pyproject / requirements に従ってください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローンしてセットアップ
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"   # または pip install -e .
   ```

2. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN=...      （J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD=...         （kabuステーション API パスワード）
   - OPENAI_API_KEY=...            （OpenAI API キー。score_news/score_regime で使用）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb   （省略時のデフォルト）
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=INFO|DEBUG|...                （デフォルト: INFO）

   注意: Settings は必須項目を取得するときに未設定だと例外を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## 使い方（主な例）

以下はライブラリを直接インポートして利用する例です。実行する前に必要な環境変数を設定してください。

- DuckDB 接続を作る（デフォルトファイルは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を None にすると本日がデフォルト（内部で調整あり）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア算出（ai）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定済みであること
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ai）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル（signal_events, order_requests, executions 等）が作成されます
  ```

- ニュース RSS 取得（単体）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

注意点：
- OpenAI 呼び出しはレスポンス検証・リトライを行いますが、APIキーが未設定だと ValueError を投げます。
- ETL 関数は内部でトランザクション管理やロールバックを行いますが、呼び出し側での適切な例外処理を推奨します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要モジュールです。ドキュメント生成やソースリファレンス用の簡易ツリーを示します。

- src/kabusys/
  - __init__.py
  - config.py                            — 環境設定・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py                         — ニュース NLP（score_news）
    - regime_detector.py                  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py              — 市場カレンダー管理（is_trading_day 等）
    - etl.py                              — ETL 公開インターフェース（ETLResult）
    - pipeline.py                         — ETL パイプライン（run_daily_etl 他）
    - stats.py                            — 統計ユーティリティ（zscore_normalize）
    - quality.py                          — データ品質チェック
    - audit.py                            — 監査ログ初期化・ユーティリティ
    - jquants_client.py                   — J-Quants API クライアント（取得/保存）
    - news_collector.py                   — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py                  — ファクター計算（momentum/volatility/value）
    - feature_exploration.py              — forward return / IC / summary

---

## 設計上の注意とベストプラクティス

- ルックアヘッドバイアス防止：
  - ai / research / data の多くの処理は target_date を引数に取り、内部で現在時刻を参照しない実装を心がけています。バックテストや過去検証でこの点に注意して使用してください。
- 冪等性：
  - J-Quants データ保存関数は ON CONFLICT を用いて冪等に保存します。ETL の再実行や部分失敗への耐性があります。
- 外部 API 呼び出し：
  - OpenAI / J-Quants 呼び出しにはリトライやレート制御、フォールバック（失敗時のデフォルト値）を実装していますが、APIキーや課金制約には注意してください。
- セキュリティ：
  - news_collector は SSRF 対策、XML 脆弱性防止（defusedxml）、受信サイズ制限などを実装しています。

---

## よくある質問 / トラブルシュート

- .env が読み込まれない  
  - パッケージはプロジェクトルート（.git や pyproject.toml を基準）を探索して .env を自動ロードします。テストなどで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI のレスポンスが不正（JSON parse error）  
  - モジュールはパース失敗時にフォールバック（スコア=0 など）する設計です。ログを確認してプロンプト・モデル・APIの安定性を調査してください。
- DuckDB スキーマが未作成でエラーになる  
  - ETL や audit の初期化関数を呼んでスキーマを作成してください（audit なら init_audit_db）。ETL は通常スキーマを期待します。

---

もし README に追加したい「使い方の CLI 化」「サンプル .env.example」「テスト実行方法」などの要望があれば教えてください。必要に応じて具体的なコマンド例やテンプレートファイルを追記します。