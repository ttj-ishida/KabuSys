# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。本リポジトリはデータ収集（J-Quants / RSS）、ETL、データ品質チェック、研究向けファクター計算、AIによるニュースセンチメント評価、市場レジーム判定、監査ログ（発注〜約定トレース）などを含むモジュール群で構成されています。

## 主な特徴
- J-Quants API からの株価・財務・上場情報取得（ページネーション、リトライ、レート制御）
- DuckDB を用いた冪等的なデータ保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF の 200 日 MA とマクロニュースを組合せ）
- 研究用ファクター群（モメンタム / バリュー / ボラティリティ）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）を保存する監査用スキーマ初期化ユーティリティ
- セキュリティ考慮（SSRF 対策、XML Defuse、API 再試行、バックオフ等）

---

## 機能一覧（抜粋）
- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local）と設定 accessor（settings）
- kabusys.data.jquants_client
  - fetch / save 系関数（daily_quotes, financial_statements, market_calendar, listed_info）
  - 認証（get_id_token）とレート制御
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult レポート
- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
- kabusys.data.news_collector
  - RSS 収集、前処理、raw_news への冪等保存（SSRF／サイズ制限あり）
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)：銘柄ごとの ai_score を ai_scores テーブルへ書き込み
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)：市場レジーム（bull/neutral/bear）を market_regime に書き込み
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - init_audit_schema / init_audit_db：監査ログ用スキーマと DB 初期化
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 要件
- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリの urllib, json, datetime 等

依存関係はプロジェクト側で管理してください（requirements.txt / pyproject.toml など）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo_url>
   cd <repo_dir>
   ```

2. Python 環境準備（仮想環境推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要ライブラリをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用）

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - 以下の環境変数は本システムで参照されます（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必要）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI を使用する機能（score_news / score_regime）で必要
   - 既定の DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb（settings.duckdb_path）
     - SQLITE_PATH: data/monitoring.db（settings.sqlite_path）
   - 環境変数はルートの .env / .env.local に置くことができます。パッケージは起点ファイルからプロジェクトルートを探索して自動的に .env を読み込みます。
   - 自動 .env ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   例：.env（サンプル）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下はいくつかのよく使うユースケースのサンプルです。

- DuckDB 接続を作成して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）を実行して ai_scores に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で設定
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で設定
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って audit テーブルにアクセスできます
  ```

- 設定値へのアクセス
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- AI 関連の API 呼び出しは OpenAI の API キーを必要とします。テスト時は各モジュール内の _call_openai_api をモックして外部呼び出しを抑止できます（unittest.mock.patch を利用）。
- run_daily_etl 等は内部で日付判定やカレンダー取得を行います。バックテスト時のルックアヘッド回避に設計されているため、明示的に target_date を指定してください。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 下の主なモジュール一覧です（抜粋）。

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
  - research/*（ファクター計算・統計ユーティリティ）
  - その他: strategy/, execution/, monitoring/（パッケージ公開対象として __all__ に定義）

この README に含まれていないサブモジュールも多数あります。各モジュールにはドキュメンテーション文字列（docstring）が豊富に付与されていますので、個別の関数やクラスの詳細は該当ファイルを参照してください。

---

## 実践的注意・設計上のポイント
- ルックアヘッドバイアス対策: 多くの関数は date.today() や datetime.now() を直接参照せず、必ず引数で日付を受け取る設計です。バックテストで使用する際は target_date を明示してください。
- 冪等性: ETL・保存処理は可能な限り ON CONFLICT / DELETE → INSERT の形で冪等になるよう設計されています。
- フェイルセーフ: AI API の失敗等は例外とならずデフォルト値（0.0 等）にフォールバックする処理が多く、運用中の致命的停止を抑制します。ただしログを確認して原因を把握してください。
- テスト容易性: API 呼び出しやネットワーク処理は内部で独立したヘルパー関数に切り出してあり、単体テストで差し替え（モック）が可能です。

---

## 開発・コントリビューション
- コードスタイル・型アノテーションが充実しています。変更を加える際は既存の設計方針（docstrings に記載）を尊重してください。
- 外部 API Key / 秘密情報は直接コミットしないでください。.env.local に置き gitignore する運用を推奨します。
- 変更時はユニットテスト（モック）を追加し、API 呼び出し部分は外部を叩かないようにしてください。

---

必要があれば、README に以下の追加情報を含めます:
- 具体的なテーブルスキーマ（raw_prices, raw_news, ai_scores, market_regime など）
- pyproject.toml / setup の例
- よくあるトラブルシューティング（OpenAI レスポンスパースエラー、DuckDB executemany の注意点など）

どの追加情報が必要か教えてください。