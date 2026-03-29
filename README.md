# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセットです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算、AI（ニュースセンチメント / 市場レジーム）などを含むモジュール群を提供します。

---

## 主な概要

- パッケージ名: `kabusys`
- 目的: 日本株のデータパイプラインとリサーチ・自動売買に必要な共通処理をまとめる
- 設計方針:
  - ルックアヘッドバイアスに配慮（日時の参照は明示的引数ベース）
  - DuckDB を主なオンディスク DB として利用（軽量かつ高性能）
  - J-Quants / RSS / OpenAI 等の外部 API 呼び出しはリトライ・フェイルセーフを備える
  - 冪等性（ETL 保存・監査テーブル等）は意識して実装

---

## 機能一覧（モジュール別ハイライト）

- kabusys.config
  - 環境変数 / .env の自動読み込み（プロジェクトルート検出）
  - 必須設定のラッパー `settings`

- kabusys.data
  - jquants_client: J-Quants API からの取得 / DuckDB 保存（rate limit・リトライ・トークン自動リフレッシュ）
  - pipeline / etl: 日次 ETL パイプライン（価格・財務・カレンダーの差分取得、品質チェック）
  - news_collector: RSS 取得と raw_news への冪等保存（SSRF 対策、トラッキング除去等）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - stats: 共通統計ユーティリティ（Zスコア正規化 等）
  - audit: 監査ログ（signal / order_request / executions）テーブル初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュース記事をまとめて LLM に送り銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジーム（日次）を判定・保存

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリなど
  - data.stats の zscore_normalize を再エクスポート

- （将来的/別モジュール）
  - strategy / execution / monitoring: パッケージの __init__ では公開予定の名前空間あり（実装は別途）

---

## 必要な環境変数（最低限）

以下はコード内で必須もしくは利用される代表的な環境変数です。プロジェクトルートの `.env` / `.env.local` に配置するか、CI / 実行環境で設定してください。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（発注等で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知（任意機能）用
- SLACK_CHANNEL_ID (必須) — Slack 通知先
- OPENAI_API_KEY (AI 機能利用時に必要) — OpenAI API キー（`score_news` / `score_regime` で使用）
- KABUSYS_ENV (任意) — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL (任意) — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると `.env` 自動ロードを無効化できます（テスト時に便利）

デフォルト DB パス（環境変数で上書き可）:
- DUCKDB_PATH (デフォルト: `data/kabusys.duckdb`)
- SQLITE_PATH (デフォルト: `data/monitoring.db`)

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.9+（typing | match 実装や一部モダンAPIを利用）
   - 仮想環境を作成する例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存関係インストール
   - 必要パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに setup/pyproject があれば `pip install -e .` を推奨します。

3. 環境変数設定
   - プロジェクトルートに `.env` を置く（`.env.local` はより優先して読み込まれます）。
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードは `kabusys.config` によりプロジェクトルート（.git or pyproject.toml を注視）から行われます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 初期 DB / 監査スキーマの作成（例）
   - Python REPL やスクリプトで:
     - from kabusys.config import settings
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db(settings.duckdb_path)
   - 上記は監査ログ専用 DB を作成して接続を返します（`:memory:` も指定可能）。

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実運用ではログ設定や例外処理を適切に行ってください。

- DuckDB に接続して日次 ETL を走らせる:
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして DB に保存:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で解決
  print("written:", written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # Z スコア正規化
  norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- J-Quants 生データ取得（認証・ページネーションを内部で処理）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

---

## 注意点 / 実運用のヒント

- OpenAI を利用する機能（news_nlp / regime_detector）は環境変数 `OPENAI_API_KEY` または各関数の `api_key` 引数でキーを与えてください。API呼び出しはリトライ・フェイルセーフ（失敗時は 0 スコア等）設計です。
- J-Quants API のレート制限（120 req/min）を守るため内部にスロットリングが実装されています。並列で大量リクエストを飛ばすと待ちが発生します。
- ETL は部分失敗を想定して設計されています（各ステップ独立でエラー処理し、結果を集約）。戻り値の ETLResult で品質問題やエラーの有無を確認して下さい。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空チェックがコード内で行われています。DuckDB のバージョンに依存する挙動に注意してください。
- news_collector は RSS の SSRF 対策・受信サイズ制限・XML パース安全化（defusedxml）を実装しています。外部 RSS の扱いは慎重に。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要ファイル一覧（抜粋）です:

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
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (他: pipeline/etl の周辺ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (将来的) strategy/, execution/, monitoring/ を公開名として __all__ に含めています

---

## ライセンス / 貢献

- 本 README に示した通り、本リポジトリは複数の外部 API（J-Quants, OpenAI）および外部データソース（RSS）に依存します。API キーや利用規約に従って使用してください。
- 貢献やバグ報告はリポジトリの Issue / Pull Request を通じてお願いします（詳細な CONTRIBUTING.md があればそちらに従ってください）。

---

README に記載の使い方はライブラリ内実装に基づく最低限の導入と実行イメージです。運用環境へ組み込む場合はログ設定、監視、バックアップ、機密情報管理（シークレット管理）を必ず行ってください。