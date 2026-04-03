# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買基礎ライブラリです。J-Quants / RSS / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- データ収集・ETL（J-Quants API を使用した株価・財務・市場カレンダー取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュースNLP（OpenAI を用いた銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、将来リターン、IC 等）
- 監査ログ（signal → order_request → execution のトレーサビリティを保持する監査 DB 初期化ユーティリティ）
- 設定管理（.env / 環境変数の自動読み込み、プロジェクトルート探索）

主な設計方針として、ルックアヘッドバイアス防止、フェイルセーフ（API失敗時に処理継続）、および DuckDB を用いた冪等保存を重視しています。

---

## 主な機能一覧

- kabusys.config
  - .env 自動ロード（.env, .env.local、OS環境変数優先）。必須変数未設定時はエラーを投げるユーティリティを提供。
- kabusys.data
  - jquants_client: J-Quants からのデータ取得 / DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL ランナー（run_daily_etl）と ETL 結果（ETLResult）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - news_collector: RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去）
  - calendar_management: 営業日判定・calendar 更新ジョブ
  - audit: 監査ログ用スキーマ初期化 / init_audit_db
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

1. Python バージョン
   - Python 3.10 以上（| 型注釈等を使用しているため）

2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて他の HTTP / テスト用ライブラリ）
   インストール例:
   ```
   pip install duckdb openai defusedxml
   ```

3. ソースを配置
   - リポジトリをクローンし、パッケージを使えるようにする（開発モード推奨）:
   ```
   git clone <repo>
   cd <repo>
   pip install -e .
   ```

4. 環境変数（.env）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます（`.env.local` は上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
   - 主な設定項目:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
     - OPENAI_API_KEY (任意) — OpenAI API キー（score_news 等で使用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意) — 通知用
     - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (任意) — 監視 DB: data/monitoring.db
     - PID_FILE_PATH / KILL_FLAG_PATH / 閾値等（監視用）
     - KABUSYS_ENV — development / paper_trading / live
     - LOG_LEVEL — DEBUG/INFO/...
   - .env の書式はシェルの `KEY=VALUE`（シングル/ダブルクォート対応、コメント対応）です。

---

## 使い方（簡易例）

以下は最小限の Python 呼び出し例です。DuckDB ファイルパスや API キーを環境変数で設定してください。

1) DuckDB 接続を作成して日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（score_news）を実行:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定しておく
print(f"scored {written} codes")
```

3) 市場レジーム判定（score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

注意:
- OpenAI 呼び出しは API レートやコストがかかります。`api_key` を引数で渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- 多くの関数は DuckDB のテーブルスキーマに依存します（スキーマ初期化は別途実行してください）。

---

## 主要モジュールと責務（概要）

- kabusys.config: 環境変数・.env の読み込みと Settings クラス
- kabusys.data.jquants_client: J-Quants からの取得、DuckDB への保存（save_*）
- kabusys.data.pipeline: run_daily_etl / run_*_etl / ETLResult
- kabusys.data.quality: データ品質チェック（run_all_checks 等）
- kabusys.data.calendar_management: 営業日判定/カレンダー更新ジョブ
- kabusys.data.news_collector: RSS フィード取得と前処理（SSRF対策等）
- kabusys.data.audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp: ニュースを LLM で評価して ai_scores へ書き込み
- kabusys.ai.regime_detector: 市場レジーム判定ロジック（MA + マクロセンチメント）
- kabusys.research.*: ファクター計算・特徴量分析ユーティリティ
- kabusys.data.stats: zscore_normalize 等の共通統計関数

---

## ディレクトリ構成

(抜粋: 主要ファイルのみ。実際のリポジトリには pyproject.toml 等が含まれます)

- src/
  - kabusys/
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
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - audit.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/  (README の要求に基づきトップ-level に存在する想定モジュール)
    - execution/   (約定・オーダー実行周りの実装想定)
    - strategy/    (戦略定義用モジュール群)

---

## 運用上の注意・ヒント

- .env 自動ロードはプロジェクトルート検出（.git または pyproject.toml）を行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。
- J-Quants のレート制限や OpenAI の API コストに注意してください（モジュールにレート・リトライ対策あり）。
- DuckDB による保存は多くが ON CONFLICT DO UPDATE（冪等）で書き込みます。バックフィルや部分失敗時の挙動は各関数のドキュメントを参照してください。
- テスト容易性のため、OpenAI 呼び出しや URL オープンなどはモック可能な内部関数に分離されています（ユニットテストで差し替えが可能）。

---

必要に応じて README にチュートリアル（ETL の定期実行 cron / systemd 設定例、監視設定、データスキーマ定義ファイル）を追加できます。追加の要求があれば、目的に合わせて詳しいガイド（例: バックテスト手順、運用チェックリスト）を作成します。