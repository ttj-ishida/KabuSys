# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース NLP（LLM を使ったセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能をモジュールごとに提供します。

主な用途の例:
- J-Quants から日次株価・財務・マーケットカレンダーを差分取得して DuckDB に格納
- RSS 収集 → ニュースを LLM でスコアリングして ai_scores に保存
- ETF とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定
- ファクター作成・IC 計算などリサーチ用途
- 発注フローの監査ログ（audit テーブル群）を DuckDB で保持

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` 自動ロード（プロジェクトルート検出、無効化可能）
  - 必須設定の取得・検証（`kabusys.config.settings`）

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの差分取得（株価 / 財務 / カレンダー）
  - 差分保存（冪等な ON CONFLICT 処理）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集 / NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS から記事収集（SSRF/トラッキング除去対策）
  - LLM（OpenAI）を使った銘柄別センチメント評価（バッチ・リトライ・バリデーション）
  - ai_scores テーブルへの書き込み

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離とマクロセンチメントを組み合わせて日次でレジーム判定

- 研究用ユーティリティ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、発注フローのトレーサビリティ向け DDL と初期化ユーティリティ

- データクライアント（kabusys.data.jquants_client）
  - J-Quants API 通信（認証・リトライ・レートリミット管理）
  - fetch/save 関数（daily_quotes、financial_statements、market_calendar、listed_info）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール  
   ※このコードベースで使われている主な外部依存:
   - duckdb
   - openai (OpenAI Python SDK)
   - defusedxml
   その他標準ライブラリのみで実装されている部分もあります。requirements.txt がある場合はそれを利用してください。なければ最低限以下をインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定  
   必須・主要な環境変数（`kabusys.config.Settings` に基づく）:
   - JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
   - OPENAI_API_KEY（LLM を使う場合、score_news / score_regime）（必須または関数呼び出しで渡す）
   任意:
   - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると `.env` の自動ロードを無効化できます。

   環境変数はプロジェクトルートの `.env` / `.env.local` から自動ロードされます（`.git` あるいは `pyproject.toml` を基準にプロジェクトルートを探索）。手動で export しても構いません。

5. データディレクトリ作成（デフォルトパスを使う場合）
   ```
   mkdir -p data
   ```

---

## 使い方（基本的な例）

以下は Python スクリプトや REPL での簡単な利用例です。各関数は duckdb 接続を受け取るため、データベース接続を生成して渡します。

- DuckDB 接続の作成（デフォルトファイル: data/kabusys.duckdb）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # または ":memory:"
  ```

- 日次 ETL を実行（J-Quants トークンは settings から自動取得）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # conn は duckdb 接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ関数（例: モメンタム計算）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  # momentum: list[dict] を解析して利用
  ```

注意事項:
- LLM を使う関数（score_news / score_regime）は OpenAI API キーを要求します。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL・保存処理は DuckDB のスキーマ（テーブル定義）が必要です。スキーマ初期化のユーティリティが別にある場合はそれを実行してください（本リポジトリ内に schema 初期化関数がある想定）。
- 各モジュールは Look-ahead バイアス防止のため、内部で date.today() を直接参照しない方針で設計されています。バックテスト用途では対象日を明示的に渡してください。

---

## 設定（環境変数の概略）

主要な設定は `kabusys.config.settings` で取得します。主なプロパティ:

- jquants_refresh_token → JQUANTS_REFRESH_TOKEN
- kabu_api_password → KABU_API_PASSWORD
- kabu_api_base_url → KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- line_channel_access_token → LINE_CHANNEL_ACCESS_TOKEN
- line_user_id → LINE_USER_ID
- duckdb_path → DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- sqlite_path → SQLITE_PATH（デフォルト data/monitoring.db）
- pid_file_path → PID_FILE_PATH（デフォルト data/execution.pid）
- kill_flag_path → KILL_FLAG_PATH（デフォルト data/kill.flag）
- kill_flag_clear_on_start → KILL_FLAG_CLEAR_ON_START（"1" で True）
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct（監視用閾値）
- env → KABUSYS_ENV（development / paper_trading / live）
- log_level → LOG_LEVEL（DEBUG/INFO/...）

設定が不足している必須キーを取得すると ValueError が発生します。`.env.example` を参考に `.env` を作成してください（自動ロード機能あり）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他 ETL/クライアント関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (予想される監視関連モジュール: present in __all__ but not enumerated above)
  - strategy/ (戦略関連モジュール: present in __all__)
  - execution/ (発注実行関連: present in __all__)

（上はコードベースの主要ファイルを抜粋しています。完全な木はリポジトリを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- 本リポジトリの API 呼び出し部分はネットワーク／API の障害を考慮したリトライ／フォールバックを実装していますが、運用では API レートやコスト、API キーの管理に注意してください。
- LLM の出力は外部サービスに依存します。応答形式の変化に備えたバリデーションが実装されていますが、運用前に十分な監視・ログを用意してください。
- DuckDB に対する大量データの書き込みはトランザクションの取り扱いに注意してください。executemany に空リストを渡せないバージョンの互換性対策がコード内にあります。
- 監査ログ（audit）テーブルは削除しない前提で設計されています。データ保持とバックアップのポリシーを決めてください。

---

## 貢献・拡張

- 新しい ETL のソース追加、他ブローカー API への発注コネクタ追加、戦略の追加はモジュール単位で実装・追加できます。
- テスト: 各モジュールは外部依存（HTTP 呼び出し・OpenAI 呼び出し）を注入可能になっている箇所があり、モックを使った単体テストがしやすい設計です。

---

必要に応じて README に追記します。たとえば:
- requirements.txt の内容
- DuckDB スキーマ初期化手順（schema SQL）
- サービスとしての実行方法（systemd / supervisor 例）
など、ご希望があれば具体的に追加します。