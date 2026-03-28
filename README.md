# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター算出、監査ログ、マーケットカレンダー管理などを含むモジュール群を提供します。

## 主な特徴
- J-Quants API と連携した差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB に定義・初期化
- DuckDB をデータストアとして利用（軽量かつ高速な分析向け）

---

## 要件
- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- OS 環境により追加ライブラリが必要な場合があります

（実際の依存はプロジェクトの packaging / requirements を参照してください。）

---

## セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # 開発用にパッケージを編集可能でインストールする場合
   pip install -e .
   ```

4. 環境変数（.env）を準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

   主要な環境変数の例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知などを使う場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境 / ログレベル
   KABUSYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   必須:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（AI 機能を使う場合）

---

## 使い方（主要ユースケースの例）

以下は Python REPL / スクリプトから呼び出す利用例です。全ての API はパッケージ経由で直接呼べます。

- DuckDB 接続準備
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（差分取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアリング（銘柄別）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム（ETF 1321 の MA200 とマクロセンチメントの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- AI 関連関数は OpenAI の API キー（OPENAI_API_KEY）を参照します。呼び出しごとに `api_key` 引数で直接指定することもできます。
- 各関数は基本的に「ルックアヘッドバイアス」を避ける設計になっているため、内部で現在日時を安易に参照しない実装になっています（テストやバックテストに向く）。

---

## 環境変数と設定
設定は基本的に環境変数から読み込みます（`kabusys.config.Settings`）。

主要な設定項目:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH / SQLITE_PATH: データベース格納先パス
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動 `.env` 読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を読み込みます。
- OS 環境変数 > .env.local > .env の優先順位
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）
以下はソースツリー（src/kabusys 以下）の主要モジュール一覧です。実装は細分化されていますが、主な機能ごとにモジュールを分離しています。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースセンチメント（銘柄別）
    - regime_detector.py            # 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント + 保存ロジック
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETL 公開型（ETLResult 再エクスポート）
    - calendar_management.py        # マーケットカレンダー管理
    - news_collector.py             # RSS ニュース収集
    - quality.py                    # データ品質チェック
    - stats.py                      # 汎用統計ユーティリティ（zscore 等）
    - audit.py                      # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            # Momentum / Value / Volatility 等
    - feature_exploration.py        # IC / forward returns / 統計サマリー
  - ai/、data/、research/以下にさらに補助関数やユーティリティあり

---

## 設計上の注意事項（重要）
- Look-ahead Bias に配慮した設計: 多くの処理が target_date を明示的に受け取り、内部で現在時刻を直接参照しないよう設計されています。バックテストや研究での公平性に配慮してください。
- API リトライ / フェイルセーフ: 外部 API 呼び出しはリトライやフォールバック（失敗時はゼロやスキップ）を行い、パイプライン全体の停止を防ぐ設計です。ただし運用では例外ハンドリングやアラートを適切に設けてください。
- データベース（DuckDB）スキーマやテーブルの前提が存在します。ETL 前に必要なテーブル定義が用意されていることを確認してください（プロジェクトにスキーマ初期化スクリプトがある場合はそれを使用）。

---

## 貢献・ライセンス
- 本 README はコードベースの主要機能と利用方法の概要を示します。さらに詳細な API ドキュメントや実運用手順（デプロイ、監視、障害対応）は別途整備してください。
- 貢献方法やライセンス情報はリポジトリのトップレベル（LICENSE, CONTRIBUTING.md）を参照してください（存在する場合）。

---

必要に応じて、README に含めるサンプル .env.example やコマンドライン用の CLI 起動方法、より詳細なスキーマ定義（テーブル DDL）などを追加できます。どの部分を詳しく追記したいか教えてください。