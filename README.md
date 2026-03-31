# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームライブラリです。  
J-Quants や RSS からのデータ収集、DuckDB を使った ETL、データ品質チェック、ファクタ計算、LLM を使ったニュース解析や市場レジーム判定、発注監査ログなどを含む一連の機能を提供します。

主な目的は「データの取得 → 品質管理 → 特徴量/ファクター計算 → シグナル生成 → 発注監査」までのワークフローをライブラリとして安定して実行できることです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主な API と利用例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数／設定項目
- テスト・開発時のヒント

---

## プロジェクト概要

- DuckDB をデータストアに用いて、J-Quants API から株価・財務・マーケットカレンダーを差分取得し、冪等的に保存する ETL パイプラインを実装しています。
- RSS からニュースを収集し、OpenAI（gpt-4o-mini 等）を用いて銘柄ごとのセンチメント評価（ai_scores）や、マクロニュースを元にした市場レジーム判定を行います。
- データ品質チェック、マーケットカレンダーヘルパー、ファクター計算、IC 等のリサーチユーティリティ、そして発注・約定の監査ログ初期化機能を備えます。
- 本リポジトリはバックテストや実運用の基盤（データ取得・監査・AI スコアリング）を提供することを主眼としています。

---

## 機能一覧

- 環境設定読み込み（.env / .env.local と OS 環境変数の統合）
- J-Quants クライアント
  - 株価日足（OHLCV）取得・保存（ページネーション・レート制御・リトライ対応）
  - 財務データ取得・保存
  - マーケットカレンダー取得・保存
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果は ETLResult に集約
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS フィードの安全な収集（SSRF 対策、gzip 対応、サイズ制限）
  - raw_news / news_symbols への冪等保存を想定
- ニュース NLP（OpenAI）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - 複数銘柄をバッチで評価し、レスポンス検証・リトライ対応
- 市場レジーム判定
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを合成して bull/neutral/bear を判定
- リサーチ（factor / feature exploration）
  - モメンタム、ボラティリティ、バリュー系ファクター計算
  - 将来リターン計算 / IC / 統計サマリー / Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema（UTC タイムゾーン固定）
- ユーティリティ
  - 統計関数（zscore_normalize）等

---

## セットアップ手順

前提:
- Python 3.9+（型記述で | を使うため 3.10 以上を推奨）
- system によっては libssl 等の依存が必要な場合があります

1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - ここでは主要な依存を列挙します（実際は requirements.txt を用意してください）。
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. プロジェクトをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートの .env または .env.local に必要な設定を記載できます（下記「環境変数」参照）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主要）

以下はコード内で参照される主要な環境変数です。必須項目は Settings._require で要求されます。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注系がある場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

例 (.env):
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxxx
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789

---

## 使い方（主要な利用例）

以下はライブラリを使う際の代表的なコード例です。DuckDB 接続は duckdb.connect(path) を使います。

- 基本的な準備
  - Python REPL またはスクリプト内で:

    from datetime import date
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行

    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（OpenAI API キーを環境変数で設定するか api_key を渡す）

    from datetime import date
    from kabusys.ai.news_nlp import score_news

    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"wrote scores for {n_written} symbols")

  - テストや明示的にキーを渡したい場合:
      score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定

    from kabusys.ai.regime_detector import score_regime

    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（監査用の独立 DuckDB を作る）

    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- カレンダー操作（営業日取得など）

    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    is_td = is_trading_day(conn, date(2026,3,20))
    next_td = next_trading_day(conn, date(2026,3,20))

- ETLResult の扱い
  - run_daily_etl は ETLResult を返します。result.to_dict() でログ保存や監査に利用できます。

注意:
- OpenAI 呼び出しは API キーが必要です（環境変数 OPENAI_API_KEY または関数引数）。
- API 呼び出しはリトライ・バックオフが組み込まれており、失敗時はフェイルセーフ（多くのケースでスコア 0 にフォールバック）を採用しています。
- DuckDB に対する executemany の空リスト渡しに注意（コード内で保護されています）。

---

## ディレクトリ構成（主要ファイルと説明）

概略（src/kabusys 配下）:

- __init__.py
  - パッケージのエクスポート定義とバージョン

- config.py
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - Settings クラス（環境変数アクセス）

- ai/
  - __init__.py
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py — ETF 1321 の MA200 とマクロニュースで市場レジームを判定

- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 取得・前処理・記事 ID 正規化・SSRF 対策
  - calendar_management.py — market_calendar の更新・営業日判定ユーティリティ
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ

- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー / rank 等

各モジュールはソースの docstring に詳細な設計方針や使用上の注意が記載されています。実装を読むことで振る舞い（ロールバック、リトライ、フェイルセーフ等）を把握できます。

---

## テスト・開発時のヒント

- OpenAI への実際の API 呼び出しを避けたいテストでは、news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替え可能です。
- .env の自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境で便利）。
- DuckDB 接続はメモリモード ":memory:" を使うことで一時 DB を構築できます。
- audit.init_audit_schema は transactional オプションを持ちます（デフォルト False）。監査スキーマの初期化は基本的に transactional=True を推奨します。

---

もし README に追加してほしいサンプルスクリプト（例: 定期実行用 cron スクリプト、Dockerfile、requirements.txt のテンプレ）や、各テーブルのスキーマ（raw_prices, raw_news, ai_scores 等）についての詳細が必要であれば教えてください。README をその内容に合わせて拡張します。