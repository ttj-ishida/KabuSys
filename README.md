# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（オーダー／約定トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI ベースのニュースセンチメント評価・監査ログを統合するライブラリ群です。設計方針として以下を重視しています。

- Look-ahead バイアス回避（内部で datetime.today() や date.today() を不適切に参照しない）
- ETL の差分取得・冪等保存（ON CONFLICT / upsert）
- API 呼び出し時のリトライ / レート制御（J-Quants / OpenAI）
- ニュース収集時の SSRF / XML 攻撃対策（defusedxml 等）
- DuckDB をデータレイクとして使用、監査ログ用 DB 初期化ユーティリティあり

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーを差分取得（pagination 対応）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比）、日付整合性チェック
- マーケットカレンダー管理
  - カレンダー取得・保存・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
- ニュース収集 & 前処理
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、記事 ID 生成、SSRF 対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合評価（score_news）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（score_regime）
  - OpenAI API の JSON mode を用いた厳格なレスポンスパース／再試行ロジック
- 研究用ユーティリティ
  - Momentum, Volatility, Value 等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算 / IC 計算 / ランク化 / Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを保証

---

## セットアップ手順 (開発環境向け)

前提: Python 3.10 以上を推奨（コード内で | 型や __future__ annotations を使用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、主要依存を個別にインストールしてください:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（パッケージとして扱う場合）:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは src/kabusys/config.py がプロジェクトルートを .git または pyproject.toml を基準に探索して行います）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID : Slack 通知用
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）

   - 例 `.env`（最小）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（主要ユースケース）

以下は Python スクリプトや REPL から呼び出す例です。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（銘柄ごと）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って order_requests や executions を操作できます
  ```

- ファクター計算 / リサーチ
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用します。
- ETL / 保存処理は冪等性を保つ設計ですが、実行前にスキーマ（必要テーブル）が存在することを確認してください（初回は schema 初期化ユーティリティ等を用いる設計想定）。

---

## ディレクトリ構成 (主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（score_news）
    - regime_detector.py             -- マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & DuckDB 保存ユーティリティ
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult のエクスポート
    - quality.py                     -- データ品質チェック
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         -- 市場カレンダー管理 / 更新ジョブ
    - news_collector.py              -- RSS ニュース収集（SSRF 対策・正規化）
    - audit.py                       -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             -- Momentum/Value/Volatility 等
    - feature_exploration.py         -- 将来リターン / IC / ランク / summary
  - ai/ (上記)
  - research/ (上記)
- pyproject.toml / setup.py (プロジェクトルートに存在する想定)

各モジュールは DuckDB 接続を引数に取る設計で、外部 API への直接発注など本番資産に触れる機能は別レイヤ（execution 等）にある想定です。

---

## その他の留意点

- 自動 .env ロード:
  - config.py はプロジェクトルートを .git または pyproject.toml を基準に探索し、.env → .env.local の順で読み込みます。OS 環境変数が優先され、.env.local は上書きします。
  - テストや特殊用途で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング:
  - settings.log_level で LOG_LEVEL を制御できます（デフォルト INFO）。
- テスト・モック戦略:
  - OpenAI / ネットワーク呼び出しは内部で再試行・例外制御を行いますが、unittest.mock を用いて _call_openai_api 等を差し替えてテスト可能です。
- セキュリティ:
  - news_collector は SSRF や XML 攻撃対策を実装していますが、運用時は許可する RSS ソースを制限してください。

---

もし README に追加したい情報（例: CLI コマンド、CI 設定、具体的なスキーマ定義 SQL の抜粋、運用スケジュール例など）があれば教えてください。必要に応じてサンプル .env.example や初期スキーマ作成スクリプトも作成します。