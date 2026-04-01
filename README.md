# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）など、アルゴリズム取引／調査に必要な共通機能群を提供します。

現在のバージョン: 0.1.0

---

## 主な機能一覧

- 環境変数/設定読み込み（.env / .env.local 自動読み込み、テスト時に無効化可）
- J-Quants API クライアント（株価日次 / 財務 / マーケットカレンダーの取得、保存）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメント評価、ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions 等）と初期化ユーティリティ
- 汎用統計ユーティリティ（Zスコア正規化等）

---

## 動作要件（概略）

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード 等）
- 環境変数に各種 API トークンを設定すること

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）
2. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements file があれば pip install -r requirements.txt
4. パッケージをインストール（編集開発時）
   - pip install -e .
5. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env/.env.local を置くと自動読み込みされます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨 Python バージョンや追加の依存はプロジェクトの pyproject.toml や CI 設定を参照してください。

---

## 必須（または主要）環境変数

- J-Quants（データ取得）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- kabuステーション（発注・口座API）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (score_news / regime_detector などのデフォルト参照先)
- Slack（通知等）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベース / 監視
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
- システム設定
  - KABUSYS_ENV : development / paper_trading / live (デフォルト: development)
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: Settings クラスは自動的に .env / .env.local ファイルをプロジェクトルートから読み込みます（OS環境変数が優先）。.env の書式は shell の export/KEY=val 等に対応しています。

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト中での典型的な使い方例です。

- 基本的な準備（DuckDB 接続を得る）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（差分取得・保存・品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア算出（OpenAI 必須）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import os

  # api_key を引数に渡すか、OPENAI_API_KEY を環境変数で設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジームスコア算出（ETF 1321 + マクロニュース）

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import os

  score_regime(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
  ```

- 監査ログ用 DuckDB 初期化（監査専用 DB）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査ログテーブルにアクセスできます
  ```

- 研究用ファクター計算の呼び出し例

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

各関数はドキュメント文字列（docstring）に詳細な挙動・引数・戻り値・副作用が書かれています。関数を呼ぶ前に DuckDB の該当テーブル（raw_prices / raw_news / raw_financials / market_calendar 等）が存在し、想定するスキーマでデータが入っていることを確認してください。

---

## 設計上の注意点 / 動作上の方針

- ルックアヘッドバイアス対策
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today()/date.today() を無意味に参照せず、外部から target_date を与える設計です。バックテストなどで必ず target_date を明示してください。
- 冪等性
  - J-Quants データ保存やニュースの保存は DB 側で ON CONFLICT や明示的な排他処理を行い、複数回の実行で重複を避けるように設計されています。
- フェイルセーフ
  - LLM や外部 API が使えない・失敗した場合でも例外でプロセスを終了させず、フォールバック値（スコア 0.0 等）で継続する設計箇所があります（運用上の監視は必要です）。
- テスト容易性
  - OpenAI 呼び出し等は内部で関数化されており、ユニットテスト時は patch / mock で差し替え可能です。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                   — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメント（OpenAI 利用）
  - regime_detector.py        — 市場レジーム判定（MA + マクロセンチメント合成）
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得・保存）
  - pipeline.py               — ETL パイプライン（差分取得・品質チェック）
  - etl.py                    — ETLResult 再エクスポート
  - news_collector.py         — RSS ニュース収集（SSRF 対策・前処理）
  - calendar_management.py    — マーケットカレンダー管理（営業日判定等）
  - quality.py                — データ品質チェック
  - stats.py                  — 統計ユーティリティ（z-score 等）
  - audit.py                  — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py        — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py    — 将来リターン/IC/統計サマリー
- ai/（ニュース/レジームは上記参照）
- その他モジュール（strategy, execution, monitoring 等はパッケージ API で想定）

（README では主要なモジュールのみ列挙しています。詳細はソースコードの docstring を参照してください。）

---

## 開発・運用上のヒント

- ローカル開発時は .env.local に秘密トークンを置き、本番は OS 環境変数を優先してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テストで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは課金対象となるため、テストではモックを使用してください。内部の _call_openai_api を patch すると便利です。
- DuckDB を使用するため、並列で同一ファイルを開く場合のロックや接続管理に注意してください。大規模運用では接続を適切に再利用してください。
- J-Quants API のレート制限やエラー挙動に合わせたリトライ/スロットリングが実装されていますが、過度な同時実行は避けてください。

---

## 貢献・拡張

- 新しい ETL ソースやニュースソースを追加する場合は、既存の jquants_client と同様に fetch/save のパターンに合わせて実装してください。
- OpenAI のモデルやプロンプト改善は news_nlp / regime_detector の SYSTEM_PROMPT を見直すことで可能です。API エラーや不正レスポンスに対するロバストネスを維持してください。

---

補足・問い合わせがあれば、どの機能（ETL／NLP／レジーム判定／監査ログ等）について詳しく知りたいか教えてください。README の補足や具体的な使用例（スクリプト、Dockerfile、CI 設定など）を追加で用意します。