# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。ETL（J-Quants からの差分取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（発注／約定トレース）、マーケットカレンダー管理など、アルゴリズムトレード基盤の主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能群を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API 経由、DuckDB 保存）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）と NLP（OpenAI を用いた銘柄ごとのセンチメント）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、前方リターン、IC、正規化）
- 監査ログ（signal → order_request → execution の完全トレース）
- マーケットカレンダー管理（JPX カレンダーの差分更新／営業日判定）

設計上の共通方針として、ルックアヘッドバイアスを避けるために内部で date.today()/datetime.today() を不用意に参照しない、外部 API 呼び出しはフェイルセーフに、DuckDB を利用した冪等（ON CONFLICT）保存を行う、などが徹底されています。

---

## 機能一覧

主な公開 API と役割（抜粋）:

- kabusys.config
  - settings: 環境変数から各種設定を取得（J-Quants, kabuAPI, Slack, DB パス等）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
- kabusys.data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（fetch_* / save_*）
  - pipeline.run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: 営業日判定・next/prev_trading_day など
  - news_collector: RSS 収集・前処理・raw_news 保存
  - quality: データ品質チェック（missing / spike / duplicates / date_consistency）
  - audit: 監査ログテーブルの初期化（signal_events / order_requests / executions）
  - stats: z-score 正規化など汎用統計
- kabusys.ai
  - news_nlp.score_news: 指定日ウィンドウのニュースを銘柄別に LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日 MA とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- kabusys.research
  - calc_momentum / calc_value / calc_volatility 等：バックテスト・研究用ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索ユーティリティ

---

## セットアップ手順

※ このリポジトリの pyproject.toml 等に依存するため、環境に合わせて適宜修正してください。以下は一般的な手順例です。

1. Python 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   - 本コードは以下のパッケージを利用します（最低限の例）:
     - duckdb
     - openai
     - defusedxml
   - requirements.txt があれば:
     ```bash
     pip install -r requirements.txt
     ```
   - なければ個別に:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. パッケージをインストール（開発モード）
   ```bash
   pip install -e .
   ```
   またはプロジェクト管理ツール（poetry 等）を利用してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数より低優先）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（基本的な例）

以下は Python REPL / スクリプトから主要機能を呼び出す例です。

- DuckDB 接続準備（設定に従う）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア付与（OpenAI API 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていること
  n = score_news(conn, date(2026, 3, 20))
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, date(2026, 3, 20))
  # recs は各銘柄の dict のリスト
  ```

注意点:
- AI 系関数（score_news / score_regime）は OpenAI API を使用します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を使う関数は J-Quants の認証トークン（リフレッシュトークン）を `JQUANTS_REFRESH_TOKEN` に設定しておく必要があります。
- ETL は部分失敗が発生しても他ステップを継続する設計です。結果は ETLResult オブジェクトで収集されます。

---

## 主要なディレクトリ構成（src/kabusys）

（重要ファイルのみ抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings（DB パス・API トークン・環境判定等）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py    — RSS 収集・前処理
    - quality.py           — データ品質チェック
    - audit.py             — 監査ログテーブル定義／初期化
    - stats.py             — zscore_normalize 等
    - etl.py               — ETLResult 型の再エクスポート
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - research/ 以下は研究用ユーティリティ群（バックテスト・要因分析用）
  - その他: strategy / execution / monitoring 等のプレースホルダ名が __all__ に含まれています（実装の有無に依存）

---

## 設定（settings）の主なキー

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) / SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI 利用時に必要

.env 自動ロードはプロジェクトルートの `.env` → `.env.local` の順で行われ、OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## テスト・開発時の注意

- OpenAI や J-Quants の外部 API 呼び出しはネットワーク依存かつコストが発生するため、ユニットテストでは各モジュール内の API 呼び出しヘルパー関数（例: news_nlp._call_openai_api, regime_detector._call_openai_api, data.news_collector._urlopen, jquants_client._request など）をモックしてテストすることを推奨します。
- DuckDB を用いた関数は接続を引数に取る設計なので、テスト用に `duckdb.connect(":memory:")` を使って簡単に分離できます。
- ログレベルや KABUSYS_ENV を切り替えて挙動を制御してください（例: paper_trading は実発注を抑制する戦略実装側のフラグに使用）。

---

## ライセンス / 貢献

本 README はコードベースの説明を目的としています。実際に運用する前に各 API キーの管理、秘密情報の取り扱い、発注・資金管理ロジックの安全性確認を必ず行ってください。商用利用や他者への配布はプロジェクトのライセンスに従ってください（リポジトリに LICENSE があればそちらを参照）。

---

必要なら、README にサンプルの .env.example や docker / CI 設定、より詳しい API リファレンス（関数引数や戻り値の詳細）、よくある問題のトラブルシューティングを追記します。どの情報を追加しますか？