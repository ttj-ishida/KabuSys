# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）

軽量なデータパイプライン（J-Quants 経由の株価・財務・カレンダー取得）、ニュース NLP、AI を使ったスコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）などを提供する内部ライブラリです。DuckDB を利用したローカルデータベースを想定しています。

---

## プロジェクト概要

KabuSys は日本株自動売買やリサーチ用途向けのモジュール群をまとめたパッケージです。主な目的は以下です。

- J-Quants API からのデータ取得（株価、財務、カレンダーなど）
- ETL（差分取得・保存）パイプライン
- ニュース収集・NLP による銘柄別センチメント算出（OpenAI）
- マーケットレジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量解析（リサーチ用）
- データ品質チェック
- 発注〜約定までをトレースする監査ログテーブル定義 / 初期化

設計上、ルックアヘッドバイアス回避や冪等性、堅牢なエラーハンドリングに配慮しています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（営業日判定・次／前営業日取得・calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル定義・初期化）
  - 統計ユーティリティ（zscore_normalize）

- ai
  - ニュース NLP（銘柄別センチメント算出: score_news）
  - レジーム判定（ETF 1321 の MA200 乖離とマクロニュースを合成: score_regime）
  - OpenAI との安全な呼び出し・リトライロジックを備える

- research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary, rank）

- config
  - .env / 環境変数読み込み（プロジェクトルート検出、自動ロード・優先順位制御）

---

## セットアップ手順

前提: Python 3.9+（型ヒントに Union | を使用しているため少なくとも 3.10 推奨）

1. リポジトリをクローンし、開発環境を作る
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 必要な主要パッケージ（抜粋）:
     - duckdb
     - openai
     - defusedxml
   - pip 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージ化されている場合:
     ```
     pip install -e .
     ```

3. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  # ai モジュールを使う場合必須
   - 任意 / デフォルト可能:
     - KABUSYS_ENV=development|paper_trading|live (default: development)
     - LOG_LEVEL=INFO|DEBUG|...
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

4. データベースの親ディレクトリ作成
   - DuckDB 用のパスの親ディレクトリを作成しておく（init 関数でも自動作成あり）。
     ```
     mkdir -p data
     ```

---

## 使い方（代表的な呼び出し例）

以下は Python スクリプトや REPL からの利用例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作る（例: settings を使う）
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを生成する（OpenAI API キーが必要）
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- マーケットレジーム判定を実行する
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する（専用ファイル）
  ```py
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit_duckdb.db")
  ```

- 設定値の参照（例）
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- AI 関連関数は OpenAI の gpt-4o-mini を利用する想定で実装されています。API 呼び出しはリトライやフォールバック（失敗時は中立スコア）を実装していますが、API コスト・レート制限に注意してください。
- ほとんどの処理は DuckDB 接続を引数で受け取り、SQL/Window 関数で効率的に集計します。バックテストや本番のループ内でのルックアヘッドを防ぐ実装方針が適用されています（target_date 未満や target_date の取り扱いに注意）。

---

## 設定（.env）サンプル

以下は必須と思われる設定の例（ファイル名: .env）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
#KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack（通知等に使用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェルライクな書式（export プレフィックス、クォート、インラインコメント処理等）に対応しています。自動ロードはプロジェクトルート検出に基づいて行われます。

---

## ディレクトリ構成 (抜粋)

実際のツリーは src 以下に配置されています。代表的な構成:

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
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在する場合)
  - strategy/ (存在する場合)
  - execution/ (存在する場合)

各ファイルはモジュール単位で責務が分離されています（データ取得 / ETL / NLP / リサーチ / 監査ログなど）。

---

## 注意事項・設計上のポイント

- ルックアヘッドバイアス回避:
  - 多くの関数は datetime.today() / date.today() を内部で参照せず、target_date を明示的に受け取る設計です。バックテストでの利用時は target_date を必ず指定してください。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT DO UPDATE / INSERT … ON CONFLICT などで冪等に行われます。
- セキュリティ:
  - RSS 収集では SSRF 対策（リダイレクト先の検証、プライベートアドレス拒否）や XML 攻撃対策（defusedxml）を実装しています。
- フェイルセーフ:
  - AI 呼び出し失敗時は中立スコア（0.0）やスキップによる継続等、致命的停止を避ける動作が多くの箇所で採用されています。

---

## 開発・デバッグのヒント

- 環境変数の自動ロードはプロジェクトルート検出に依存するため、プロジェクトルートで作業してください。
- 自動ロードを無効にしてユニットテストを実行したい場合は、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI への呼び出しは各モジュール内で差し替え可能なヘルパー関数（_call_openai_api 等）を用意しているため、テスト時にモックしやすくなっています。

---

もし README に追加したい具体的な使用例（cron ジョブ設定、Slack 通知フロー、バックテストとの連携例など）があれば教えてください。用途に合わせてサンプルや運用手順を追記します。