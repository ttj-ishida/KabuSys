# KabuSys

日本株のデータプラットフォームと自動売買サポートライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を使用したセンチメント）、ファクター計算、監査ログ（約定トレース）、マーケットカレンダー管理などの機能を提供します。

---

## 主な概要

- パッケージ名: `kabusys`
- 目的: 日本株のデータパイプライン（ETL）と研究/自動売買インフラのユーティリティ群を提供
- 設計方針:
  - Look-ahead bias を避ける（日付参照は明示的な引数を使用）
  - DuckDB をコアデータベースとして想定（軽量で高速な分析向け）
  - 外部 API（J-Quants / OpenAI / RSS）呼び出しは堅牢なリトライ・レート制御を実装
  - ETL・品質チェック・監査ログを通じて再現性・トレーサビリティを担保

---

## 機能一覧

- data（kabusys.data）
  - ETL パイプライン：日次 ETL（株価、財務、カレンダー） run_daily_etl
  - J-Quants クライアント（fetch / save / 認証・レート制御）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS の取得と前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（audit テーブル群の作成）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 等）を用いた JSON モード呼び出し、バッチ/リトライ制御
- research（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索（将来リターン計算、IC、サマリー）
- config（kabusys.config）
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 設定アクセス用の `settings`（各種必須/任意設定をプロパティ経由で取得）

---

## セットアップ手順

前提:
- Python 3.10 以上
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをチェックアウトし、パッケージをインストール
   - 開発中:
     - pip install -e .
   - 依存ライブラリ（最低限）:
     - duckdb, openai, defusedxml
     - 例:
       - pip install duckdb openai defusedxml

2. 環境変数 / .env の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（`kabusys.config`）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

3. 必要な環境変数（代表）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネルID（必須）
   - OPENAI_API_KEY: OpenAI API キー（news/regime スコアリングで使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - 監視用閾値等（PID_FILE_PATH, CPU_THRESHOLD_PCT, ...）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

- DuckDB 接続の準備（settings を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダー・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI APIキーは環境変数か引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を使う
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査用スキーマ初期化
  - 既存の接続にスキーマを追加:
    ```python
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)
    ```
  - 監査専用 DB を作る:
    ```python
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    ```

- RSS を直接フェッチ（ニュースコレクタの低レベル API）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意:
- AI モジュール（news_nlp / regime_detector）は OpenAI キーが必要です。api_key パラメータを渡すか OPENAI_API_KEY 環境変数を設定してください。
- すべての公開関数はドキュメント文字列（docstring）に詳しい挙動が書かれています。実行前に確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル群を抜粋しています:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py (再エクスポート)
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - ...（その他のデータユーティリティ）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（他ユーティリティ）
    - research/factor_research.py
  - その他パッケージメタ情報等

（上記はリポジトリ内の主要モジュールを示します。細かなサブモジュールはコードベースを参照してください。）

---

## 開発・運用上の注意

- Python バージョン: Union 型（A | B）を使用しているため Python >= 3.10 を推奨します。
- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動的に読み込みます。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。
- OpenAI 呼び出しはリトライ・バックオフ・5xx 対応を備えていますが、APIコストやレートには注意してください。
- J-Quants API の利用はレート制限（120 req/min）を遵守するよう実装していますが、実運用前にトークン/利用契約を確認してください。
- DuckDB のクエリ・executemany で空リストが問題になるバージョンがあります（0.10 等）。ETL 内では条件チェックで回避していますが、運用中の DuckDB バージョンに注意してください。
- 監査ログは削除しないことを前提に設計されています（トレーサビリティ保持）。

---

## ライセンス / 貢献

この README はコードベースの説明を目的とした要約です。実際のライセンス情報や貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

---

必要であれば、README に以下の追加を作成できます:
- .env.example のテンプレート
- CI / テスト実行方法の手順
- 実運用時の推奨監視・デプロイ例（systemd / Dockerfile など）

どの追加情報が欲しいか教えてください。