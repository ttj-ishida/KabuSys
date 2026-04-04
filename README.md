# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）・ニュース収集・AIニューススコアリング・市場レジーム判定・リサーチ（ファクター計算）・監査ログなどを含む、バックテスト／運用用の共通処理群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・カレンダーデータを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事 ↔ 銘柄の紐付け
- OpenAI を使ったニュース単位およびマクロセンチメントのスコアリング（gpt-4o-mini を想定）
- ETF（1321）やニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム・ボラティリティ・バリュー等）の計算と特徴量探索ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査（発注 → 約定のトレーサビリティ）
- kabuステーション（ローカル発注）や LINE 通知などのための設定管理

設計上の共通方針として、ルックアヘッドバイアスを避ける（内部で date.today() を無条件に参照しない）、DB への書き込みは冪等性を重視する、外部 API 呼び出しはリトライやレート制御を入れる等が採用されています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存関数、トークン自動リフレッシュ、レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（監査テーブル・インデックス作成）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースを合成して market_regime に書き込み
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env 自動読み込み（プロジェクトルートに .env / .env.local がある場合）
  - 環境変数経由で各種設定（J-Quants トークンや OpenAI キー、DB パス、監視しきい値等）を管理

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. 仮想環境を作成・有効化（任意）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストールします。リポジトリに requirements.txt がない場合、代表的な依存例は以下です（実プロジェクトでは pyproject.toml / setup.cfg を参照してください）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   または、パッケージをローカルで編集可能インストールする場合:
   ```bash
   pip install -e .
   ```

4. 環境変数の準備:
   プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` を置くと自動的に読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   例 `.env`（最低限必要な値）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - LINE やその他の設定は任意で追加できます（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等）。

5. データ保存先ディレクトリ（例: data/）を作成しておきます:
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下はライブラリを直接 Python から利用する簡単な例です。実行前に設定（環境変数 / .env）を整えてください。

- DuckDB 接続・ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーを環境変数に設定するか、api_key 引数で渡す）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査DBの初期化（監査ログ用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以降、order_requests / signal_events / executions を使用可能
  ```

- ファクター計算（リサーチ用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  momentum = calc_momentum(conn, d)
  value = calc_value(conn, d)
  volatility = calc_volatility(conn, d)
  ```

注意点:
- OpenAI 呼び出しはレスポンスが厳密 JSON で返ることを期待しています。API エラーやパースエラーはフェイルセーフ動作（ゼロスコアやスキップ）にフォールバックしますが、ログを確認してください。
- J-Quants API 呼び出しは rate limiter とリトライを備えています。認証はリフレッシュトークン経由で行います（JQUANTS_REFRESH_TOKEN を .env に設定）。

---

## 環境変数（主な項目）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須。config.Settings.jquants_refresh_token）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
- KABU_API_PASSWORD: kabu API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

config.Settings クラスからこれらを安全に参照できます（不足時は ValueError を発生させる必須項目もあります）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / .env ロード・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュース NLP スコアリング（score_news）
    - regime_detector.py         -- マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（fetch / save）
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py          -- RSS 収集・前処理
    - quality.py                 -- データ品質チェック
    - stats.py                   -- zscore_normalize 等
    - etl.py                     -- ETLResult 再エクスポート
    - audit.py                   -- 監査ログテーブル作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py     -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/（その他の補助モジュール）
  - monitoring / execution / strategy モジュールは __all__ に含まれる想定（実装は別）

---

## 実運用・開発上の注意

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。
- OpenAI 呼び出しにはリトライとフォールバック（失敗時スコアを 0.0 とする）が実装されていますが、API コストやレートには注意してください。
- DuckDB への INSERT は冪等（ON CONFLICT）で行われます。ETL の部分は部分失敗時に既存データを保護するよう設計されています。
- ニュース収集は SSRF・XML Bomb・大容量レスポンスの対策を含みますが、インターネットアクセスを有する環境でのみ実行してください。
- 本ライブラリはバックテストや実運用の一部として利用できるよう設計されていますが、実際の発注ロジック（資金管理、スリッページ、接続先ブローカーの API の扱い等）は別途実装が必要です。

---

## 参考（よくある操作コマンド）

- DuckDB コンソールで DB を確認:
  ```bash
  python -c "import duckdb; c=duckdb.connect('data/kabusys.duckdb'); print(c.execute('SHOW TABLES').fetchall())"
  ```

- ETL を手動で実行（例: 今日分）:
  ```bash
  python - <<'PY'
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  PY
  ```

---

必要であれば README に以下を追加できます:
- requirements.txt / pyproject.toml からの正確な依存リスト
- CI / デプロイ手順（コンテナ化・cron での ETL 実行など）
- サンプル .env.example ファイル
- 詳細な API 使用例（各関数のパラメータ説明と戻り値例）

どの追加情報が欲しいか教えてください。