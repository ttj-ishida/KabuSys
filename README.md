# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants や RSS、OpenAI（LLM）など外部データを取り込み、ETL・データ品質チェック・特徴量計算・ニュース NLP・市場レジーム判定・監査ログなど、取引システム構築に必要なコンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足・財務データ・市場カレンダーを差分取得／保存 (duckdb)
  - 差分取得、バックフィル、ページネーション対応、レート制御、トークン自動リフレッシュ
- データ品質管理
  - 欠損・スパイク・重複・日付不整合などの品質チェック機能
- ニュース収集・NLP
  - RSS フィードの安全な収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_score）
- 市場レジーム判定
  - ETF（1321）の200日MA乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を算出
- リサーチ用ユーティリティ
  - モメンタム・バリュー・ボラティリティなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を持つ監査テーブル DDL と初期化ユーティリティ
  - 発注フローの冪等性・トレース保証
- 設定管理
  - .env ファイルや環境変数からの設定読み込み（プロジェクトルート探索、自動読み込み機能あり）
  - 実行環境（development / paper_trading / live）やログレベル管理

---

## 前提・準備

- 推奨 Python バージョン: 3.10+
  - （コード中で `X | None` 型や `from __future__ import annotations` を使用しています）
- 主な依存パッケージ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで足りる部分が多い設計ですが、上記は必須）

requirements.txt を用意する場合の例:
```
duckdb>=0.7
openai>=1.0
defusedxml>=0.7
```

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
   ```

2. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt がない場合は上のパッケージを個別に pip install してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（デフォルト）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数（必須/任意の一覧）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 BOT トークン
   - SLACK_CHANNEL_ID (必須) — Slack のチャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (任意) — one of: development, paper_trading, live
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL
   - OPENAI_API_KEY (必須: AI 機能を使う場合) — OpenAI API キー

   .env の雛形はプロジェクトに `.env.example` があればそれを参考にしてください。

4. DuckDB 等データベース初期化（監査ログ用の例）
   Python から監査 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（主要な例）

以下はライブラリ関数を直接呼ぶサンプルです。実運用では各関数をジョブスケジューラや CLI から呼び出します。

- 日次 ETL の実行（prices / financials / calendar の差分 ETL + 品質チェック）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日を対象
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込み件数:", n_written)
  ```

- 市場レジーム判定（ma200 と マクロニュースの LLM 合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算の例
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
- AI 関連関数（score_news, score_regime）は OpenAI API キーが必要です。api_key を引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB のスキーマ（テーブル定義）は外部で初期化する必要があります（ETL を実行する際に該当テーブルが必要）。監査テーブルは `init_audit_schema` / `init_audit_db` で作成可。
- テストや CI で自動環境変数読み込みを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 設計上のポイント（短く）

- ルックアヘッドバイアス防止: 各日次処理は内部で datetime.today() を直接参照しない・DB クエリに明示的な排他条件を置く設計。
- 冪等性: DB 保存処理は ON CONFLICT（または個別 DELETE → INSERT）で冪等を保つ。
- フェイルセーフ: 外部 API 失敗時は例外を即投げずフォールバック動作（多くはスキップして継続）を行う。
- セキュリティ / 安全性: RSS の SSRF 対策、defusedxml の利用、.env 読み込み時の保護キーなど。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル/モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の自動読み込み、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント算出（OpenAI 呼び出し、バッチ処理、検証）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー処理（営業日判定・更新ジョブ）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - pipeline.py            — 日次 ETL 実装（prices/financials/calendar の差分取得）
    - stats.py               — z-score 正規化など統計ユーティリティ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ定義・初期化
    - jquants_client.py      — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py      — RSS 収集・前処理・保存ヘルパー
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - その他モジュール（strategy / execution / monitoring 等）はパッケージ公開対象として __all__ に含まれますが、実装ファイルはプロジェクト内の用途に応じて配置されています。

---

## 補足・運用上の注意

- 本ライブラリはデータ取得や発注など外部 API を扱います。実口座での運用時は paper_trading モードや十分なログ・監査を行い、安全性を担保してください。
- OpenAI 呼び出しのテスト時はモック化（関数の差し替え）を推奨します。news_nlp と regime_detector の _call_openai_api はテスト時に patch して差し替えできる設計です。
- DuckDB のバージョン差異により executemany の空リストに関する挙動などがあるため、DB 操作時は既定の互換性対策に注意しています。

---

必要があれば、README に以下を追加できます:
- 具体的なテーブルスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime など）
- サービス向けの systemd ユニット例や cron / Airflow ジョブの例
- .env.example の具体例
- CI / テストの記載

どの追加情報が必要か教えてください。