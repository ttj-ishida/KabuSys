# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、戦略用ユーティリティなどを含みます。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの差分 ETL（株価・財務・カレンダー取得）と品質チェック
- RSS ニュース収集と記事前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント分析（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を用いたデータ保存／処理

パッケージルート: `src/kabusys`

---

## 主な機能一覧

- data
  - ETL パイプライン（差分取得、保存、品質チェック）
  - J-Quants クライアント（認証・ページネーション・レート制御・保存）
  - market_calendar 管理・営業日判定
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - audit（監査テーブル作成・監査DB初期化）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - stats（汎用統計ユーティリティ）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算し `ai_scores` に保存
  - regime_detector.score_regime: ETF MA とマクロニュース（LLM）で市場レジーム判定
- research
  - factor_research: モメンタム、バリュー、ボラティリティ等のファクター
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ、ランク化
- config
  - 環境変数読み込み（`.env` / `.env.local` 自動ロード、必要に応じて無効化可能）
  - `settings` オブジェクトで各種設定にアクセス可能

---

## 前提条件

- Python 3.10 以上（型ヒントで `X | None` などを使用）
- 推奨ライブラリ（最低限、以下をインストール）
  - duckdb
  - openai
  - defusedxml

必要に応じて他の標準ライブラリ（urllib、json 等）を使用します。

---

## セットアップ手順

1. リポジトリをクローン／配置し、開発用にインストール（例）:

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # 開発インストール（パッケージ化されている場合）
   pip install -e .
   ```

2. 環境変数を設定する。プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます。
   自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）

必須（機能による）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 実行で必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注等で使用）

OpenAI / 通知:
- OPENAI_API_KEY — OpenAI API キー（`score_news` / `score_regime` で必要）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知（オプション）
- LINE_USER_ID — LINE 送信先（オプション）

DB / ファイルパス:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)

その他:
- KABUSYS_ENV: development | paper_trading | live （default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading 挙動）

※ settings モジュール内にデフォルト値やバリデーションの説明があります。

---

## 初期化・使い方（典型例）

以下は DuckDB を使って簡単に各処理を呼ぶ例です。実行は Python スクリプトやジョブから行います。

- DuckDB 接続の作成:

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査 DB の初期化（監査テーブルを作成）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）:

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に保存:

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-XXXX")
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 結果を合成）:

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-XXXX")
  ```

- ファクター計算（リサーチ）:

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  r = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(r), r[:3])
  ```

- 品質チェック単体実行:

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

注意:
- OpenAI を使う関数は `api_key` 引数でキーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / API 呼び出しはネットワークや認証を伴うため、例外処理を行ってください。

---

## 開発ヒント

- 自動で `.env` を読み込みます。テスト環境などで自動ロードを停止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分はモジュール内で関数に分離しているため、ユニットテストでは該当の内部呼び出し関数をモックしやすく設計されています（例: `kabusys.ai.news_nlp._call_openai_api` を patch）。
- J-Quants クライアントは内部にレートリミッタとリトライロジックを持っています。テスト時に ID トークンを注入できるように設計されています。
- DuckDB 実行時の TRX（BEGIN/COMMIT/ROLLBACK）や `executemany` の空パラメータ制約に留意している実装です。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（ai_scores 生成）
    - regime_detector.py            -- 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETL 結果型の再エクスポート
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - news_collector.py             -- RSS 収集・前処理（SSRF 対策）
    - calendar_management.py        -- 市場カレンダー管理・営業日ロジック
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログテーブル定義・初期化
    - stats.py                      -- 汎用統計ユーティリティ
    - pipeline.py                   -- ETL パイプライン（上記）
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム/バリュー/ボラティリティ
    - feature_exploration.py        -- 将来リターン, IC, 統計サマリ
  - research/ ...（上記ファイル群）
  - その他（strategy、execution、monitoring 等のサブパッケージは __all__ に含める設計）

---

## 付記

- README は実例を中心にまとめています。各モジュール内に詳細な docstring（日本語）があるため、API の細かい挙動はソースの docstring を参照してください。
- ライセンス・デプロイ手順・CI/CD の設定は本 README に含めていません。必要があれば追記してください。

もし README に追加したい項目（例: .env.example のテンプレート、コマンドラインツールの使い方、Docker 化手順など）があれば教えてください。必要に応じて例を追加します。