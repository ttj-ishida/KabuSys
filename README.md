# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ニュース収集／NLP（OpenAI）や市場レジーム判定、ファクター計算、ETL、監査ログなどを含むモジュール群を提供します。

---

## 主要な特徴

- データ取得（J-Quants）と DuckDB に対する冪等保存（ON CONFLICT を利用）
- ニュース収集（RSS）および OpenAI を用いた銘柄別／マクロセンチメントのスコアリング
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM スコア）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（JPX カレンダー差分更新、営業日判定ユーティリティ）
- 監査ログ（signal / order_request / execution）の初期化・管理（DuckDB）
- 設計上の配慮：ルックアヘッドバイアス回避、API リトライとレート制限、SSRF 対策、フェイルセーフ

---

## 機能一覧（モジュール別ハイレベル）

- kabusys.config
  - 環境変数自動読み込み（.env / .env.local）と Settings クラス
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / ETLResult
  - news_collector: RSS 取得 / 前処理 / raw_news への保存
  - calendar_management: market_calendar 管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントスコア（OpenAI）
  - regime_detector.score_regime: 市場レジーム判定（MA200 + マクロLLM）
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. Python 環境を作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール（最小限）
   ※ プロジェクトの requirements.txt がない場合は下記を目安にインストールしてください。
   ```
   pip install duckdb openai defusedxml
   ```
   他に logging 等標準ライブラリ以外の依存がある場合は適宜追加してください。

3. 環境変数設定
   - リポジトリルートに `.env` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須環境変数（実行する機能によって必要なものが異なります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注機能利用時）
     - SLACK_BOT_TOKEN — Slack 通知用
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用途や別 DB、デフォルト: data/monitoring.db）

   サンプル `.env`（プロジェクトルートに `.env.example` を参考に作成してください）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの準備
   - ETL や audit 初期化関数を使ってスキーマを作成します（例は下記）。

---

## 使い方（基本例）

以下は Python インタプリタ / スクリプトからの利用例です。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成する（OpenAI API キーが設定されていること）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
  ```

- 監査ログ DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの duckdb 接続
  ```

- マーケットカレンダー周りユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- OpenAI 呼び出しを行う機能（news_nlp / regime_detector）は `OPENAI_API_KEY` を参照します。引数で明示的に api_key を渡すこともできます。
- 自動で .env を読み込む仕組みはプロジェクトルートを .git / pyproject.toml から検出するため、実行時の CWD に依存しません。テスト等で自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys 以下に主要コードがあります。主なファイルを抜粋すると:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema 初期化等)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

簡易ツリー:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 設計上の注意・運用メモ

- ルックアヘッドバイアス防止:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で date.today()/datetime.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや再現性のため、target_date を明示的に渡して使ってください。
- 冪等性:
  - データベース保存（raw_prices, raw_financials, market_calendar, ai_scores など）は ON CONFLICT や個別 DELETE→INSERT により冪等に実装されています。
- リトライ・レート制御:
  - J-Quants クライアントは固定間隔のレートリミッタとリトライ（指数バックオフ）を実装しています。OpenAI 呼び出しにもリトライロジックが実装されています。
- セキュリティ:
  - news_collector は SSRF 対策（スキーム検証・プライベートホスト検出・リダイレクト検査）や defusedxml を利用した XML パースで安全性を確保しています。
- フェイルセーフ:
  - LLM 呼び出しや API 失敗時にはゼロスコアやスキップで継続するなど、運用上の堅牢化がなされています。

---

## よくある質問 / トラブルシューティング

- .env が自動で読み込まれない
  - プロジェクトルートが .git や pyproject.toml で特定できない場合、自動ロードをスキップします。手動で環境変数を設定するか、カレントディレクトリをプロジェクトルートにしてください。
  - 自動ロード自体を無効化している（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）場合は解除してください。

- OpenAI 呼び出しでエラーが出る
  - API キーが正しくセットされているか確認。429/ネットワーク/5xx はリトライされますが、それでも失敗するとスコアは 0.0 でフォールバックされます。

- DuckDB にスキーマがない / テーブルがない
  - ETL 実行前にスキーマ初期化、あるいは使用するテーブルを作成する必要があります。監査ログ用には audit.init_audit_db を使用するとスキーマが作成されます。

---

## ライセンス / 貢献

本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在しない場合は運用ルールを追加してください）。

---

README は以上です。必要であれば、セットアップ時の具体的な requirements.txt、CI 設定、開発フロー（ローカル ETL 実行・デバッグ手順）などを追加で作成します。どの情報が欲しいか教えてください。