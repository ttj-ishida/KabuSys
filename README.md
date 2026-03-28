# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、LLM を使ったセンチメント評価、市場レジーム判定、ファクター計算・リサーチ、監査ログ（オーディット）など、トレーディングシステム構築に必要な機能をモジュール化して提供します。

概要・設計方針の一部：
- Look-ahead バイアスを避ける設計（内部で date.today() を不用意に参照しない等）
- DuckDB をデータレイクとして使用（冪等保存、トランザクション利用）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- OpenAI（gpt-4o-mini）を利用した JSON Mode を前提にした LLM 呼び出し
- 冪等性・監査証跡を重視（監査テーブル、UUID ベースのトレーサビリティ）

---

## 主な機能一覧

- data
  - ETL パイプライン: 日次 ETL（株価、財務、カレンダー）実行（kabusys.data.pipeline.run_daily_etl）
  - J-Quants API クライアント（fetch / save / 認証・リトライ・レートリミッタ付）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化、トラッキング除去）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化・DB（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（銘柄ごとのセンチメントを取得して ai_scores に保存）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成してレジームを判定）: kabusys.ai.regime_detector.score_regime
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク変換等
- config
  - 環境変数読み込み（.env 自動読み込み。プロジェクトルートは .git or pyproject.toml を基準）
  - Settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>
   - プロジェクトルートに移動

2. Python 環境（推奨: venv / pyenv）
   - python 3.9+ を利用してください（コードは型ヒントに 3.10+ の表記も含まれますが、互換性があれば動作します）。
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate

3. 必要なパッケージをインストール
   - 主要依存（一例）:
     - duckdb
     - openai
     - defusedxml
   - pip インストール例:
     - pip install duckdb openai defusedxml
   - （実際の requirements.txt がある場合はそれを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数（主要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（ETL 用）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（実行モジュールで使用）
     - SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector など）
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — 監視データベースパス（デフォルト data/monitoring.db）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

5. データディレクトリ
   - デフォルトでは data/ 以下に duckdb ファイル等が置かれます。存在しない場合は自動作成される関数もありますが、適宜ディレクトリを用意してください。

---

## 使い方（主要な呼び出し例）

※ 以下は最小限の使用例です。実運用ではログ設定や例外処理、トークン管理を適切に行ってください。

1. DuckDB 接続を用意して ETL を回す
   - Python 例:
     - import duckdb
     - from kabusys.data.pipeline import run_daily_etl
     - from datetime import date
     - conn = duckdb.connect("data/kabusys.duckdb")
     - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
     - print(result.to_dict())

2. ニュース NLP（銘柄ごとのニューススコア付け）
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - score_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は環境変数 OPENAI_API_KEY を利用
   - returns: 書き込んだ銘柄数（int）

3. 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - from datetime import date
   - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   - テーブル market_regime に判定結果を書き込みます

4. 監査ログ DB 初期化（オーダー監査用）
   - from kabusys.data.audit import init_audit_db
   - conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

5. ファクター計算・リサーチ
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - records = calc_momentum(conn, target_date=date(2026, 3, 20))
   - 正規化ユーティリティ: from kabusys.data.stats import zscore_normalize

6. J-Quants 直接利用（クライアント）
   - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   - token = get_id_token()  # settings.jquants_refresh_token を利用して id_token を取得
   - data = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))

7. デバッグ・設定
   - 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で有用）。

---

## 主要なディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py          — パッケージ定義（version 等）
  - config.py            — 環境変数 / Settings 管理、.env 自動読み込み
- src/kabusys/data/
  - __init__.py
  - pipeline.py          — ETL パイプライン（run_daily_etl / run_*_etl）
  - jquants_client.py    — J-Quants API クライアント（fetch / save / get_id_token）
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py    — RSS ニュース収集（SSRF 対策、正規化）
  - quality.py           — データ品質チェック
  - stats.py             — 統計ユーティリティ（zscore_normalize）
  - audit.py             — 監査ログ（DDL / 初期化）
  - etl.py               — ETLResult の再エクスポート
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP（score_news）
  - regime_detector.py   — 市場レジーム判定（score_regime）
- src/kabusys/research/
  - __init__.py
  - factor_research.py   — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- その他
  - src/kabusys/…（将来 strategy / execution / monitoring 等のサブパッケージを想定）

（上記は現状の主要ファイルを要約。詳細は src/kabusys 以下を参照してください。）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants refresh token
- KABU_API_PASSWORD (必須 for kabu API)
- SLACK_BOT_TOKEN (必須 if Slack通知を使用)
- SLACK_CHANNEL_ID (必須 if Slack通知を使用)
- OPENAI_API_KEY (必須 for AI スコアリング機能)
- DUCKDB_PATH (省略可、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|...)

.env.example 等を参考にプロジェクトルートに .env を作成してください。

---

## 注意事項 / 運用上のヒント

- OpenAI の呼び出しはコストとレート制限がかかります。バッチサイズやリトライ設定を運用に合わせて調整してください。
- J-Quants API にはレート制限があるため、jquants_client は内部でスロットリングとリトライを実装しています。大量データ取り込みは時間を要する場合があります。
- 本リポジトリはバックテストや研究用途とプロダクション用途の両方を想定していますが、発注（実際のブローカーへの送信）を行うモジュールを組み合わせる際は安全策（ペーパー取引モード・制限・二重発注防止）を必ず導入してください。
- DuckDB のバージョン差異により executemany の扱い等に注意があります（pipeline / ai モジュール内に対策あり）。

---

必要であれば以下も作成できます：
- requirements.txt / pyproject.toml のテンプレート
- 実行スクリプト（CLI）サンプル
- よくあるトラブルシュート（例: OpenAI レスポンスパースエラー、J-Quants 401 トークン更新失敗 など）

ご希望があれば README に追記します。