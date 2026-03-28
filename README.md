# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を使用したセンチメント解析）、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを含みます。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分/バックフィルロジック、レートリミット・リトライ実装、Idempotent 保存（ON CONFLICT）
- ニュース収集
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news テーブルへの冪等保存
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（news_nlp）
  - マクロニュースと ETF MA200 乖離を合成して市場レジーム判定（regime_detector）
- リサーチ（ファクター計算）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン算出、IC（Spearman）計算、Zスコア正規化等
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェックと QualityIssue レポート
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、環境変数ラッパー（kabusys.config.settings）

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ＋urllib 等）

※ 実行環境により追加パッケージが必要になる場合があります。プロジェクトの package/dependency 管理に合わせてインストールしてください。

---

## 環境変数（主なもの）

このライブラリは環境変数で多くを設定します。最低限必要な変数：

- JQUANTS_REFRESH_TOKEN  
  - J-Quants API 用のリフレッシュトークン（必須）
- KABU_API_PASSWORD  
  - kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN  
  - Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID  
  - Slack チャネル ID（必須）
- OPENAI_API_KEY  
  - OpenAI 呼び出しに使用（news_nlp / regime_detector 等）
- DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）  
  - DuckDB のファイルパス
- SQLITE_PATH（任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意、デフォルト: development）  
  - 有効値: development / paper_trading / live
- LOG_LEVEL（任意、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト等で利用）

.env/.env.local をプロジェクトルートに置くと、自動で読み込まれます（.git または pyproject.toml をプロジェクトルート検出に使用）。

---

## セットアップ手順（例）

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成＆有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   - ここでは一例（実際はプロジェクトの requirements.txt / pyproject.toml に従ってください）
   ```
   pip install duckdb openai defusedxml
   pip install -e .
   ```

4. 環境変数を設定（例 .env）  
   .env.example を参考に .env を作成してください。主要変数は上記参照。

---

## 使い方（主要ユーティリティと例）

以下はライブラリの代表的なユースケース例です。適宜ロギング設定やエラーハンドリングを追加してください。

- DuckDB 接続の準備（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）スコアリング（news_nlp.score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数で設定しておく
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))  # 要 OPENAI_API_KEY
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

---

## 注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止のため、多くの関数は内部で date.today() を参照せず、呼び出し側が target_date を指定することを前提にしている。
- OpenAI 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0）を含む。
- J-Quants クライアントはレートリミット、リトライ、トークン自動リフレッシュを実装。
- ニュース収集は SSRF 対策、XML の安全処理（defusedxml）、受信サイズ制限等を実装。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT）を意識した設計。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル／モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（銘柄別スコア）
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                      — ETL パイプライン（run_daily_etl など）
    - etl.py                           — ETL インターフェース再エクスポート
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理・ユーティリティ
    - quality.py                       — データ品質チェック
    - stats.py                         — 汎用統計ユーティリティ（z-score など）
    - audit.py                         — 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py               — Momentum/Value/Volatility 等
    - feature_exploration.py           — forward returns, IC, summary, rank
  - ai/、data/、research/ の各モジュールが主要ロジックを提供

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下のファイルを参照してください）

---

## よくある操作・デバッグ

- .env の自動読み込みを無効化したいとき:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- ログレベルを上げたいとき（例: デバッグ出力）:
  ```
  export LOG_LEVEL=DEBUG
  ```
- OpenAI 呼び出しをテスト時にモックする場合、モジュール内部の _call_openai_api を patch してください（news_nlp/regime_detector で別々に定義されています）。

---

必要に応じて README を拡張して、CI / 起動スクリプト、運用手順（発注フロー）、Slack 通知の設定例、テスト方法などを追加できます。追加してほしい項目があれば教えてください。