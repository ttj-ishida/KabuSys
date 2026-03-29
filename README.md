# KabuSys

日本株向け自動売買・データ基盤ライブラリ（モジュール集合）。  
データ収集（J-Quants / RSS）、ETL、品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレース）などを包含します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤および研究プラットフォームのための Python モジュール群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理・銘柄紐付け
- OpenAI を用いたニュースセンチメント（ai_score）および市場レジーム判定
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注から約定までの監査ログ（監査テーブル / 初期化ユーティリティ）

設計上の共通方針として「ルックアヘッドバイアス回避」「冪等性」「堅牢なエラーハンドリング」「外部APIのレート制御/リトライ」を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
  - settings オブジェクト経由で必須値の取得

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（jquants_client）：認証、ページネーション、リトライ、保存関数（raw_prices, raw_financials, market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策・gzip 限度・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini + JSON mode）を用いた銘柄ごとのニュースセンチメント計算
  - チャンク・リトライ・レスポンスバリデーション・スコアのクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュース LLM スコア（30%）を合成して
    daily レベルで market_regime テーブルへ冪等書き込み

- 研究モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility（prices_daily/raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue 記録

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義
  - init_audit_schema / init_audit_db（冪等な初期化ユーティリティ）

---

## 必要な環境変数（主なもの）

必須（コード中で _require によってチェックされるもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 関連:

- OPENAI_API_KEY — news_nlp / regime_detector などで使用（関数呼び出し時に引数で注入可能）

任意・設定可能:

- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

注意: パッケージ起動時に自動でプロジェクトルート（.git または pyproject.toml を探索）を検出して `.env` / `.env.local` を読み込みます。テスト時に自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（例）

   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate

   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール（最低限）

   pip install duckdb openai defusedxml

   ※プロジェクト全体に requirements.txt / pyproject.toml がある場合はそちらからインストールしてください（例: pip install -e .）。

3. 環境変数設定

   プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な変数をセットします。例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース用ディレクトリ作成

   DuckDB のファイル保存先ディレクトリを作成しておきます（例: data/）。

   mkdir -p data

5. 監査DB 初期化（必要に応じて）

   Python REPL / スクリプトで:

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")

   あるいは、既存接続へスキーマ追加:

   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)

---

## 使い方（簡単な例）

以下は代表的なワークフローおよび呼び出し例です。すべての関数は docstring に使い方が書かれています。

- 設定の参照

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

- DuckDB 接続を開く

  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

- ニューススコア（ai_scores）生成

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY 環境変数を使用
  print(f"scored {n} codes")

- 市場レジーム判定

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 研究用ファクター計算

  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- J-Quants API を直接使う

  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))

- 監査テーブル初期化（既存接続へ）

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

---

## よくある利用上の注意 / トラブルシューティング

- .env 自動読み込み
  - パッケージインポート時にプロジェクトルート（.git か pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。テスト等でこれを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI API 呼び出し
  - news_nlp と regime_detector は OpenAI を利用します。API キーがないと ValueError を送出します。テスト時は _call_openai_api をモックしてレスポンスを差し替えてください（モジュール内で patch 可能な設計になっています）。

- DuckDB executemany の件
  - DuckDB のバージョンによる制約（executemany に空リストを渡せない等）に配慮した実装になっています。関数は空データ時に早期リターンします。

- J-Quants API レート制御
  - 内部で 120 req/min に合わせたレートリミッタを実装しています。大量データ取り込み時は時間がかかる点に注意してください。

- 監査ログ
  - 監査テーブルは削除しない前提です（履歴保持）。init_audit_schema は冪等で何度でも呼べます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLU / OpenAI 呼び出し
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py                  — ETL パイプライン (run_daily_etl 等)
  - etl.py                       — ETLResult のエクスポート
  - news_collector.py            — RSS 収集 / 前処理
  - calendar_management.py       — 市場カレンダー管理 / 営業日判定
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - audit.py                     — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum/value/volatility）
  - feature_exploration.py       — 将来リターン / IC / サマリー 等

---

## テスト・開発ヒント

- OpenAI クライアント呼び出しはモジュール内部の _call_openai_api を patch することで外部呼び出しを回避できます（ユニットテスト用）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するとテスト環境での .env の影響を防げます。
- DuckDB をインメモリで使う場合は db_path に ":memory:" を指定できます（init_audit_db 等）。

---

補足・参照:
- 各モジュールの docstring に詳細な設計方針・引数説明・戻り値・例外が記載されています。実装を利用する際はまず docstring を参照してください。