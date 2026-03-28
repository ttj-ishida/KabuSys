# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
ETL（J-Quants → DuckDB）によるデータ取得・品質チェック、ニュースの収集・NLP スコアリング、LLM を用いた市場レジーム判定、研究用ファクター計算、監査ログ（発注 → 約定トレース）など、トレーディングシステムの基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル・ページネーション・冪等保存（ON CONFLICT）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- データ基盤（DuckDB）
  - raw_prices / raw_financials / market_calendar 等のテーブルへの保存ユーティリティ
  - 監査ログ（signal_events / order_requests / executions）初期化・管理
- ニュース収集・前処理
  - RSS フィードの取得（SSRF 対策・サイズ制限・URL 正規化）
  - raw_news / news_symbols テーブルへの冪等保存
- ニュース NLP / LLM
  - ニュース記事群を銘柄単位にまとめ、OpenAI（gpt-4o-mini）でセンチメント評価（ai_scores へ保存）
  - マクロニュースと ETF（1321）の MA 乖離を合成して市場レジーム判定（bull/neutral/bear）
  - 再試行・フェイルセーフ設計（API 失敗時は安全側で継続）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、Zスコア正規化、統計サマリー
- 安全性と運用性
  - .env 自動ロード（プロジェクトルート基準、OS環境変数優先）
  - レート制御（J-Quants API: 120 req/min 固定間隔スロットリング）
  - ロギング、トランザクション保護（BEGIN/COMMIT/ROLLBACK）や冪等設計

---

## 必要条件

- Python >= 3.10（PEP 604 の型記法や union 型表記を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

依存関係はプロジェクトに合わせて requirements.txt / pyproject.toml を用意してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   # または: pip install -r requirements.txt
   ```

2. 環境変数／.env を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（OS 環境変数優先）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます（テスト時など）。

3. 必須の環境変数（主要）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
   - KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 基本的な使い方（コード例）

※ すべての例は既に必要な環境変数が設定済みで、DuckDB ファイルパス等が適切に設定されていることを前提とします。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（指定日のニュースをスコアリングして ai_scores に保存）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
  print("scored:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（新規監査 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査用の DuckDB 接続（TimeZone は UTC に設定済み）
  ```

- J-Quants クライアントの直接利用（データ取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from datetime import date

  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

- RSS 取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

---

## 実装・動作上の注意／設計上のポイント

- Look-ahead バイアス防止
  - モジュールは多くの箇所で date / target_date 指定を要求し、datetime.today()/date.today() の直接参照を避けるよう設計されています（再現可能なバックステスト向け）。
- フェイルセーフ
  - LLM 呼び出しや外部 API は失敗してもシステム全体を停止させないよう、0.0 のデフォルトやスキップで継続する実装が多くあります。
- 冪等性
  - ETL 保存は ON CONFLICT などで冪等に設計されています。部分失敗時は既存データ保護に配慮しています。
- レート制御・リトライ
  - J-Quants は固定間隔スロットリング（120 req/min）を採用。OpenAI 呼び出しはエクスポネンシャルバックオフで再試行します。
- セキュリティ
  - news_collector は SSRF 対策、最大レスポンスサイズ、defusedxml による XML パース保護を実施しています。

---

## 主要なディレクトリ構成

（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数 / Settings 管理、自動 .env ロードロジック)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースの LLM スコアリング、ai_scores 書き込み)
    - regime_detector.py (マーケットレジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ユーティリティ)
    - pipeline.py (ETL パイプラインと run_daily_etl)
    - etl.py (ETL インターフェース再エクスポート)
    - calendar_management.py (市場カレンダー管理・営業日ロジック)
    - news_collector.py (RSS 収集・前処理)
    - stats.py (統計ユーティリティ: zscore 正規化)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化 / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (momentum/volatility/value 等)
    - feature_exploration.py (forward returns / IC / rank / summary)

---

## 開発時のヒント

- テスト・モック
  - OpenAI 呼び出しやネットワーク I/O 部分はモックしやすいように内部呼び出し関数を分離しています（例: _call_openai_api の patch）。
- 環境変数自動ロード
  - config.py はプロジェクトルート（.git or pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の互換性
  - DuckDB のバージョン差異に対する注記がいくつかあります（executemany の空リスト制約など）。ローカル環境ではインストールする DuckDB のバージョンに注意してください。

---

## その他

- ライセンスやコントリビュート方法はリポジトリのルートに置いてください（この README には含めていません）。
- 追加のユーティリティや実行スクリプト（CLI、ジョブスケジューリング）はプロジェクト側で適宜実装してください。

もし README に追記したい「実行スクリプト例」「CI 設定」「開発用 Dockerfile」などがあれば、提供するコードや要件に合わせて追記案を作成します。