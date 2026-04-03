# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、データ品質チェック、ニュース収集とAIによるニュース/NLP評価、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などのユーティリティを提供します。

※ この README はソースコード（src/kabusys 以下）を元に作成しています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）と DuckDB への ETL（差分更新・バックフィル）
- ニュース収集（RSS）と前処理、raw_news テーブルへの保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_scores / マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの融合）
- 研究向けファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Zスコア、IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマの作成・初期化
- 設定管理（.env / 環境変数の自動読み込み）

設計上の重要点:
- ルックアヘッドバイアス（未来情報参照）を避ける実装方針
- DuckDB を中心としたローカル DB 構成（ETL と研究用）
- LLM・外部 API 呼び出しは堅牢化（リトライ・フォールバック）され、失敗してもシステムを破綻させない設計

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの daily_quotes（raw_prices）、financial_statements（raw_financials）、market_calendar の差分取得と保存（jquants_client）
  - 日次パイプライン run_daily_etl（calendar → prices → financials → 品質チェック）
  - ETL の結果を表す ETLResult

- データ品質チェック（data.quality）
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
  - QualityIssue による問題集約

- ニュース収集 / 前処理（data.news_collector）
  - RSS フィード取得（SSRF 対策、最大受信サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定

- AI / NLP（ai.news_nlp, ai.regime_detector）
  - 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores へ保存（score_news）
  - マクロニュースと ETF(1321) の MA 乖離を合成して市場レジームを daily に判定（score_regime）
  - LLM 呼び出しはリトライ・エラーハンドリング付きでフェイルセーフに実装

- 研究用ユーティリティ（research）
  - calc_momentum / calc_value / calc_volatility（ファクター算出）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・IC 計算）
  - zscore_normalize（data.stats）

- カレンダー管理（data.calendar_management）
  - market_calendar の更新ジョブ、営業日判定、next/prev_trading_day、get_trading_days 等

- 監査ログスキーマ（data.audit）
  - signal_events, order_requests, executions テーブルの作成・初期化関数（init_audit_schema / init_audit_db）
  - 監査用インデックス定義

- 設定管理（config）
  - .env / .env.local / OS 環境変数の読み込み（優先度: OS > .env.local > .env）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）

---

## 前提 / 必要環境

- Python 3.10+
- 必要な主なライブラリ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリに加え上記をインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt/pyproject.toml がある場合はそちらを参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをプロジェクトにインストール
   - 開発環境であれば editable install:
     ```
     pip install -e .
     ```

2. 環境変数を設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL で使用）
   - 推奨 / 任意:
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD : kabuステーション API パスワード（注文機能統合時）
     - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite（デフォルト data/monitoring.db）
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PID_FILE_PATH 等

   - .env をプロジェクトルートに置くと自動で読み込まれます（.env.local が存在する場合はそれで上書きされます）。
     - 自動ロードを無効化するには環境変数を設定:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxx
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

3. DuckDB 初期スキーマ（監査ログ等）を用意する
   - 監査ログスキーマを作成する例:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)
     # 以降 conn を利用
     ```

---

## 使い方（主なユースケース）

以下は Python セッションからの利用例です。各関数は DuckDB 接続（duckdb.connect）を受け取る想定です。

- DuckDB 接続の作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（ローカル日）を使用
print(result.to_dict())
```

- 株価日足 ETL（個別実行）:
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースセンチメント評価（銘柄別）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化（ファイルパスを指定してインメモリも可）:
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db(":memory:")  # インメモリ DB
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
```

各関数は詳細な引数（例: backfill 日数、API トークン注入等）を持っています。ソースの docstring を参照してください。

---

## 設定の詳細

- 自動 .env 読み込み
  - プロジェクトルート（config._find_project_root が .git または pyproject.toml を検出）を基準に `.env` と `.env.local` を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効にする場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- settings オブジェクト
  - `from kabusys.config import settings` で取得可能。
  - プロパティ一覧（主なもの）
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - line_channel_access_token, line_user_id
    - duckdb_path, sqlite_path
    - pid_file_path, kill_flag_path, kill_flag_clear_on_start
    - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
    - env (development|paper_trading|live), log_level, is_live, is_paper, is_dev

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / .env ロードと settings
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメント（銘柄別） score_news
  - regime_detector.py    — マクロ + MA による市場レジーム判定 score_regime
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダーの管理 / 更新 / 営業日判定
  - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py            — 日次 ETL 実装（run_daily_etl 等）
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - quality.py             — データ品質チェック（QualityIssue）
  - audit.py               — 監査ログスキーマ作成 / 初期化
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - news_collector.py      — RSS 収集・前処理・保存
- research/
  - __init__.py
  - factor_research.py     — momentum / value / volatility ファクター
  - feature_exploration.py — forward returns / IC / summary / rank
- research.* 他のモジュール（ファクター分析）

各モジュールは docstring に詳細な処理フロー、設計方針、フォールバック・エラーハンドリング仕様が記載されています。

---

## 実運用時の注意点 / ベストプラクティス

- OpenAI や J-Quants の API キーは安全に管理してください。`.env` はリポジトリに含めないでください。
- LLM 呼び出しはリトライやレスポンス検証が組み込まれていますが、API の仕様変更や生成内容の偏りに注意してください。ログレベルを上げて挙動を監視してください。
- run_daily_etl 等は外部 API 呼び出しを含むため、スケジューラ（cron 等）で定期実行する際はタイムアウト・監視・ロギングを適切に設定してください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログはデータ削除を前提としていません。
- テストでは settings の自動 .env 読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して環境を安定させるとよいです。

---

## 参考 / 追加情報

- 主要な設計方針（コード内 docstring）
  - ルックアヘッドバイアス防止（target_date を明示、datetime.today() を参照しない等）
  - ETL は差分更新とバックフィル戦略
  - API 呼び出しの堅牢化（リトライ、指数バックオフ、トークン自動リフレッシュ）
  - DB 保存は可能な限り冪等（ON CONFLICT/UPSERT）で実装

詳細は各モジュールの docstring を参照してください。

---

問題や追加してほしい使い方（例: CLI 提供、Docker 化、CI テスト例など）があれば教えてください。README に追記します。