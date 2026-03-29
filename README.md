# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants / RSS / OpenAI 等を組み合わせてデータ取得・品質チェック・AIによるニュース評価・市場レジーム判定・監査ログなどの機能を提供します。

主な用途例:
- 日次ETL（株価・財務・市場カレンダー）を自動取得して DuckDB に保存
- ニュースを集約して LLM で銘柄ごとのセンチメントを算出し ai_scores に保存
- ETF とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定
- 監査用テーブルでシグナル→発注→約定のトレーサビリティを保持
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 機能一覧

- data（データ基盤）
  - ETLパイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF対策、URL正規化）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ（signal_events, order_requests, executions）初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize など）

- ai（LLM連携）
  - news_nlp.score_news: 銘柄ごとにニュースを集約して LLM に送り ai_scores を生成
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して market_regime に書き込み

- research（調査用）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC/ランク/統計サマリーなど

- config
  - .env 自動ロード（プロジェクトルート検出）と Settings（環境変数管理）

---

## 必要環境・依存

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI 等）

（実際の setup.py / pyproject.toml に従ってインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   - 例: git clone ... && python -m pip install -e .

2. 必要な環境変数を設定
   - 推奨: プロジェクトルートに `.env` を作成（`.env.example` を参考に）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注関連）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | ...) — デフォルト `INFO`
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定するか、各関数に api_key 引数を渡す

3. 自動 .env ロードについて
   - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して自動で `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 追加インストール（例）
   - pip install duckdb openai defusedxml

---

## 使い方（簡易ガイド）

以下はライブラリの代表的な使用例です。実際はアプリ側でエラーハンドリングやログを適切に行ってください。

- DuckDB 接続を作成して ETL を日次実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリング（LLM）を実行する例:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"ai_scores に書き込んだ銘柄数: {written}")

- 市場レジーム判定を実行する例:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログDBの初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます

- データ品質チェック（単体実行）:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点:
- AI 呼び出し関数（score_news / score_regime）は OPENAI_API_KEY を期待します。api_key を直接渡すことも可能です。
- 各処理はルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない・target_date ベース）になっています。
- DuckDB の executemany は空リストを受け取れない箇所があるため、呼び出し側の実装で空チェックが実装されています。

---

## よくある操作コマンド例

- .env を読み込ませた上で ETL を実行する（スクリプトを用意して呼ぶことを想定）
- テスト実行時に自動 .env ロードを抑止:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（自動 .env ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを LLM でスコア化して ai_scores へ書き込み
    - regime_detector.py           — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 型再エクスポート（ETLResult）
    - news_collector.py            — RSS 取得・前処理・raw_news 保存（SSRF対策）
    - calendar_management.py       — 市場カレンダー管理・判定ロジック
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - audit.py                     — 監査ログ（DDL / 初期化）ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等の計算
    - feature_exploration.py       — 将来リターン / IC / rank / summary 等

---

## 開発／運用上の注意

- セキュリティ:
  - news_collector は SSRF や XML Bomb 等に対する対策を実装していますが、運用時はネットワークポリシーや RSS ソースの管理を行ってください。
  - APIキーやパスワードは `.env` やシークレットストアで安全に管理してください。

- エラー設計:
  - 多くの処理はフェイルセーフ（API失敗時の部分スキップや 0.0 フォールバック）を採用しています。アプリケーション側でログやアラートを設定して可視化してください。

- テスト:
  - LLM / 外部API 呼び出しはモック化してユニットテストを作成してください。内部で API 呼び出し関数を差し替えられるよう設計されています（unittest.mock.patch を想定）。

---

README は概要と典型的な使い方をまとめたものです。より詳細な仕様（スキーマ、API レスポンスのフィールド仕様、運用手順）はプロジェクト内の設計ドキュメント（DataPlatform.md, StrategyModel.md 等）を参照してください。必要であれば README に追加する例やコマンドを増やします。