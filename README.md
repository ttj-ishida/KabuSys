# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ群です。  
ETL（J-Quants からのデータ収集）、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

---

## 主な機能 (Highlights)

- ETL / Data Platform
  - J-Quants API からの株価（日足）・財務・マーケットカレンダーの差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション対応・トークン自動リフレッシュ・レート制御
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini / JSON mode）を使った銘柄ごとのニュースセンチメント算出（ai_scores への保存）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマ初期化 / DB 作成ユーティリティ
- その他ユーティリティ
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - jquants_client（fetch/save の Idempotent 実装）

---

## 要件（推奨）

- Python 3.10+
- 必要ライブラリ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリのみで多くの処理を実装しています。実行環境に応じて追加ライブラリを pip で導入してください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージ開発時:
pip install -e .
```

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git or pyproject.toml を基準）にある `.env` / `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な環境変数（一部）:

- J-Quants / データ関連
  - JQUANTS_REFRESH_TOKEN (必須)
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム設定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- OpenAI
  - OPENAI_API_KEY（score_news / score_regime などの呼び出しに必要）

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存関係をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # 存在する場合
   # または最低限:
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をエクスポートしてください。
   - `.env.example` を参考に作成します（リポジトリに例ファイルがある想定）。

4. DuckDB 初期化（任意: 監査DBを新規作成）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続オブジェクト
     ```

---

## 使い方（代表的な例）

※ すべての API は DuckDB 接続（duckdb.connect(...) で得られるオブジェクト）を受け取ります。

- 日次 ETL を実行する（prices / financials / calendar を差分で取得 → 品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを生成（OpenAI が必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数か api_key 引数で指定
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"Scored {n} symbols")
  ```

- 市場レジーム判定を実行（ma200 + マクロニュース LLN）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマを初期化（既存 DB に追加）:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究用）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

---

## API 的注意点（実運用上のポイント）

- Look-ahead bias 回避のため、多くの関数は内部で datetime.now()/date.today() を直接参照しない設計になっています。target_date を明示して呼ぶことを推奨します。
- OpenAI 呼び出しはリトライ・タイムアウト管理、レスポンス検証（JSON mode）などフェイルセーフ実装があります。API キーは環境変数か引数で渡してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を守る実装です。大量取得時は時間の余裕を持ってください。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、実装側でチェックしています。

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP スコアリング（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + save_* 実装
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - calendar_management.py # マーケットカレンダー管理
    - news_collector.py      # RSS 収集・前処理
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログスキーマ初期化
    - etl.py                 # ETL の公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 計算
    - feature_exploration.py # forward returns / IC / summary / rank
  - ai、research、data 以下に多数のユーティリティ関数と DB 操作ロジックあり

---

## テスト・開発時のヒント

- 環境変数の自動ロードを無効化したいときは:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI の実際の呼び出しは単体テストでモック化してテスト可能なように設計されています（内部 _call_openai_api をパッチする等）。
- DuckDB をインメモリで使うことでテストが高速になります:
  ```python
  import duckdb
  conn = duckdb.connect(":memory:")
  ```

---

## ライセンス / コントリビューション

（リポジトリに合わせてここにライセンス情報や貢献ガイドを追記してください）

---

必要であれば README に実行例（cron / systemd / airflow 用のジョブ設定例）や .env.example の完全テンプレート、よくあるトラブルシューティング（OpenAI エラー、J-Quants の 401 リフレッシュ問題、DuckDB 権限など）を追加します。どの項目を拡張するか教えてください。