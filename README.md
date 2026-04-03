# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）、マーケットカレンダー管理、研究用ファクター計算などを含みます。

---

## できること（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日次OHLCV）・財務・上場情報・マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・品質チェックを行う日次 ETL パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS からニュースを収集し raw_news に保存（news_collector）
  - OpenAI（gpt-4o-mini）を使い、銘柄ごとのニュースセンチメント（ai_scores）を生成（score_news）
  - マクロニュース + ETF（1321）200日移動平均乖離で市場レジームを判定（bull/neutral/bear）（score_regime）
- 監査ログ（オーダー / 約定のトレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブルを生成・初期化（init_audit_schema / init_audit_db）
- マーケットカレンダー管理
  - JPX カレンダーの取得・保存、営業日判定・前後営業日検索などのユーティリティ
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、Zスコア正規化など
- データ品質チェック
  - 欠損・重複・スパイク・将来日付・非営業日データ等を検出

設計上のポイント:
- ルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカル DB 保持・冪等保存（ON CONFLICT）
- OpenAI / J-Quants の呼び出しはリトライ・バックオフやフェイルセーフを備える
- テスト容易性（API 呼び出しの差し替え箇所を明確化）

---

## 前提 / 要件

- Python 3.10+
- 依存パッケージ（主要）
  - duckdb
  - openai
  - defusedxml
- （他サポートライブラリは setup.py / pyproject.toml を参照）

---

## 環境変数（主な設定）

config.Settings から読み込まれる主要な環境変数：

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime 等で使用)
- kabuステーション API
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス等
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
- 監視・プロセス管理
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" でクリア）
- システム
  - KABUSYS_ENV = development | paper_trading | live（デフォルト development）
  - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` を自動で読み込みます。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

.env のパースはシェル風の簡易パーサに従います（コメントやクォート処理あり）。

---

## セットアップ手順

1. リポジトリをクローン、仮想環境を作成：
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）:
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはプロジェクトの pyproject.toml / requirements.txt に従う
   ```

3. パッケージを開発モードでインストール（任意）:
   ```
   pip install -e .
   ```

4. .env を用意（プロジェクトルート）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   `.env.local` はローカル上書きに使われます。

5. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API の例）

以下は基本的な利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダーの取得 → 株価 → 財務 → 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- ニュースセンチメント（銘柄ごとの AI スコア）を発生（score_news）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数にあること
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（score_regime）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  # OpenAI API キーを引数で渡すことも可能
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査用 DuckDB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが作成されます
  ```

- マーケットカレンダー操作（営業日判定）:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

---

## テスト・開発時の注意

- OpenAI / J-Quants の外部 HTTP コールはモック可能に設計されています。ユニットテストでは該当内部関数（例: kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api、kabusys.data.jquants_client._request 等）を patch して差し替えてください。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールが .env を読み込まなくなります（テスト用）。
- score_news / score_regime は API 呼び出し失敗時にフェイルセーフでスコアに 0 を用いる等の耐障害性が組み込まれていますが、API キー設定は必須です（ValueError が発生します）。
- DuckDB の executemany で空リストを渡すと失敗するバージョンがあるため、コード内で空チェックがされています。DB 操作の際は注意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースは `src/kabusys` 配下にあります。主なモジュール:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult 再エクスポート
    - news_collector.py      -- RSS ニュース収集
    - calendar_management.py -- マーケットカレンダー管理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログ（監査テーブル初期化）
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム・ボラ・バリュー計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリ等

（上記は主要ファイルのみ。詳細はソースツリーを参照してください）

---

## 開発者向けメモ

- 設計思想として「バックテストや研究環境でのルックアヘッドバイアス防止」が強く意識されています。target_date パラメータを明示して呼ぶ設計になっている関数が多く、内部で date.today() を参照しない実装が意図されています。
- 外部API呼び出し（OpenAI / J-Quants）はリトライ・バックオフ・HTTP ステータスに応じた挙動を持ちます。テスト時はこれらをモックして遅延やレート制限の影響を防いでください。

---

これで README の骨子です。必要であれば、環境別の .env.example、CI 用のテスト例、より具体的なコマンド例（ETL を cron で回す例や systemd ユニット例）を追加できます。どの部分を詳しく書き足しましょうか？