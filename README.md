# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ「KabuSys」のリポジトリ向け README（日本語）。

この README は、コードベース（src/kabusys 以下）に基づいて以下を説明します。

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な API/ジョブの実行例）
- ディレクトリ構成（主要ファイルの役割）
- 環境変数一覧（必須・任意）

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・品質管理・特徴量（ファクター）計算・AI（LLM）を用いたニュースセンチメント評価・市場レジーム判定・ETL パイプライン・監査ログ管理などを包含する内部ライブラリです。主に以下用途を想定しています。

- J-Quants API から株価・財務・カレンダー等を差分で取得する ETL
- RSS を用いたニュース収集と AI による銘柄別センチメントスコア算出
- 市場レジーム（bull/neutral/bear）判定（ETF の移動平均乖離 + マクロニュース）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引フローの監査ログ（signal → order_request → execution）を DuckDB に永続化

設計方針として、ルックアヘッドバイアス回避（内部で date.today() を直接参照しない）、API 呼び出しの堅牢性（リトライ・バックオフ）、DuckDB を利用した軽量な永続化・処理を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB へ冪等保存）
  - ニュース収集（RSS）と前処理（SSRF 防御、URL 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ DB 初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（gpt-4o-mini を想定した JSON Mode を使用し銘柄別スコアを取得）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン計算、IC、統計サマリー など）
- config
  - 環境変数読み込みと設定（.env 自動ロード／必須値チェック）
- audit / monitoring / execution / strategy（基盤としての監査・発注・戦略レイヤーの土台）

---

## 前提条件（最低限）

- Python 3.10 以上（型注釈に | を使用しているため）
- 必要な主要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

プロジェクト内の pyproject.toml / requirements.txt がある想定でインストールしてください。

---

## セットアップ手順（例）

1. リポジトリをクローンし移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージのインストール

   - 開発環境でローカルインストールする場合（プロジェクトルートに pyproject.toml がある想定）:

     ```bash
     pip install -e .
     ```

   - 必要な依存だけをインストールする場合:

     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置すると自動読み込みされます（読み込み順: OS 環境変数 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（後節に一覧あり）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - OPENAI_API_KEY（AI 機能を使う場合必須）
   - KABU_API_PASSWORD（kabuステーション連携）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（監視通知用）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（モニタリング DB など）

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB ファイルディレクトリ作成（必要なら）

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

下記は Python スクリプト内または対話環境での利用例です。適切な環境変数（特に API キー）は必ず設定してください。

- 共通準備（DuckDB 接続と設定取得）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # Path object を文字列で渡す
  ```

- 日次 ETL を実行する（run_daily_etl）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  - ETL では市場カレンダー → 株価日足 → 財務データ → 品質チェック の順に実行します。
  - ETLResult に保存数や検出された品質問題が格納されます。

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY から自動取得されますが、
  # 第3引数で明示的に渡すこともできます。
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム算出（ETF 1321 の MA200 + マクロニュース）

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  res = score_regime(conn, target_date=date(2026,3,20))
  print("score_regime result:", res)
  ```

- 監査ログ（audit DB）初期化

  監査ログ専用 DB を作成してスキーマを初期化するユーティリティがあります。

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
  ```

  既存接続に監査スキーマを追加したい場合は `init_audit_schema(conn)` を使います。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY
  - OpenAI API（gpt-4o-mini 等）呼び出しに必要。news_nlp / regime_detector で参照。

- KABU_API_PASSWORD
  - kabuステーション API 連携に必要（発注モジュール等で使用）。

- KABUSYS_ENV
  - 動作環境。development / paper_trading / live（デフォルト development）

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - Slack 通知用（オプションだが設定されている想定）。

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト data/monitoring.db）

自動的に `.env` / `.env.local` をプロジェクトルートから読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## トラブルシューティング / 注意点

- .env の自動ロードはプロジェクトルート（.git もしくは pyproject.toml のある親）を起点に解決します。パッケージを配布後や CWD が異なる場合、期待どおりに見つからないことがあります。必要に応じて環境変数を OS レベルで設定してください。
- OpenAI 呼び出しはエラー時にフォールバックする設計（ニュースが無い／APIエラーならスコア 0.0）ですが、API キーが未設定だと ValueError を出します。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングを行います。大量取得の際は時間がかかる可能性があります。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード中では空チェックを行っています。DuckDB のバージョンに注意してください。
- RSS の取得は SSRF 対策・サイズ制限・gzip 対策等の防御を行っています。外部 RSS を追加する場合、URL のスキーム（http/https）やホストがプライベートネットワークでないことを確認してください。

---

## ディレクトリ構成（主なファイルと説明）

（プロジェクトルート / src/kabusys 以下）

- __init__.py
  - パッケージのバージョンとエクスポート設定

- config.py
  - 環境変数読み込み、Settings クラス（設定管理）

- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの集約・OpenAI 呼び出し・レスポンス検証・ai_scores テーブルへの書込み
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースを組み合わせた市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック・レート制御）
  - pipeline.py
    - ETL のメインと個別ジョブ（run_daily_etl, run_prices_etl 等）および ETLResult
  - news_collector.py
    - RSS 取得・前処理・記事ID 正規化・SSRF 対策
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management.py
    - 市場カレンダー管理、営業日判定、calendar_update_job
  - audit.py
    - 監査ログの DDL/初期化処理（signal_events / order_requests / executions）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - etl.py
    - ETLResult の公開再エクスポート

- research/
  - __init__.py
  - factor_research.py
    - モメンタム、ボラティリティ、バリューの計算
  - feature_exploration.py
    - 将来リターン、IC、統計サマリー、rank 等の研究用ユーティリティ

その他、strategy/、execution/、monitoring/ といったモジュールを想定してエクスポート定義が行われています（コードベースの一部のみを抜粋）。

---

## 開発とテストについて（簡易）

- 自動環境変数読み込みを無効にしてユニットテストや CI で明示的に環境を作る場合:

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- AI 呼び出しや外部 API 呼び出しはユニットテストでモック可能なように設計されています（例: news_nlp._call_openai_api を patch する等）。

---

もし README に追加したいサンプル（より詳しい ETL ワークフロー、Docker / CI 設定、.env.example の具体例、スキーマ定義の README など）があれば、用途やターゲット（運用者 / 開発者 / 研究者）を教えてください。目的に合わせた詳細な手順やサンプルコードを追加します。