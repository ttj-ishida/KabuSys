# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター計算、監査ログ（発注・約定トレース）、研究用ユーティリティを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等性（DB へは ON CONFLICT / DELETE→INSERT などで上書き保存）
- フェイルセーフ（外部 API エラー時はスキップして継続する設計）
- DuckDB をデータ層に採用（軽量で SQL が使える）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの日足（OHLCV）取得、財務データ、JPX カレンダー取得（jquants_client）
  - 差分更新・バックフィル対応の ETL パイプライン（data.pipeline.run_daily_etl 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS 取得・正規化・raw_news 保存（news_collector）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai.news_nlp.score_news）
  - マクロ記事を用いた市場レジーム判定（ai.regime_detector.score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー（research.feature_exploration）
  - Zスコア正規化等のユーティリティ（data.stats.zscore_normalize）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレース用テーブル定義と初期化（data.audit.init_audit_schema / init_audit_db）
  - 発注の冪等キー（order_request_id）やタイムスタンプ（UTC）を前提とした設計

- 設定管理
  - .env または環境変数から設定を読み込む（config.Settings）
  - パッケージルート（.git / pyproject.toml）を基準に .env/.env.local 自動読み込み（無効化可）

---

## 必要条件 / 依存ライブラリ

（実行環境に応じてインストールしてください）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

例（pip）:
pip install duckdb openai defusedxml

※ 実際の運用では依存を pyproject.toml / requirements.txt にまとめてください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを設置

2. 必要パッケージのインストール
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（パッケージがルートを探索して読み込み）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須となる主要環境変数（プロジェクトで使用されているもの）:
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      — kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY         — OpenAI API キー（ai.news_nlp / ai.regime_detector 使用時に必須）
   （その他、DUCKDB_PATH / SQLITE_PATH / KABU_API_BASE_URL / KABUSYS_ENV / LOG_LEVEL 等は任意でデフォルトあり）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB（データベース）準備
   - ETL・データ格納用の DuckDB ファイルはデフォルトで `data/kabusys.duckdb`（settings.duckdb_path）。
   - 監査ログ専用 DB を分けたい場合は `data/audit.duckdb` などを指定して `data.audit.init_audit_db()` を使用します。

---

## 使い方（代表的な例）

下記は Python REPL / スクリプトからの呼び出し例です。適切な環境変数をセットした上で実行してください。

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム（bull/neutral/bear）を算出して market_regime に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # インメモリ ":memory:" も可
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])
  ```

注意:
- OpenAI 呼び出しを伴う処理（score_news / score_regime）は API キーおよびネットワーク接続が必要です。API失敗時は警告を出して該当処理をスキップし、システム全体は継続する設計です。
- ETL やニュース取得は外部 API 呼び出しのため実行中にレート制限やネットワーク障害が発生することがあります。ログを確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリ内の主なモジュール階層と特徴です（抜粋）:

- src/kabusys/
  - __init__.py            — パッケージ初期化（version 等）
  - config.py              — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント算出（OpenAI 連携）
    - regime_detector.py   — マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl など）
    - etl.py               — ETLResult 再エクスポート
    - news_collector.py    — RSS 収集・前処理・保存ロジック
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             — Zスコア正規化など共通統計ユーティリティ
    - audit.py             — 監査テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー 等

---

## 運用上の注意・補足

- セキュリティ
  - news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査）や XML 内容に対する defusedxml の利用などを行っています。
  - 環境変数に API キー等を置く際はアクセス制御に注意してください。

- 冪等性
  - ETL と保存関数（save_daily_quotes / save_financial_statements / save_market_calendar 等）は ON CONFLICT を用いて冪等に動作することを意図しています。

- ログ・監視
  - settings.log_level によりログレベルを制御できます。Slack 通知等は別モジュール（未掲載）と連携する想定です。

- テスト
  - OpenAI / ネットワーク呼び出しはモックしやすいように内部呼び出し関数が分離されています（ユニットテストで差し替え可能）。

---

README はここまでです。必要であれば以下を追加できます：
- API リファレンス（各関数の引数・返り値の詳細）
- 具体的な .env.example ファイル
- 実行用スクリプト / systemd / cron ジョブ例
- CI / テスト手順

どれを追加しますか？