# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（監査テーブル初期化）などを提供します。

---

## 概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI を使ったニュースセンチメント評価・市場レジーム判定・監査ログ等を一貫して扱うためのモジュール群です。DuckDB を主要なオンディスク DB として利用し、J-Quants API や外部 RSS / OpenAI を組み合わせて運用・研究に必要な処理を行います。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない実装）
- ETL・保存処理は冪等（idempotent）設計
- API 呼び出しはリトライやレートリミット管理を実装
- 品質チェックを充実させ、問題を収集して呼び出し元で判断可能にする

---

## 機能一覧

- 環境変数 / .env 読み込みとアプリ設定（kabusys.config）
- J-Quants API クライアント（fetch / save / トークン管理 / レート制御）
  - 株価日足（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
- ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
- ニュース収集（RSS の安全な取得・正規化・raw_news への保存補助）
- ニュース NLP（OpenAI を使った銘柄別センチメント -> ai_scores）
  - score_news（batch, JSON mode, リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースで bull/neutral/bear を判定）
  - score_regime
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - calc_momentum, calc_value, calc_volatility
- 研究支援ユーティリティ（将来リターン計算、IC 計算、Z スコア正規化 等）
- 監査ログスキーマの初期化（監査テーブル / インデックス作成）
  - init_audit_schema / init_audit_db

---

## 必要な環境・依存

- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai (OpenAI の公式 SDK)
  - defusedxml

（プロジェクト配布の setup / pyproject に依存関係がある想定です。開発環境では pip でインストールしてください。）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   もしくは最低限:
   - pip install duckdb openai defusedxml
4. 環境変数を設定（.env をプロジェクトルートに置くことで自動読み込みされます）
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...          （kabu ステーション API 用）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...             （news_nlp / regime_detector で使用）
   任意/デフォルト:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. 自動 .env ロードを無効化したい場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行・使い方（例）

以下は Python REPL やスクリプトからの簡単な呼び出し例です。

- DuckDB 接続サンプル:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア付け（OpenAI API key が必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored: {count}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査用別 DB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI API を使う関数は api_key 引数でキー注入可能（テスト・一時切替用）。未指定時は環境変数 OPENAI_API_KEY を参照します。
- ETL/API 関連はネットワーク・認証情報が必要であり、ローカルでの実行には J-Quants のリフレッシュトークン等が必須です。
- 本リポジトリのコードはデータ取得や発注等の機能を含むため、本番環境ではシークレット管理・テストを慎重に行ってください。

---

## ディレクトリ構成

（主要モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースのセンチメント解析 / score_news
    - regime_detector.py            -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント / save_* / fetch_*
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - news_collector.py             -- RSS 収集ユーティリティ
    - calendar_management.py        -- 市場カレンダー管理・営業日判定
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 汎用統計（zscore_normalize 等）
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- momentum / value / volatility 計算
    - feature_exploration.py        -- forward returns, IC, factor summary, rank
  - ai, data, research 以下にさらに細かい関数・定数・ヘルパーあり

---

## .env と自動読み込みの仕組み

- プロジェクトルート（.git か pyproject.toml のあるディレクトリ）を起点に .env, .env.local を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを無効化する場合は環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風の形式（export KEY=val やコメント、クォート、エスケープ）に対応します。

---

## 運用上の注意

- KABUSYS_ENV による run-time の切り替え（development / paper_trading / live）を実装済みです。live モードでは外部発注等に繋がる機能を有効にする想定のため慎重に扱ってください。
- OpenAI や J-Quants の API 呼び出しはコストやレート制限があります。運用時は API キー・レート制御に注意してください。
- ニュース収集は SSRF 等に配慮した安全実装が入っていますが、運用時のソース管理（RSS 一覧）には注意してください。
- DuckDB のバージョン差異により executemany の空リスト取り扱いなど挙動差があるため、ライブラリの互換性に注意してください。

---

README に記載のない詳細な API や追加ユーティリティは各モジュールの docstring を参照してください。必要であれば README に追加したい具体的な操作（例: バッチスケジューリング、CI 用コマンド、データスキーマ定義）を教えてください。