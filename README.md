# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

---

## 特徴（概要）

- J-Quants API を用いた株価・財務・上場情報・市場カレンダーの差分取得（ページネーション・レート制御・自動リフレッシュ対応）
- DuckDB を用いたローカルデータレイク（冪等保存：ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）と市場レジーム判定（ETF + マクロニュース）
- 研究用モジュール：モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン・IC・統計サマリ
- 監査ログスキーマ（signal → order_request → execution）を DuckDB に初期化するユーティリティ
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

---

## 機能一覧（抜粋）

- データ取得・保存
  - fetch_daily_quotes / save_daily_quotes（raw_prices）
  - fetch_financial_statements / save_financial_statements（raw_financials）
  - fetch_market_calendar / save_market_calendar（market_calendar）
  - fetch_listed_info（上場銘柄情報）
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - ETL 結果は ETLResult オブジェクトで返却（品質チェック含む）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- ニュース収集
  - fetch_rss（安全対策：SSRF, gzip 上限, トラッキング除去）
  - raw_news / news_symbols テーブルへ冪等保存（実装部分）
- ニュース NLP / AI
  - score_news（銘柄別センチメントを ai_scores に書込）
  - score_regime（ETF 1321 の MA とマクロニュース LLM を合成して market_regime に書込）
  - OpenAI 呼び出しはリトライ・バックオフを考慮
- 研究用（research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（監査スキーマを DuckDB に作成）

---

## 要求環境 / 依存パッケージ

- Python 3.10+
- 主な依存（プロジェクト側で requirements を用意してください）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリも多用しています（urllib, datetime, json 等）

（実際のパッケージ配布時は requirements.txt または pyproject.toml を参照してください）

---

## 環境変数（主なもの）

※KabuSys は .env / .env.local を自動で読み込みます（プロジェクトルート判定: .git または pyproject.toml が存在するディレクトリ）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（使用箇所により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）

オプション:
- KABUSYS_ENV — 動作環境: `development` (default) / `paper_trading` / `live`
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — 監視用 SQLite データベースのパス（デフォルト: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを抑制する（任意）

.env の読み込み優先順位:
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージインストール
   - pip / requirements.txt がある前提:
     ```
     pip install -r requirements.txt
     ```
   - または開発モードでローカルインストール:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - リポジトリルートに `.env`（および `.env.local`）を作成し、必要なキーを設定してください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB データベースの初期化（監査DB を別で準備する例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（よく使う例）

以下は Python スクリプト内での利用例の抜粋です。各関数は DuckDB 接続オブジェクトを受け取ります（duckdb.connect(...) を使用）。

- 基本的な DuckDB 接続
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると today が対象
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア）を実行
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  ret = score_regime(conn, target_date=date(2026, 3, 20))
  print("score_regime returned:", ret)
  ```

- 監査ログスキーマの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  # 既に作成済みの DuckDB 接続に対してスキーマを追加
  init_audit_schema(conn, transactional=False)
  ```

- J-Quants から株価を直接取得（テスト用途）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
  print(len(records))
  ```

注意点（実運用上のヒント）:
- AI モジュールは OpenAI API キーが必要です。API 呼び出しはリトライやフェイルセーフが組み込まれており、失敗時はスコア 0.0 でフォールバックする設計です。
- run_daily_etl は個別ステップで例外をハンドリングしつつ処理を継続するため、一部ステップ失敗でも結果オブジェクトにエラー情報が含まれます。
- .env の自動読み込みはプロジェクトルートが特定できる場合のみ行われます。ユニットテスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（本リポジトリの現在のコードベースに基づく）：

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — 記事のセンチメント解析（OpenAI）
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 主要型の再エクスポート（ETLResult）
    - news_collector.py             — RSS 取得・前処理
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック（missing, spike, duplicates, date consistency）
    - audit.py                      — 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility ファクター計算
    - feature_exploration.py        — 将来リターン計算 / IC / 統計サマリ

（上記以外に strategy / execution / monitoring 等のパッケージが公開される設計になっていますが、このコードベースでは __all__ に名前のみが含まれています）

---

## 設計上の重要な注意事項

- ルックアヘッドバイアス対策:
  - AI / ETL / 研究モジュールは内部で date.today() 等を不用意に参照せず、明示的な target_date を受け取る設計になっています。
  - DB クエリは target_date 未満 / 以前のデータだけを参照する等の注意が払われています。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて冪等保存を行います。
  - ニュース収集も記事ID をハッシュ化して冪等性を担保する設計です。
- フェイルセーフ:
  - AI 呼び出しや API 呼び出しはリトライ・バックオフを導入し、致命的失敗時でもシステムが継続するようにフォールバックを持たせています。
- セキュリティ:
  - RSS の取得では SSRF 対策（ホストのプライベート判定・リダイレクト検査）や XML パーサーの安全実装（defusedxml）を採用しています。

---

## サポート / 開発者向け

- テスト／CI: 環境変数の自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト時に便利です）。
- OpenAI 呼び出しは内部関数をモックしやすいように分離されています（unittest.mock.patch を利用可能）。
- DuckDB のバージョンによっては executemany の空リストに制約があるため、実装で空チェックが入っています（互換性配慮）。

---

README はここまでです。必要であれば以下の追加情報を出力できます：
- 具体的な .env.example のテンプレート
- サンプルスクリプト（ETL ジョブ / ニュース収集 / レジーム判定）ファイル
- requirements.txt の候補リスト

どれが必要か教えてください。