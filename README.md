# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター算出、監査ログ（DuckDB）など、自動売買システムのデータ基盤と研究用ユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群を含みます。

- J-Quants API からの株価・財務・カレンダー取得（rate limiting / retry / token refresh 対応）
- DuckDB を用いた ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS を用いたニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（AI スコア）と市場レジーム判定
- 研究向けファクター算出（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）を格納する DuckDB スキーマ

設計上の共通方針として、バックテストでのルックアヘッドバイアスを避ける実装や、外部 API 呼び出しの堅牢化（リトライ・フェイルセーフ）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からの取得・DuckDB 保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 収集・前処理・raw_news 保存処理のユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等のカレンダー補助
  - audit: 監査ログ用テーブル定義・初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA とマクロニュースを合成して市場レジームを判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数自動ロード（.env / .env.local）と設定取得（settings）

---

## 必要条件・依存パッケージ

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリや urllib 等も使用

（実プロジェクトでは pyproject.toml / requirements.txt を参照して正確な依存をインストールしてください）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements/pyproject があればそちらを使用）
   ```bash
   pip install duckdb openai defusedxml
   pip install -e .
   ```

4. 環境変数を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN  （必須） — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD      （必須） — kabu API パスワード（発注等）
   - SLACK_BOT_TOKEN        （必須） — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID       （必須） — Slack チャネル ID
   - OPENAI_API_KEY         （必須 for AI 機能） — OpenAI API キー
   - DUCKDB_PATH            （任意, default: data/kabusys.duckdb）
   - SQLITE_PATH            （任意, default: data/monitoring.db）
   - KABUSYS_ENV            （任意, development|paper_trading|live）
   - LOG_LEVEL              （任意）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから呼ぶ典型的な流れです。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを作成（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込む
  print("wrote scores for", written, "codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import (
      is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  )
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  ```

注: OpenAI 呼び出しを伴う機能は API キーとネットワーク環境が必要です。テストでは該当関数をモックする設計がなされています。

---

## .env 自動ロードの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント生成（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント / DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — マーケットカレンダー管理 / 営業日判定
    - quality.py                     — データ品質チェック
    - stats.py                       — zscore_normalize 等
    - audit.py                       — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py         — forward returns / IC / summary / rank
  - research/
  - (その他: strategy / execution / monitoring のプレースホルダ)

リポジトリルートでは pyproject.toml 等のパッケージ定義を想定しています。

---

## 注意点・運用上のポイント

- ルックアヘッドバイアス対策: 多くの関数は date 引数を明示的に受け取り、内部で datetime.today() を直接参照しない設計です。バックテストでは必ず過去時点のデータのみを与えるよう注意してください。
- OpenAI / 外部 API 呼び出しは失敗時にフェイルセーフ（スコア 0.0 など）で継続する実装になっていますが、結果の解釈には注意が必要です。
- DuckDB への大量挿入では executemany の挙動（空リスト不可など）に配慮した実装になっています。
- news_collector は SSRF 対策（リダイレクト検査・プライベートIPブロック）や受信サイズ制限などセキュリティ考慮があります。

---

## 貢献／開発

- バグ修正・機能追加は PR を受け付けます。コードはユニットテスト・静的解析を通すことを推奨します。
- 外部 API（J-Quants / OpenAI）を使用する箇所はインタフェースが抽象化されており、テスト時はモック差し替え可能です。

---

以上。必要であれば README に「コマンドラインツール」「CI設定」「より詳細な API リファレンス」等の節を追加できます。どの項目を拡張したいか教えてください。