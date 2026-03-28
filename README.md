# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（株価 / 財務 / カレンダー）・データ品質チェック・ニュース NLP・市場レジーム判定・研究用ファクター計算・監査ログ（発注 / 約定トレーサビリティ）など、一連のバックエンド機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL（J-Quants API 経由）
  - 株価日足（OHLCV）、四半期財務、JPX カレンダーの差分取得・保存（冪等）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、重複、将来日付、株価スパイクなどの検出
- ニュース収集 / 前処理
  - RSS フィードの安全な取得（SSRF 対策、gzip / サイズ制限、トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント算出（gpt-4o-mini を想定）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントを合成して日次で 'bull' / 'neutral' / 'bear' を判定
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算、将来リターン、IC（情報係数）、統計サマリー
- 監査ログ（オーディット）
  - signal_events / order_requests / executions テーブルを提供し、発注から約定までのトレーサビリティを保証

---

## 必要環境

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 主な Python 依存ライブラリ:
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで多くの処理を実装）

依存関係は pyproject.toml / requirements.txt を用意している想定です。手元の環境に合わせてインストールしてください。

---

## セットアップ

1. リポジトリをクローン、またはプロジェクトルートへ移動。

2. 仮想環境を用意して依存パッケージをインストール（例）:

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # または: pip install -e .
   ```

3. 環境変数 / .env の準備  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主に必要となる環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（発注系）
   - SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
   - SLACK_CHANNEL_ID — Slack チャネル ID（必要な場合）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite path（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
   - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

   .env の例（簡略）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な呼び出し例）

以下はライブラリを Python から利用する最小例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続（settings 参照）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成する（OpenAI API キーが必要）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
  print("書き込み銘柄数:", written)
  ```

- 市場レジームを算出して保存する（OpenAI API キーが必要）

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 研究用ファクター計算

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

- 監査ログ用 DB 初期化（監査専用 DB を別途作る場合）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- ニュース RSS を取得（単体テスト用）

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode を利用する実装になっています。API 呼び出し回数やレートに注意してください。
- ETL / news_nlp / regime_detector は Look-ahead bias を避ける設計（target_date 未満／前日ウィンドウ等）になっています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 src/kabusys をルートとして抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込み（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、batch 処理、検証）
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py — RSS 収集 / 前処理 / 保存ロジック
    - calendar_management.py — 市場カレンダー / 営業日判定 / calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — Z スコア正規化などの統計ユーティリティ
    - audit.py — 監査ログスキーマ初期化（signal_events, order_requests, executions）
    - (その他: jquants_client の保存関数 / ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 設計上のポイント・注意点

- 冪等性: 多くの保存関数は ON CONFLICT DO UPDATE を用いてあり、再実行しても安全な設計です。
- Look-ahead バイアス対策: 多くの分析関数・ETL は target_date より未来データを参照しないように注意して実装されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）で問題が起きた際、極力例外を上位に投げずにフォールバックやログ出力で継続する実装が多いです（ただし重要な認証情報が欠けている場合は ValueError が発生します）。
- セキュリティ: news_collector は SSRF 対策、XML パースの安全化、レスポンスサイズ制限などを行っています。

---

## 開発 / テスト

- 自動環境変数読み込みはプロジェクトルートの .env / .env.local を参照します。テスト中に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出し部分は内部で関数を分離しており、unittest.mock.patch により外部 API をモックしてユニットテストしやすく設計されています。

---

問題点・追加要求があれば、README の改善点（例: 実行用 CLI、systemd / Airflow のジョブ定義、より詳細な .env.example、テスト例）を教えてください。必要に応じて README の拡張版を作成します。