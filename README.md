# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログといった要素を含む、バックテスト／自動売買プラットフォームのコンポーネント群です。  
主に以下の用途を想定しています：

- J-Quants API を用いた株価／財務／マーケットカレンダーの差分 ETL
- ニュース収集（RSS）と LLM による銘柄別センチメント算出
- マーケットレジーム判定（ETF の MA とマクロニュースの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）とリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注〜約定までを追跡する監査（audit）スキーマの初期化・操作

コードは DuckDB をメインのオンディスクデータベースとして想定し、OpenAI（gpt-4o-mini）など外部 API と連携します。

---

## 主な機能一覧

- ETL
  - J-Quants からの株価日足・財務データ・マーケットカレンダーの差分取得（ページネーション対応、リトライ、レート制御）
  - ETL 実行結果の集約（ETLResult）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合の検出
- ニュース収集 & NLP
  - RSS からのニュース収集（SSRF対策・トラッキング除去・gzip・XML攻撃対策）
  - OpenAI を利用した銘柄別ニュースセンチメント（ai_scores）算出（バッチ化・リトライ・レスポンス検証）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して daily の market_regime を書き込み
- 研究用ユーティリティ（research）
  - momentum / value / volatility のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - 監査用の独立した DuckDB 初期化関数

---

## セットアップ手順

以下はローカル開発向けの一般的な手順です。プロジェクトに合わせて適宜調整してください。

1. Python（推奨: 3.9+）を用意する。
2. 仮想環境を作成・有効化：
   - unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .\.venv\Scripts\activate
3. 必要パッケージをインストール（例: duckdb / openai / defusedxml 等）。requirements.txt がある場合はそれを使用してください。
   - 例:
     - pip install duckdb openai defusedxml
     - または（プロジェクトをパッケージ化している場合）pip install -e .
4. 環境変数（または .env ファイル）の準備  
   自動でプロジェクトルートの `.env` と `.env.local` をロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
   必須と思われる環境変数（用途に応じて設定）:
   - JQUANTS_REFRESH_TOKEN        — J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY               — OpenAI API キー（news_nlp / regime_detector）
   - KABU_API_PASSWORD            — kabuステーション API パスワード（発注等）
   - SLACK_BOT_TOKEN              — Slack 通知用 Bot トークン（必要なら）
   - SLACK_CHANNEL_ID             — Slack チャンネル ID（必要なら）
   オプション:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB 用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/…）

   例 .env（実運用では機密情報を管理してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   ```

5. DuckDB ファイルディレクトリを作成（自動作成される関数もありますが明示的に）:
   - mkdir -p data

注意事項:
- 自動ロードを無効にしてユニットテストを行うには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や J-Quants API を使用する処理は各サービスの課金やレート制限に注意して実行してください。

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト例です。必要に応じてエラーハンドリングやログ設定を追加してください。

- ETL（日次 ETL を実行）:
  ```python
  import duckdb
  import datetime
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア算出（news_nlp.score_news）:
  ```python
  import duckdb
  import datetime
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written_count = score_news(conn, target_date=datetime.date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written_count}")
  # api_key を明示する場合: api_key="sk-..."
  ```

- 市場レジーム判定（regime_detector.score_regime）:
  ```python
  import duckdb
  import datetime
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=datetime.date(2026, 3, 20))
  ```

- 監査 DB 初期化（audit テーブルの作成）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # または既存接続に対して init_audit_schema(conn)
  ```

- 研究用：モメンタム / ボラティリティ計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=datetime.date(2026,3,20))
  ```

ログレベルは環境変数 LOG_LEVEL で制御できます（Settings.log_level）。

---

## 主要 API / モジュール一覧（簡易）

- kabusys.config
  - Settings：環境変数の取得・バリデーション、自動 .env ロード
- kabusys.data
  - jquants_client.py：J-Quants API の fetch/save 系とレート制御・リトライ
  - pipeline.py：run_daily_etl / run_*_etl と ETLResult
  - news_collector.py：RSS 収集・前処理・保存
  - calendar_management.py：マーケットカレンダーの判定・更新ジョブ
  - quality.py：データ品質チェック
  - stats.py：zscore_normalize 等の統計ユーティリティ
  - audit.py：監査スキーマ DDL と初期化ユーティリティ
- kabusys.ai
  - news_nlp.py：news を LLM でスコアリングして ai_scores を書き込む
  - regime_detector.py：MA とマクロニュースで日次市場レジームを判定
- kabusys.research
  - factor_research.py：モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py：将来リターン・IC・統計サマリー
- kabusys (パッケージ初期化)
  - __init__.py（バージョン管理と公開モジュール）

---

## ディレクトリ構成

（リポジトリの主要ファイルを抜粋・説明付きで列挙）

- src/kabusys/
  - __init__.py — パッケージエントリ（__version__ 等）
  - config.py — 環境変数 / .env 自動ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリングロジック
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS フィード取得と前処理
    - calendar_management.py — マーケットカレンダーの操作・更新ジョブ
    - quality.py — データ品質チェック群
    - stats.py — zscore_normalize 等汎用統計ユーティリティ
    - audit.py — 監査ログ用 DDL / 初期化関数
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 計算
    - feature_exploration.py — forward returns / IC / rank / summary
  - research/*その他モジュール*
- そのほか（プロジェクトルート）
  - .env / .env.local（任意、機密情報）
  - data/（デフォルトの DB 保存先）
  - pyproject.toml / setup.cfg / requirements.txt（プロジェクトに応じて）

---

## 運用上の注意点・設計上の要点

- Look-ahead bias 回避：
  - モジュール群は target_date を引数に受け取り、内部で datetime.today() を利用しない設計が多く採用されています。バックテスト等で過去日時を入力してもリークしないように配慮されています。
- 冪等性：
  - J-Quants からの保存処理は INSERT ... ON CONFLICT DO UPDATE により冪等に実装されています。
- 外部 API とリトライ：
  - OpenAI / J-Quants の呼び出しはリトライ・指数バックオフ・500 系の扱い・レート制御が実装されています。
- セキュリティ：
  - RSS 取得では SSRF 対策（リダイレクト先検査・プライベートアドレス拒否）や XML の defusedxml を利用しています。
- テスト容易性：
  - OpenAI 呼び出しなどは内部関数をモックしやすいように抽象化されています（ユニットテストでの差し替えを想定）。

---

## サポート / 開発のヒント

- ログは標準の logging を利用しています。LOG_LEVEL を設定して挙動を確認してください。
- 単体関数は DuckDB 接続を直接引数で受けるためテスト用に in-memory DuckDB を使うと良いです（duckdb.connect(":memory:")）。
- OpenAI 呼び出しをローカルで試す際は利用料に注意してください。テストはモック推奨です。

---

必要であれば次の内容を追加します：
- .env.example の完全なテンプレート
- 依存パッケージ一覧（requirements.txt 形式）
- より詳細なコマンドライン実行例や systemd / cron によるバッチ実行例

追加したい情報や書式指定があれば教えてください。