# KabuSys

日本株自動売買プラットフォームのコアライブラリ群（データ収集・ETL・品質チェック・研究用ファクター・AI ニュース解析・監査ログ等）

このリポジトリは、J-Quants / RSS / kabuステーション / OpenAI 等を組み合わせて、
データパイプライン、ファクター計算、ニュースセンチメント評価、監査ログといった
自動売買システムの基盤機能を提供します。

---

## 主要機能（抜粋）

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数取得ヘルパ（未設定時は明確なエラーを返す）

- データプラットフォーム（DuckDBベース）
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
  - 差分ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS、安全対策付き）と raw_news 保存
  - 監査ログスキーマ / 初期化（signal_events, order_requests, executions）

- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - クロスセクション Z スコア正規化ユーティリティ

- AI（OpenAI）連携
  - ニュース記事をまとめて LLM に投げる sentiment スコアリング（score_news）
  - ETF（1321）200日MA乖離とマクロニュースを合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ / バックオフ・JSON モード対応（レスポンス検証あり）

- ネットワーク安全対策
  - RSS 収集時の SSRF 対策、受信サイズ制限、gzip 解凍保護など

---

## 必要条件（想定）

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt がある場合はそちらを参照してください）

---

## 環境変数（主なもの）

以下はライブラリ内で参照される主な環境変数です（README の例）：

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
- KABUSYS_ENV: 環境 ("development"|"paper_trading"|"live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL")（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から
`.env`、`.env.local` を自動で読み込みます。.env.example を参考に .env を作成してください。

.env の読み込みルール（簡潔）:
- OS 環境変数 > .env.local > .env の優先順位
- export KEY=val 形式に対応
- クォート・エスケープ・インラインコメントに対する堅牢なパース実装あり

---

## セットアップ（開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を使ってください）
   開発インストール:
   - python -m pip install -e .

4. .env を作成
   プロジェクトルートに `.env` または `.env.local` を作成して必要な環境変数を設定します。
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=passwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要API例）

以下はライブラリの代表的な呼び出し例です。各関数は DuckDB 接続を受け取る設計です。

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントスコア生成（AI）
  - ai.score_news は ai モジュールの公開関数です。api_key を引数で渡せます（テスト時に差し替え可能）。
  ```python
  from datetime import date
  from kabusys.ai import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {written} stocks")
  ```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリが無ければ自動作成
  ```

- J-Quants から直接データを取得して保存（ETL内部で使用される関数）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  saved = save_daily_quotes(conn, records)
  ```

- データ品質チェックを個別で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI API 呼び出しは gpt-4o-mini を想定しており、結果は JSON mode を期待して検証しています。
- API キーを明示的に渡せる設計（api_key 引数）なので、テスト時はモックやテストキーを利用してください。

---

## 設計上のポイント / 注意事項

- ルックアヘッドバイアス回避:
  - 内部実装は date.today() や datetime.today() を直接参照しない設計で、
    バックテストや再現性の観点から target_date ベースで動作します。

- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）が不安定な場合、多くの箇所で安全側のデフォルトを返すか
    スキップして処理継続するようになっています（例: macro_sentiment=0.0）。

- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を使用して冪等に保存します。
  - ニュース収集は URL 正規化＋ハッシュで ID を生成し重複を防ぎます。

- テスト容易性:
  - OpenAI 呼び出しやネットワークアクセス箇所は関数を差し替え可能（unittest.mock.patch）な設計です。

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys 以下）の主要ファイル一覧です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（他の研究用モジュール）
  - (その他: strategy / execution / monitoring パッケージが初期公開される想定)

この README は主要部分を抜粋したものです。各モジュールの docstring に詳細な設計意図・処理フロー・例外仕様が記載されています。開発時はそちらも参照してください。

---

## 開発・運用上のヒント

- ローカル開発では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます（テスト環境構築時に便利）。
- ETL の実行はスケジューラ（cron / Airflow / GitHub Actions など）から日次で run_daily_etl を呼ぶ想定です。
- OpenAI 呼び出しはコストとレート制限に留意してください。batch サイズやトークン消費を適切に調整してください。
- DuckDB ファイルはバックアップやロールフォワードに注意して管理してください。
- 監査ログは削除しない前提です。ストレージ管理（アーカイブ）ポリシーを検討してください。

---

もし README に追加したい内容（例: CI 手順、詳細なスキーマ定義、運用フロー図、例外ハンドリング方針など）があれば教えてください。必要に応じて追記・整備します。