# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータパイプライン / 研究ツール / ニュース NLP / 市場レジーム判定を提供するライブラリです。J-Quants API など外部データソースからデータを取得し、DuckDB 上で ETL、品質チェック、ファクター計算、LLM を用いたニュースセンチメント評価、監査ログの管理までを行うことを想定しています。

主な目的:
- 日次 ETL（株価・財務・市場カレンダー）の自動化
- ニュース記事の収集と LLM による銘柄センチメント算出
- 市場レジーム（bull/neutral/bear）判定
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal → order_request → execution）テーブルの初期化

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（優先度: OS環境変数 > .env.local > .env）
  - 必須設定の取り扱い、各種パス・スレッショルド・運用モードの取得

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得し DuckDB に保存
  - 差分取得、ページネーション、トークン自動リフレッシュ、レートリミット、リトライ処理を実装
  - ETL 実行結果を ETLResult dataclass として返却

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出、スパイク検出、重複検出、日付整合性チェック
  - 問題は QualityIssue のリストで返却（error / warning）

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルの管理、営業日判定／次営業日／前営業日／期間の営業日取得
  - JPX カレンダーの夜間差分更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS からニュース取得、URL 正規化、テキスト前処理、SSRF 対策、重複回避
  - raw_news / news_symbols への冪等保存想定

- ニュース NLP（kabusys.ai.news_nlp）
  - LLM（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_score）を算出・ai_scores へ保存
  - バッチ処理、チャンク化、JSON モード、リトライ・フォールバック実装

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を算出し market_regime テーブルへ書き込み
  - Look-ahead バイアス防止の設計（target_date ベース）

- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルおよびインデックスの初期化
  - 監査に適した DDL と初期化ユーティリティを提供

---

## セットアップ手順（開発・実行）

前提:
- Python 3.9+（タイプヒントの Union 表現や typing の仕様に適合するバージョン）
- ネットワーク接続（J-Quants / OpenAI など外部 API）

1. リポジトリを取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要な主要パッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください:
     pip install -e . または pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (LLM を使う機能で必要)
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用、任意)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   - サンプル `.env`（例）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. データベースディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要 API サンプル）

以下はライブラリをインポートして機能を利用する最小例です。DuckDB 接続を渡して各関数を実行します。

- ETL（日次パイプライン）の実行例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごとの ai_scores 生成）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム評価:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査テーブル初期化（監査用 DB を別途用意する場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成される
  ```

- 研究用ファクター取得例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

注意点:
- score_news / score_regime など LLM を呼ぶ関数は OPENAI_API_KEY（引数でも渡せる）を必要とします。
- run_daily_etl は network / API を呼ぶため、適切な認証情報（JQUANTS_REFRESH_TOKEN）が必要です。
- 関数は DuckDB の指定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime など）を前提に実装されています。最小限のスキーマ初期化は利用側で行ってください（例: ETL が必要なテーブルを作成します）。

---

## 設計上の注意・運用メモ

- Look-ahead バイアス対策
  - 多くの処理は target_date ベースで実装され、datetime.today()/date.today() を直接参照しないように設計されています（バックテストや再現性の確保のため）。

- 自動 .env ロード
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` → `.env.local` の順で読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- フェイルセーフ
  - LLM / API 呼び出しはリトライやフォールバック値（例: macro_sentiment=0.0）を用意しており、外部サービス障害時でも処理全体が崩れないよう配慮されています。

- 冪等性
  - jquants_client の保存関数は INSERT ... ON CONFLICT DO UPDATE により冪等に保存します。
  - ETL はバックフィルや差分取得をサポートしています。

---

## ディレクトリ構成（主要ファイル）

（ルートから見た代表的なソース構成を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                        — ニュース NLP（銘柄ごとのセンチメント）
    - regime_detector.py                 — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント（取得・保存）
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - etl.py                             — ETL 再エクスポート
    - quality.py                          — データ品質チェック
    - calendar_management.py             — 市場カレンダー管理
    - news_collector.py                   — RSS ニュース収集
    - audit.py                            — 監査ログテーブル初期化
    - stats.py                            — 統計ユーティリティ（z-score 等）
  - research/
    - __init__.py
    - factor_research.py                 — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py             — 将来リターン計算 / IC / 統計サマリー
  - ai/, data/, research/ はそれぞれ公開 API を __all__ で定義

補足:
- 一部パッケージ（strategy, execution, monitoring 等）は __init__.py の __all__ に含まれていますが、該当実装がこのコード抜粋内に含まれていない場合があります。リポジトリ全体での構成を確認してください。

---

## テスト・開発

- テストを書いている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、環境依存を切り離してテスト実行してください。
- LLM 呼出しやネットワークを含む箇所はモック可能な設計（内部の _call_openai_api などを patch）になっています。

---

ご不明点や README に追加したい具体的な使用例（例: CI / デプロイ手順、cron ジョブ設定、docker-compose 構成など）がありましたら教えてください。それらに合わせたセクションを追記します。