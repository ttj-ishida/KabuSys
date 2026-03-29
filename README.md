# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）・ETL・ニュース集約・AIによるニュースセンチメント・市場レジーム判定・研究用ファクター計算・監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数（.env）
- ディレクトリ構成 / 主要モジュールの説明
- テスト・モックに関する補足

---

プロジェクト概要
- 日本株のデータパイプラインとリサーチ／売買基盤のための共通ユーティリティ群を提供します。
- データ取得（J-Quants）→ DuckDB 保存 → 品質チェック → 研究用ファクター計算 → AIでのニュース評価 → 市場レジーム判定 → 監査ログ（注文・約定トレース）といったワークフローをサポートします。
- 設計方針として、バックテストに有害なルックアヘッドバイアスを避ける（system 日付参照を限定する等）こと、ETL の冪等性、API 呼び出しに対する堅牢なリトライ／フォールバックを重視しています。

主な機能一覧
- data/
  - jquants_client: J-Quants API から株価・財務・カレンダーなどを取得し DuckDB に保存する（レート制御・リトライ・トークンリフレッシュ対応）。
  - pipeline: 日次 ETL の実行（差分取得、保存、品質チェック）。
  - news_collector: RSS 取得→前処理→raw_news に保存（SSRF 対策・サイズ制限・トラッキング除去）。
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）。
  - audit: 戦略→シグナル→発注→約定の監査テーブル定義と初期化ユーティリティ。
  - calendar_management: 営業日判定・次/前営業日の計算・カレンダー更新ジョブ。
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）。
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメント評価、ai_scores へ書き込み。
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存。
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算。
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク化ユーティリティ。

セットアップ手順
1. 必要環境
   - Python 3.10 以上（PEP 604 の union 型（|）などを使用しているため）
   - DuckDB（Python パッケージとしてインストール）
   - OpenAI Python SDK
   - defusedxml（RSS パース用）
   - その他（requests は直接使わないが標準ライブラリの urllib を使用）

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージのインストール（プロジェクトルートに pyproject.toml / setup.cfg 等がある前提）
   - 開発中に editable インストールする場合:
     ```bash
     pip install -e .
     ```
   - 依存を個別に入れる場合（例）
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env` と `.env.local` を置くと自動でロードされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（詳細は下記「環境変数」参照）

5. DB 初期化（監査ログ DB の初期化例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # 必要ならパスを作成
   ```

使い方（代表的なサンプル）
- DuckDB 接続の作成例（settings を用いる場合）
  ```python
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores に保存する
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # API キーは環境変数 OPENAI_API_KEY を使う
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームを判定して market_regime に保存する
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

環境変数（.env の主な項目）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時 data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL")

自動 .env ロード
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定の読み込み・検証（.env 自動ロードを含む）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを銘柄ごとに集約して OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - news_collector.py     — RSS 収集と raw_news 保存（SSRF 対策）
    - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py              — 監査（signal/order/execution）テーブル定義と初期化
    - calendar_management.py — カレンダー管理、営業日判定、calendar_update_job
    - stats.py              — 汎用統計（Zスコア等）
    - pipeline.py (ETLResult 再エクスポート含む)
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/*, ai/*, data/* 内にさらに多くのユーティリティ関数とヘルパーが存在します。

テスト・モックに関する補足
- OpenAI 呼び出しはモジュール内で _call_openai_api のような一箇所の関数を経由しており、テスト時は unittest.mock.patch で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api）。
- RSS の HTTP 操作は _urlopen をテストでモックして外部ネットワークに依存しないようにできます（kabusys.data.news_collector._urlopen を差し替え）。
- ETL／API 呼び出しの外部依存を切り離して単体テスト可能な設計になっています。

運用上の注意
- OpenAI 呼び出しや J-Quants API 呼び出しはコスト／レート制限があります。設定やリトライの挙動、ログを確認しながら運用してください。
- run_daily_etl は複数ステップから成り、各ステップは独立して例外処理されています。ETLResult を参照して品質問題やエラーの有無を確認してください。
- 監査ログ（audit）を利用することで、シグナルから約定までのトレーサビリティを確保できます。init_audit_db / init_audit_schema を適切に実行しておいてください。

最後に
- README に記載の使い方はライブラリ内部の関数をそのまま呼ぶ形の例です。運用アプリケーション（スケジューラ／オーケストレーション層）からこれらを呼び出して統合運用してください。
- 追加のドキュメント（StrategyModel.md、DataPlatform.md 等）に基づく実装注釈や設計ノートがコード内に多数あります。設計意図や安全策はコードコメントを参照してください。

ご要望があれば、README に CLI コマンド例、`.env.example` のテンプレート、あるいは具体的な初期化スクリプト（シェルスクリプト／Makefile）などを追記します。どの形式を優先しますか？