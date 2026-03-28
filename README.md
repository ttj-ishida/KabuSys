# KabuSys README

日本株向けの自動売買／データプラットフォーム用ライブラリ群「KabuSys」の README です。  
本ドキュメントはリポジトリ内の実装（src/kabusys 以下）に基づき、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API を利用した市場データ（株価・財務・カレンダー等）の差分 ETL と DuckDB 保存
- RSS ニュース収集とニュース → 銘柄紐付け、LLM（OpenAI） を用いたニュースセンチメント評価（銘柄毎の ai_score）
- 市場レジーム判定（ETF の移動平均乖離とマクロニュースの LLM センチメントを合成）
- 研究（ファクター計算、将来リターン、IC 計算、統計サマリー）用ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査ログ（監査テーブル初期化・管理）
- J-Quants クライアント（リトライ・レートリミット・トークン自動リフレッシュ対応）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で `date.today()` / `datetime.today()` を不用意に参照しない実装方針
- DuckDB を中心に SQL と軽量 Python ロジックで実装（外部 heavy ライブラリに依存しない）
- API 呼び出しに対する堅牢なリトライ・バックオフ・フェイルセーフ（API 失敗時は部分的にスキップして継続する設計）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出、環境変数上書きルール）
  - 必須環境変数取得ユーティリティ（`kabusys.config.settings`）
- データ取得・保存（J-Quants）
  - fetch / save: 日次株価 (`/prices/daily_quotes`), 財務 (`/fins/statements`), 上場情報, マーケットカレンダー
  - rate limit と retry、401 時のリフレッシュ処理を備えたクライアント (`kabusys.data.jquants_client`)
- ETL パイプライン
  - 日次 ETL エントリポイント: `run_daily_etl`（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ: `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`
- ニュース関連
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限） (`kabusys.data.news_collector`)
  - ニュース NLP（OpenAI を用いたバッチスコアリング、JSON Mode を活用） (`kabusys.ai.news_nlp`)
- 市場レジーム判定
  - ETF（1321）200 日 MA 乖離 + マクロニュース LLM センチメントで日次レジームを算出し DB へ保存 (`kabusys.ai.regime_detector`)
- 研究（Research）
  - ファクター計算（momentum, volatility, value 等） (`kabusys.research.factor_research`)
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等 (`kabusys.research.feature_exploration`)
  - Z スコア正規化ユーティリティ (`kabusys.data.stats`)
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（`kabusys.data.quality`）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化・DB 作成 (`kabusys.data.audit`)

---

## 必要要件（推奨）

- Python 3.10+
  - 型ヒントに `X | Y` を使っているため 3.10 以上を想定しています
- 主な依存パッケージ（pip install で追加）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外のパッケージは上の通り。実際の requirements.txt があればそちらを使用してください。

---

## 環境変数（主要）

以下の環境変数 / .env キーがコード内で参照されます。必須のものは README 中で明示します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN — Slack 通知に使う場合
- SLACK_CHANNEL_ID — Slack チャネル ID
- KABU_API_PASSWORD — kabu API 連携がある場合のパスワード
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp, regime_detector）で必要

任意 / デフォルトあり:
- KABUSYS_ENV — {development, paper_trading, live}。デフォルト `development`
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}。デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）

.env 自動読み込みの挙動:
- プロジェクトルートはこのパッケージのファイル位置から上位に `.git` または `pyproject.toml` を検索して決定します
- OS 環境変数 > .env.local > .env の順で読み込み（.env.local は上書き）
- テストなどで自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてルートへ移動
   - (git clone ...)

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必須キーを記載するか、OS 環境変数で設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

5. DuckDB 初期化（監査ログ用 DB 等）
   - Python REPL やスクリプトから:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または監査スキーマだけを既存接続に適用:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)

---

## 使い方（代表的な例）

以下は主要な操作例（Python スニペット）です。実行は仮想環境で行ってください。

- 設定値参照
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

- 日次 ETL を実行してデータを DuckDB に取り込む
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（ai_scores 生成）
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込銘柄数: {n_written}")

- 市場レジーム判定
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  status = score_regime(conn, target_date=date(2026, 3, 20))
  print("OK" if status == 1 else "NG")

- 監査DB 初期化（ファイル作成）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_logs を書き始めることができます

- 研究用ファクター計算例
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))

注意点:
- OpenAI を使う機能は `OPENAI_API_KEY` を設定する必要があります（関数に api_key を直接渡すことも可能）。
- J-Quants API はレート制限があります。`JQUANTS_REFRESH_TOKEN` を必ず用意してください。
- ETL は部分失敗（API エラー等）に対してフェイルセーフ設計ですが、ログを確認して手動対応を行ってください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
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
  - etl.py (ETL インターフェース再エクスポート)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージは zscore 正規化やファクター探索関数を公開
- その他（strategy, execution, monitoring 等のパッケージ名が __all__ に含まれますが、ここに示したファイル群が主要実装）

（上記はリポジトリ内の主要モジュールを抜粋したものです。実際のリポジトリにはさらにモジュールやテストが含まれる可能性があります。）

---

## 運用上の注意・ベストプラクティス

- 環境分離:
  - 本番（live）環境と paper_trading / development を明確に分け、KABUSYS_ENV を設定してください
- 秘密情報管理:
  - API キー（OpenAI、J-Quants 等）は環境変数で管理し、リポジトリにコミットしないでください
- ロギング:
  - LOG_LEVEL を適切に設定して運用ログを確認してください
- DuckDB ファイル:
  - DB ファイルはバックアップしておくことを推奨します（破損時の復元が難しい場合があります）
- API レート制限:
  - J-Quants のレート制限（120 req/min）を尊重してください（クライアント実装に組み込み済み）

---

## 開発・テストに関するヒント

- 自動 .env ロードを無効化したいテストは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- OpenAI 呼び出しはモジュール内で `_call_openai_api` を分離しているため、ユニットテストではパッチしてモックできます（例: unittest.mock.patch）
- J-Quants 電文のテストは `jquants_client._request` をモックするか、`id_token` をテスト用に差し替えて行う

---

疑問点・追加して欲しいセクションがあれば教えてください。README を用途（開発者向け / 運用手順 / API リファレンス）に応じて拡張できます。