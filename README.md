# KabuSys

日本株向け自動売買・データ基盤ライブラリ兼ツール群

KabuSys は日本株のデータ収集（ETL）・データ品質チェック・特徴量計算（リサーチ）・ニュースの NLP（LLM を用いたセンチメント）・市場レジーム判定・監査ログ（トレーサビリティ）など、自動売買システムに必要な基盤処理をまとめた Python モジュール群です。DuckDB をデータ層に採用し、J-Quants API / RSS / OpenAI 等と連携して日次 ETL や分析処理を行います。

注意:
- バックテストや本番運用で利用する際は、設定・権限・APIキーの取り扱いに注意してください。
- モジュール設計は「ルックアヘッドバイアス防止」や「冪等性（idempotency）」を意識しています（README 後述の各関数説明参照）。

---

## 主な機能一覧

- データ ETL（J-Quants API からの株価・財務・マーケットカレンダー取得）
  - 差分取得、ページネーション、トークン自動リフレッシュ、レートリミット対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL の統合エントリーポイント（run_daily_etl）

- データ品質チェック
  - 欠損、重複、株価スパイク、日付整合性チェック
  - QualityIssue 型で問題を集約（重大度 error/warning）

- ニュース収集 & 前処理
  - RSS フィードから記事収集（SSRF 対策、トラッキング除去、XML の安全パース）
  - raw_news / news_symbols への保存ロジック（冪等）

- ニュース NLP（OpenAI）
  - 銘柄単位のニュース統合センチメント（score_news）
  - LLM のレスポンス検証、バッチ送信、リトライ（429 / ネットワーク等）

- 市場レジーム判定（AI + テクニカル）
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して
    市場レジーム（bull/neutral/bear）を判定（score_regime）

- リサーチ用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算関数（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ、Z-score 正規化

- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用スキーマ初期化（init_audit_schema / init_audit_db）
  - UUID ベースの冪等・ステータス管理

- 市場カレンダー管理
  - JPX カレンダー更新ジョブ（calendar_update_job）
  - 営業日判定 / 前後営業日取得 / 期間内営業日リスト取得

---

## 動作要件（推奨）

- Python 3.10 以上（型ヒントの | 演算子等を使用）
- 必要なライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード 等）
- 環境変数で API キーやパスを設定

（プロジェクト配布状態に合わせて pyproject.toml / requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 例（pip）
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージ一覧がある場合は requirements.txt を利用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` ファイルを置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロード無効）。
   - 必須 / よく使う環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD : kabuステーション API パスワード
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 通知用（任意）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 監視用設定
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値
     - KABUSYS_ENV : environment ("development" / "paper_trading" / "live")
     - LOG_LEVEL : ログレベル ("DEBUG","INFO",...)

   - .env の書式は shell 型（export を前置可能）・コメント対応・クォート対応しています。

5. データベース初期化（必要に応じて）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
     ```
   - 既存の DuckDB 接続に監査スキーマのみ追加する場合:
     ```python
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主な API と例）

以下は Python REPL / スクリプトからの直接利用例です。各関数は DuckDB の接続オブジェクトを受け取る設計になっています。

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（LLM）でスコア付け（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("scored:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（リサーチ）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 品質チェックを手動実行
  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- カレンダー更新ジョブ（夜間バッチ等で実行）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved calendar rows:", saved)
  ```

備考:
- OpenAI 呼び出しは API キーが必須です（api_key 引数、または環境変数 OPENAI_API_KEY）。
- ETL / AI 関連の処理は外部 API を呼ぶためネットワーク障害やレート制限を考慮してリトライとフェイルセーフが実装されています。失敗時はログに記録され、フェイルセーフ値（例: macro_sentiment=0.0）が用いられることがあります。

---

## 設計上の注記（重要）

- ルックアヘッドバイアス防止: 多くの関数は内部で date.today() / datetime.today() を参照せず、引数として与えられる基準日（target_date）に基づいて処理します。これによりバックテストでの未来情報漏洩を防止しています。
- 冪等性: DB への保存処理は可能な限り ON CONFLICT / UPSERT を用いた冪等設計です。
- フェイルセーフ: 外部 API が失敗した場合、システムを完全停止させず継続できるようにデフォルト値で処理を続行するロジックが多くあります（ただし重要変数が無ければ例外を出します）。
- セキュリティ: RSS 収集では SSRF 対策（ホスト/IP のチェック、リダイレクト検査）、defusedxml による XML パース等を実装しています。

---

## ディレクトリ構成（主要ファイル）

（package ルートは src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（LLM 統合）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 結果クラスの再エクスポート
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（z-score 正規化）
    - calendar_management.py        — 市場カレンダー管理
    - audit.py                      — 監査ログ（トレーサビリティ）初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — 将来リターン・IC・統計サマリ
  - monitoring/ (注: README に記載されているがコードベースに監視系がある場合の想定)
  - strategy/ (戦略層を配置する想定)
  - execution/ (発注層を配置する想定)

（リポジトリの完全なファイルツリーは各プロジェクトの配布物を参照してください）

---

## ロギングと運用

- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 環境に応じて KABUSYS_ENV を設定（development / paper_trading / live）。is_live/is_paper/is_dev が Settings 経由で参照可能です。
- 実運用ではプロセス監視（PID ファイル・KILL フラグ）やリソース閾値（CPU/MEM/DISK）監視を組み合わせてください（設定項目は config.Settings に定義あり）。

---

## テスト / 開発時のヒント

- 環境変数の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（ユニットテスト等で有用）。
- OpenAI 呼び出しやネットワーク I/O は内部で関数単位に切り替え可能（テスト時にモック可能）。各モジュール内で _call_openai_api や _urlopen を patch できます。
- DuckDB を使った関数はインメモリ DB (":memory:") で素早くテストできます。

---

## ライセンス / 貢献

この README はコードベースの説明用テンプレートです。実際のライセンス・貢献ポリシーはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README に次の項目も追加できます：
- .env.example のテンプレート
- 具体的なユースケース別ワークフロー（ETL スケジューリング、戦略 → 発注の流れ図）
- CI / テスト実行手順（pytest 等）
- 依存パッケージの正確なバージョン要件（pyproject.toml / requirements.txt に基づく記載）

追加で盛り込みたい情報があれば教えてください。