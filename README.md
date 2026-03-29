# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や RSS、OpenAI など外部データと連携して、データ収集（ETL）、品質チェック、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定、リサーチ用ファクター算出、監査ログ（order → execution のトレーサビリティ）などを提供します。

主に DuckDB をデータストアに用い、バックテスト／運用システムのデータプラットフォームおよび研究（research）用途に適したユーティリティ群をまとめています。

---

## 主な機能

- データ ETL（J-Quants API 経由）
  - 株価日足（OHLCV）、財務諸表、マーケットカレンダー等の差分取得・保存（ページネーション・リトライ・レート制御）
  - id token 自動リフレッシュ、フェイルセーフな再試行
- データ品質チェック（quality）
  - 欠損、重複、スパイク（前日比急変）、日付整合性（未来日 / 非営業日）検出
- カレンダー管理（market_calendar）
  - 営業日判定、前後営業日取得、期間内営業日取得、JPX カレンダーの夜間差分更新ジョブ
- ニュース収集（RSS）
  - RSS フィード取得、前処理、SSRF 対策、トラッキングパラメータ除去、記事ID生成（SHA-256）
- AI（LLM）関連
  - ニュース NLP（銘柄毎のセンチメントを OpenAI で評価し ai_scores に保存する処理）
  - 市場レジーム判定（ETF 1321 の MA 乖離とマクロニュースの LLM センチメントを合成）
  - OpenAI API 呼び出しは堅牢なリトライ・パース検証を実装
- 研究（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン、IC（スピアマンランク相関）、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルを用いたトレーサビリティ、監査スキーマ初期化ユーティリティ

---

## 必要条件（概略）

- Python 3.10 以上（型注釈 Path | None, | 型などを使用）
- 外部パッケージ（主に）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード）

※ 実際のプロジェクト配布では requirements.txt を用意してください。本 README では主要な依存を記載しています。

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   実運用では pip install -r requirements.txt または poetry/pipenv を使用してください。

3. 環境変数の設定
   - 環境変数または .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な必須項目（例）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xxxxx
     - SLACK_CHANNEL_ID=xxxxx
     - OPENAI_API_KEY=xxxxx
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

下例は Python REPL やスクリプトでの利用例です。すべての例は簡略化しています。実運用ではエラーハンドリングやログ設定を行ってください。

- DuckDB 接続と日次 ETL 実行

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- OpenAI を用いたニューススコアリング（news_nlp.score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で渡すか、第3引数 api_key に文字列を渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

- 市場レジーム判定（regime_detector.score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます

- ニュース RSS 取得（fetch_rss の単体利用）

  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

注意点:
- OpenAI 関連関数は api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
- 自動ロードされる環境変数の優先順位は OS 環境 > .env.local > .env です。.env.example がリポジトリにある場合はそれを参考に .env を作成してください。

---

## 設定と挙動の注記

- 自動 .env 読み込み
  - パッケージがロードされた際にプロジェクトルート（`.git` または `pyproject.toml` のある親ディレクトリ）を探索し、`.env` と `.env.local` を自動読み込みします。
  - テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings API
  - kabusys.config.settings によって設定値へアクセスできます（例: settings.jquants_refresh_token）。
  - KABUSYS_ENV は development / paper_trading / live のいずれかでなければなりません。LOG_LEVEL は標準的なログレベル文字列を受け付けます。
- OpenAI 呼び出しの安全性
  - LLM 呼び出しはリトライ・JSON バリデーションなど堅牢化されており、API 障害時はフェイルセーフ（デフォルト 0.0 など）で継続する設計です。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル・ディレクトリ構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（LLM 統合）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 取得・前処理
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py               — 統計ユーティリティ（z-score 正規化）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

各モジュールはドメイン別に分離されており、ETL・データ整備・研究・AI・監査の責務が明確に分かれています。

---

## 開発・テストのヒント

- 自動 .env 読み込みを止めたいとき:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク依存部分は unit test でモックしやすいように設計されています（内部の _call_openai_api 等を patch する）。
- DuckDB をテストで使う場合は ":memory:" でインメモリ DB を利用できます（例: init_audit_db(":memory:")）。

---

この README はコードベース（src/kabusys）から主要な設計方針・使用例を抜粋して記述しています。具体的な運用フロー（発注ロジック、Slack 通知、戦略実行ループ等）は別途 strategy / execution モジュールや運用ドキュメントで管理される想定です。必要であれば各機能の使い方（API レベルの細かい例）や .env.example のテンプレート、依存関係一覧（requirements.txt）も作成します。どの情報がさらに必要か教えてください。