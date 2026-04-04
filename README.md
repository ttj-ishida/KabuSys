# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ ETL、ニュース収集・NLP（LLM）によるセンチメント評価、ファクター計算、監査ログ（発注・約定トレーサビリティ）など、バックテスト・研究・本番運用に必要な機能群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける設計（target_date を明示して処理する）
- DuckDB を主要なデータ格納先として使用
- J-Quants / OpenAI と統合（トークンの自動リフレッシュやリトライロジックを備える）
- API 呼び出しは堅牢なリトライ / レート制御を実装
- 冪等性（ETL / DB 書き込みは ON CONFLICT 等で安全に上書き）

---

## 機能一覧

- 環境設定管理
  - `.env` 自動読み込み（プロジェクトルート検出）および必須環境変数チェック
- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS 取得、前処理、記事 ID 正規化（SSRF対策、トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア（ai_scores への書き込み）
  - マクロニュース＋ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- カレンダー（JPX）管理
  - 営業日判定、prev/next 営業日取得、カレンダー更新ジョブ
- 監査ログ（Audit）
  - signal_events, order_requests, executions を含む監査スキーマの初期化・管理
- 汎用ユーティリティ
  - レートリミッタ、JSON/レスポンスの堅牢な処理、データ変換ユーティリティ等

---

## 必要環境・依存ライブラリ

- Python 3.10+
- 推奨ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：datetime, urllib, json, logging など

（プロジェクトの実際の requirements.txt を用意していればそちらを利用してください。ここに記載のパッケージは主要な外部依存です。）

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）：

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション（発注を行う場合）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (LLM を使う関数で参照)
- LINE（通知用、任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 監視・プロセス管理
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- 実行環境設定
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO

必須の値（たとえば JQUANTS_REFRESH_TOKEN）は `kabusys.config.settings` 経由で取得し、未設定の場合は ValueError が送出されます。

---

## セットアップ手順（ローカル開発）

1. Python 仮想環境の作成と有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 例（最低限の項目）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成
   - mkdir -p data

---

## 使い方（代表的な例）

基本的に各機能はモジュール関数として公開されています。以下は実行例です（簡易）。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で与える
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（MA200 とマクロニュースの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- 将来リターン / IC / 統計サマリー
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- カレンダー操作
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  is_trade = is_trading_day(conn, date(2026,3,20))
  next_td = next_trading_day(conn, date(2026,3,20))
  ```

- 監査ログスキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from pathlib import Path
  db_path = Path("data/audit.duckdb")
  audit_conn = init_audit_db(db_path)
  ```

注意点：
- LLM を使う関数（news_nlp.score_news, regime_detector.score_regime 等）は OPENAI_API_KEY（または api_key 引数）を必要とします。
- ETL や DB 書き込みは DuckDB 接続を受け取ります。適切なパス・バックアップを用意してください。
- ルックアヘッドバイアスを避けるため、日付は必ず明示的に与えるか、run_daily_etl のように内部で調整された日付を使ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM 評価（ai_scores 生成）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — 市場カレンダー管理（営業日判定、更新ジョブ）
    - news_collector.py             — RSS 取得・正規化・保存ロジック
    - quality.py                    — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査テーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value の計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー 等
  - research/* その他の補助モジュール（ファイル一覧は上に示した通り）

---

## 開発・貢献

- 自動環境変数読み込みは project root を基準に行われます（.git または pyproject.toml を検出）。テスト時や特殊な環境で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- LLM / API 呼び出し部分はテストしやすいように内部呼び出しをモック可能な実装になっています（_call_openai_api 等を patch してください）。
- DuckDB の executemany はバージョン依存の挙動があるので、空配列渡しの回避や個別 DELETE を使う実装上の工夫があります。ローカルで DuckDB バージョンを固定してテストを行ってください。

---

README に書かれているサンプルや説明は、コード中にコメントとして記載された設計方針・使用方法に基づいています。実運用前に環境変数・API トークンの管理、DB のバックアップ方針、そして実際の発注フローに対する安全確認（ペーパートレード環境での十分な検証）を必ず行ってください。