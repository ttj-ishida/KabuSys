# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・AI評価・監査ログ・ETL 等を備えた自動売買・研究プラットフォームのコアライブラリです。本リポジトリは以下の主要機能群を提供します。

- データ取得・ETL（J-Quants 連携、DuckDB 保存、品質チェック）
- ニュース収集 & NLP（OpenAI を用いたニュースセンチメント）
- 市場レジーム判定（ETF ベース＋マクロニュースによる判定）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル→発注→約定をトレースする監査スキーマ）
- マーケットカレンダー管理（JPX カレンダーの保存 / 営業日計算）
- 実行環境設定（.env 自動読み込み / 環境変数経由）

対象ユーザー: データエンジニア・クオンツリサーチャー・自動売買システム開発者

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（トークン管理、ページネーション、保存用関数）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS 取得・前処理・raw_news 保存、SSRF 対策・gzip 制限）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査テーブル DDL / index 作成・init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 乖離 + マクロセンチメントの合成）
  - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定、リトライ／フォールバック処理あり
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数管理（.env / .env.local の自動読み込み、Settings クラス）
  - 必要な環境変数の検証ロジック（例: JQUANTS_REFRESH_TOKEN 等）

---

## セットアップ手順

前提: Python 3.10+（型アノテーションや union 型を利用）を推奨します。

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な追加パッケージ（主なもの）
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env を用意する

   必須（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（プロジェクトで Slack を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を別途実装する場合）

   任意 / デフォルトあり:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を呼ぶ場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト data/monitoring.db）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

   .env 自動読み込みの振る舞い:
   - 自動ロード順: OS 環境変数 > .env.local > .env
   - .env ファイルはプロジェクトルート（.git もしくは pyproject.toml のある親）から探索
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定すると自動読み込みを無効化できます（テスト時など）

4. DuckDB 初期化（監査用）
   - 監査テーブルを初期化する関数が提供されています（init_audit_db）。親ディレクトリがなければ自動作成されます。

---

## 基本的な使い方（例）

以下は Python REPL / スクリプト内でのサンプル利用例です。

- 共通: settings の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env, settings.log_level)
  ```

- DuckDB 接続を開いて ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written codes:", written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY
  ```

- 監査 DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit_kabusys.duckdb")
  ```

- カレンダー操作
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect(str(settings.duckdb_path))
  d = date(2026, 3, 20)
  print("is trading:", is_trading_day(conn, d))
  print("next trading:", next_trading_day(conn, d))
  ```

注意:
- score_news / score_regime は OpenAI API を利用するため、OPENAI_API_KEY の設定または api_key 引数の指定が必要です。
- データ取得系（ETL）では J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。
- 実際の発注（kabuステーション連携）や Slack 通知の利用は別モジュールや運用スクリプトで行います（本コードベースの一部は設定 / クライアントを用意しています）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須 for ETL)
- KABU_API_PASSWORD (必須 if kabu API を使う場合)
- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 if Slack 通知を使う)
- SLACK_CHANNEL_ID (必須 if Slack 通知を使う)
- OPENAI_API_KEY (必須 for AI スコアリング：score_news / score_regime)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動 .env 読み込みを無効化）

---

## ディレクトリ構成

リポジトリの主なファイル/ディレクトリは次のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースセンチメント解析（score_news）
    - regime_detector.py  # レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント & 保存ロジック
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - etl.py              # ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py            # 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
  - monitoring/ (存在する場合、監視関連モジュール)
  - execution/ (発注・約定関連の実装（将来的に）)
  - strategy/ (戦略実装用モジュール)

この README は上記コードベースの主要モジュールを要約したものです。各モジュールの詳細な API/引数/戻り値はソースコードの docstring を参照してください。

---

## 運用上の注意・ベストプラクティス

- Look-ahead bias 回避: 多くの関数は date 引数を明示的に受け取り、内部で date.today() 等を参照しない実装方針です。バックテストや過去日検証では target_date を明示してください。
- OpenAI / J-Quants の API コストとレート制限に注意してください（モジュール内でリトライやレートリミッタを備えていますが、運用ポリシーは別途定めてください）。
- DuckDB に対する複数プロセス同時書き込み等は注意が必要です。運用環境では排他制御を考慮してください。
- .env には機密情報（API トークン等）を直書きしないか、アクセス管理に注意してください。
- production（ライブ）環境での発注は十分なテストを経て実行してください（KABUSYS_ENV を適切に設定）。

---

必要であれば README に「発注（kabu）連携」「Slack 通知」「デプロイ手順（cron / Airflow / GitHub Actions）」などの運用ガイドを追加します。どの項目を優先的に追加しますか？