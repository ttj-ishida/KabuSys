# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレース）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・品質管理・リサーチ・AI スコアリング・監査ログ・発注監視までをカバーする内部ライブラリです。主な設計方針は以下です。

- Look-Ahead バイアスを避ける（内部で date.today() を無闇に参照しない設計）
- DuckDB をデータプラットフォームとして採用（軽量かつ高速）
- J-Quants API の差分取得・保存（冪等）を備えた ETL
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- ニュース収集時の SSRF 対策や XML パースの安全化（defusedxml）
- 監査ログ（signal → order_request → executions）で完全なトレーサビリティを確保

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）、財務、上場情報、JPX カレンダーを差分取得・保存
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック

- ニュース処理 / NLP
  - RSS 取得（SSRF 対策、gzip、トラッキングパラメータ除去）
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース＋ETF MA200 乖離を用いた市場レジーム判定（score_regime）

- リサーチ（ファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの初期化・管理
  - init_audit_db / init_audit_schema による冪等な初期化

- 外部クライアント
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ付）
  - OpenAI クライアント経由で JSON Mode を用いた安全な呼び出し

---

## 必要環境・依存

- Python >= 3.10（typing の `X | Y` 構文を使用）
- 主要依存パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI）

（プロジェクトの pyproject.toml / requirements.txt に依存バージョンを記載する想定です）

---

## セットアップ手順

1. リポジトリを取得してインストール（編集モードを想定）
   - pip を使う場合（プロジェクトルートに pyproject.toml または setup.py がある前提）:
     ```
     pip install -e .
     ```
   - 開発時に直接 `src` を PYTHONPATH に追加して利用することも可能:
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH
     ```

2. 必要パッケージをインストール:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしプロジェクトルートは .git または pyproject.toml を基準に探索）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

4. 実行に必要な主要環境変数（例）
   - J-Quants / API 関連:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - OpenAI:
     - OPENAI_API_KEY=<your_openai_api_key>
   - kabuステーション API:
     - KABU_API_PASSWORD=<password>
     - （Kabu API のベースURLは任意、デフォルト: http://localhost:18080/kabusapi）
   - Slack 通知:
     - SLACK_BOT_TOKEN=<token>
     - SLACK_CHANNEL_ID=<channel_id>
   - システム / DB パス（任意、省略時はデフォルト）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - 実行環境 / ログレベル:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  (default: INFO)

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（よく使う例）

以下はライブラリ API を直接呼ぶ最小例です。適宜 logging 設定やエラーハンドリングを追加してください。

- DuckDB 接続の作成（デフォルトのファイルパスを使用する場合）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を省略すると today（システム日）を使用
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコア化して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print(f"written {written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  # ":memory:" を渡すとインメモリ DB を作成
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェック実行
  ```python
  from kabusys.data.quality import run_all_checks
  from datetime import date

  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  # issues は QualityIssue のリスト（severity: "error" | "warning"）
  ```

---

## 補足: J-Quants クライアント / トークン

- jquants_client モジュールは id_token の自動取得（refresh token を使った POST）とページネーションに対応しています。
- get_id_token() は settings.jquants_refresh_token を参照します。ETL 実行時に id_token を直接引き渡すことも可能です（テスト用）。

---

## 注意点 / 設計上の挙動（重要）

- 多くの関数は「ルックアヘッドバイアス」を避けるため、内部で現在時刻（date.today()）を直接参照せず、呼び出し側で target_date を明示することを推奨します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは JSON Mode を使って厳密な JSON を返すようプロンプト設計されていますが、通信失敗やパース失敗時はフェイルセーフ（例: スコア=0.0）で継続する実装が多くあります。
- DuckDB の executemany は空リストを渡せないバージョン制約を考慮した実装があります（0.10 系）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

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
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit 用 DB 初期化ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/ (OpenAI を使った機能群)
- その他（execution / strategy / monitoring 等の名前空間は __all__ に含まれているが、今回の抜粋には全面実装が含まれていません）

---

## 開発 / テストに関して

- テスト時は一部のネットワーク呼び出し（OpenAI、HTTP fetch 等）をモックする想定です。各モジュール内でモックしやすいように _call_openai_api や URL オープン関数を関数単位で分離しています。
- DuckDB を利用した単体テストは ":memory:" を使うことで高速化できます（init_audit_db(":memory:") など）。

---

## ライセンス / 責任

本リポジトリに含まれるコードは内部運用用を想定した実装です。実際の発注や資金運用に使う場合は十分な検証と法的・運用上の確認を行ってください。本 README はコードベースの使用説明であり、投資助言を提供するものではありません。

---

もし README に追加したい「コマンドラインツールの仕様」「CI 設定」「具体的な .env.example のテンプレート」など要望があれば教えてください。必要に応じて README を拡張します。