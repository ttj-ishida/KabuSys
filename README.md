# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（オーダー／約定トレーサビリティ）、市場カレンダー管理など、投資戦略開発・バックテスト・運用に必要な基盤機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を担います。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集し raw_news に保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算と特徴量探索ツール
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化と DB ユーティリティ
- 設定管理（.env/.env.local の自動ロードや環境変数経由の設定）

設計上のポイント：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない等）
- 冪等性を重視（DB への保存は ON CONFLICT DO UPDATE 等）
- フェイルセーフ（外部 API 失敗時は適切にフォールバックし例外を走らせない箇所がある）
- DuckDB を中心に軽量に動作するよう設計

---

## 主な機能一覧

- data/
  - ETL：run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client：J-Quants API 呼び出し・ページネーション・保存（raw_prices, raw_financials, market_calendar 等）
  - news_collector：RSS 取得・前処理・raw_news への冪等保存
  - quality：データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management：営業日判定・next/prev_trading_day 等、market_calendar 管理
  - audit：監査ログ用スキーマ初期化（signal_events / order_requests / executions）
  - stats：zscore_normalize などの統計ユーティリティ
- ai/
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF（1321）MA200 乖離とマクロセンチメントを合成して market_regime を更新
- research/
  - factor_research：calc_momentum, calc_value, calc_volatility
  - feature_exploration：calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理（kabusys.config.Settings）：環境変数・.env 自動ロード機能

---

## 前提（Prerequisites）

- Python 3.10 以上（モジュール内で | 型注釈等を使用）
- pip が使える環境
- 必要な Python パッケージ（例: duckdb, openai, defusedxml など）

例（仮の requirements）:
- duckdb
- openai
- defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローン（例）
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（例）
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

4. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 必要な変数（最低限）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY：OpenAI API キー（ai モジュールを使う場合）
     - SLACK_BOT_TOKEN：Slack 通知を使う場合
     - SLACK_CHANNEL_ID：Slack 通知チャンネル
     - KABU_API_PASSWORD：kabu ステーション API パスワード（実運用で使用する場合）
     - DUCKDB_PATH（省略可、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（省略可、デフォルト data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live のいずれか）
     - LOG_LEVEL（DEBUG/INFO/...）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。DuckDB 接続を作成し、ETL / AI / 研究系関数を呼び出します。

- DuckDB 接続の作成（ファイル DB）
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL（市場カレンダー取得 → 株価・財務取得 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアリング（先に raw_news, news_symbols が存在すること）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  score_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {score_count} codes")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算例
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))

- 監査ログスキーマ初期化（監査用 DB を別ファイルに分けたい場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意:
- OpenAI API を使用する関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を使用する関数は内部で settings.jquants_refresh_token を参照して id_token を取得します（必要に応じて get_id_token に明示的に渡すことも可能）。

---

## 重要な設定と自動読み込み

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を基準に .env と .env.local を自動ロードします。
  - ロード順: OS 環境変数 > .env.local（override=True） > .env（override=False）
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップします。

- Settings（kabusys.config.settings）で取得される主要な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須で kabu API を使う場合)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                        -- 設定・.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント集計と ai_scores 書き込み
    - regime_detector.py             -- マクロ + ETF MA 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API 呼び出し & DuckDB 保存関数
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py                         -- ETLResult の再エクスポート
    - news_collector.py              -- RSS 取得・前処理・保存
    - calendar_management.py         -- market_calendar 管理・営業日ロジック
    - quality.py                     -- データ品質チェック群
    - stats.py                       -- zscore_normalize 等
    - audit.py                       -- 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py         -- 将来リターン・IC・統計サマリー等
  - research/*（他の研究ユーティリティ）
  - (strategy, execution, monitoring) -- パッケージ公開用名だが実装ファイルは別に配置される想定

（README は実装ファイル群の抜粋に基づいて作成しています。実際のリポジトリでは tests、scripts、examples などが存在する場合があります。）

---

## 開発・運用上の注意

- DuckDB の SQL 互換性に依存する箇所があるため、DuckDB のバージョンによる微妙な挙動差に注意してください（コメントに互換性対策多数）。
- OpenAI のレスポンスは外部依存かつ変動するため、news_nlp や regime_detector は冪等やパース失敗時のフォールバックを備えています。API 利用時はレート制限と課金に注意してください。
- J-Quants API のレート制限や認証リフレッシュ処理を組み込んでいますが、実運用では id_token の取り扱いやリトライ方針を更に確認してください。
- .env ファイルにシークレット（API キー等）を含める場合はリポジトリにコミットしないように注意してください（.gitignore に .env を追加する等）。

---

## 貢献・拡張

- 新しいデータソースの追加（RSS ソースや外部ファクト）や戦略モジュールの追加は、既存の data / ai / research API を利用して拡張できます。
- テストを追加する場合は、各外部呼び出し（OpenAI, J-Quants, HTTP）をモックしてユニットテストを作成してください。コード内にテスト差し替えを想定した hook（例: _call_openai_api の差し替え）があります。

---

必要であれば、README に含める詳細な .env.example、requirements.txt の候補、実行スクリプト例（cron / systemd timer 用）や運用手順（バックアップ、監査 DB 管理）なども追記できます。希望があれば教えてください。