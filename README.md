# KabuSys

日本株の自動売買・リサーチ・データパイプラインを目的とした Python パッケージです。  
ETL（J-Quants） → データ品質チェック → ファクター計算 → ニュース/NLP 評価 → レジーム判定 → 監査ログという一連のワークフローを提供します。

主な用途
- 日次の市場データ取得（J-Quants）と DuckDB への保存（ETL）
- データ品質チェック
- ファクター（モメンタム / バリュー / ボラティリティ 等）計算
- ニュースの LLM（OpenAI）によるセンチメント付与（ai_scores）
- 市場レジーム判定（ETF + マクロニュース）
- 監査テーブル（signal / order_request / executions）初期化・管理

---

## 機能一覧

- 環境変数管理
  - `.env` / `.env.local` をプロジェクトルートから自動読み込み（OS 環境変数が優先）
  - 自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- データ取得（J-Quants）
  - 日足（OHLCV）、財務（四半期データ）、JPX カレンダー取得（ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新 + バックフィル（デフォルト 3 日）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - 日次統合実行: `run_daily_etl`
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 各銘柄に対してニュースを集約し、gpt-4o-mini（JSON mode）でセンチメントを付与
  - バッチ送信・リトライ・レスポンス検証・±1.0 クリップ
  - 関数: `kabusys.ai.news_nlp.score_news`
- レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime を書き込み
  - 関数: `kabusys.ai.regime_detector.score_regime`
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを冪等に初期化
  - 初期化ユーティリティ: `init_audit_schema` / `init_audit_db`
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化

---

## セットアップ手順

前提
- Python 3.10+ を推奨（type hint に `X | Y` を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例（venv を使う）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. 開発インストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=xxxxx
- SLACK_BOT_TOKEN=xxxxx
- SLACK_CHANNEL_ID=xxxxx
- OPENAI_API_KEY=xxxxx  （news / regime の実行に必要）
- DUCKDB_PATH=data/kabusys.duckdb  （任意のパス）
- SQLITE_PATH=data/monitoring.db     （監視DBなど）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

.env のパース仕様（簡単な説明）
- コメントは行頭 `#` または 値の前にスペースがある `#` をコメントとみなす
- `export KEY=val` 形式に対応
- シングル/ダブルクォート内ではバックスラッシュでエスケープ可能
- 読み込み優先順: OS 環境 > .env.local > .env

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL からの呼び出し例です。実行前に `OPENAI_API_KEY` や `JQUANTS_REFRESH_TOKEN` 等を設定してください。

- DuckDB に接続して日次 ETL を実行する
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(res.to_dict())

- ニュースの NLP スコア付与（指定日に対して）
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を使用
  - print(f"scored {n} codes")

- 市場レジーム判定（指定日）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB を初期化する
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

- 初期化（スキーマだけ既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - init_audit_schema(conn, transactional=True)

注意点
- LLM 呼び出しは API コストが発生します。バッチやリトライの挙動を確認してください。
- 自動売買（発注／実行）機能を統合する場合は、`KABUSYS_ENV` を `paper_trading` または `development` にして十分に検証してから `live` に切り替えてください。
- LLM や外部 API の失敗は多くの箇所でフォールバック（スコア 0.0、処理継続）する設計になっていますが、運用方針に合わせてロギング・通知を整えてください。

---

## ディレクトリ構成

（抜粋）src/kabusys 以下の主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP スコアリング（score_news）
    - regime_detector.py             -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py         -- 市場カレンダー管理（営業日判定等）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py              -- J-Quants API クライアント（fetch/save 等）
    - news_collector.py              -- RSS 収集・前処理
    - quality.py                     -- データ品質チェック
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - audit.py                       -- 監査ログスキーマ初期化
    - etl.py                         -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー 等

その他の注記:
- 多くのモジュールは duckdb 接続（duckdb.DuckDBPyConnection）を引数として受け取り、SQL と Python を組み合わせて処理します。
- OpenAI 呼び出しは openai.OpenAI クライアントを生成して行います（API キーを引数で注入可能）。

---

## 運用・開発上のポイント

- テスト・CI:
  - 自動 .env 読み込みはテストで副作用を避けたい場合 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- セキュリティ:
  - RSS 取得は SSRF 対策・レスポンスサイズ制限・XML 安全パーサ（defusedxml）を採用しています。
  - J-Quants トークンは .env で管理し、ログ等に直接出力しないでください。
- 冪等性:
  - J-Quants からの保存関数は ON CONFLICT DO UPDATE を利用して冪等に設計されています。
  - 監査テーブルの order_request_id / broker_execution_id は冪等キーを想定しています。

---

必要に応じて、この README をプロジェクトの実際のセットアップ（pyproject.toml / requirements.txt）や運用手順書（運用 runbook, Slack 通知設定等）に合わせてカスタマイズしてください。必要であれば、具体的な .env.example や quickstart スクリプト（etl_run.py, score_news.py 等）のテンプレートも作成します。