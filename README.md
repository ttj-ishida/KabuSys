# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群です。本リポジトリは以下を主に提供します：
- J-Quants / RSS からのデータ取得（ETL）および DuckDB への保存
- ニュースの NLP による銘柄センチメント付与（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 判定を合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（トレーサビリティ）用スキーマ初期化ユーティリティ
- データ品質チェック・マーケットカレンダー管理 等

この README ではプロジェクト概要、機能一覧、セットアップ手順、簡単な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるツール群です。主な役割は「信頼できるデータ基盤（ETL / 品質チェック / カレンダー管理）」と「研究・シグナル生成（ファクター計算 / ニュース NLP / レジーム判定）」、および「監査ログ（発注→約定の追跡）」です。バックテストや本番運用における Look-ahead バイアス回避や冪等性、API レート制御、堅牢なエラーハンドリングを設計方針に持ちます。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分・バックフィルロジック、ページネーション対応、IDトークンの自動リフレッシュ、レート制御、リトライ
- ニュース収集
  - RSS フィード収集（SSRF対策、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols との紐付けと冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごと・時間ウィンドウごとのニュースをまとめて LLM に投げて ai_scores を書き込む（JSON mode）
  - エラー時のフォールバック・リトライ（429/ネットワーク/5xx など）
- 市場レジーム判定
  - ETF（1321）の200日MA乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジーム判定
  - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化
- 品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査スキーマ作成、監査専用 DB 初期化ユーティリティ

---

## セットアップ手順

以下は開発・実行に必要な一般的な手順です。プロジェクトに requirements.txt / pyproject.toml がある想定で説明します（無ければ必要なパッケージを手動でインストールしてください）。

1. Python 環境
   - Python 3.10+ を推奨

2. リポジトリをクローンして依存関係をインストール
   - 例:
     - pip install -r requirements.txt
     - もしくは pip install .（パッケージ化されている場合）
   - 本コードで使われる主なライブラリ:
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリのみで使える機能も多いです）

3. 環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で必要）
   - KABU_API_PASSWORD : kabuステーションAPI パスワード（使用する場合）
   - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID : Slack 通知のチャンネル ID
   - これらは .env / .env.local に記載しておけます（config モジュールが自動ロード）
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

4. .env 自動ロードについて
   - パッケージ内の config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` → `.env.local` の順で自動読み込みします。
   - 読み込みルール：
     - OS 環境変数 > .env.local > .env
     - .env.local は .env の値を上書きする（ただし既に OS 環境にあるキーは保護されます）

5. データベース初期化（監査用）
   - 監査ログ専用 DB を作る場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
   - これにより監査用テーブル群とインデックスが作られます（UTC タイムゾーン固定）

---

## 使い方（代表例）

以下はライブラリ関数を直接使う簡単な例です。実際はロガー設定や例外処理、スケジューラ（cron 等）との組合せで運用します。

1. 設定の利用
   - from kabusys.config import settings
   - settings.jquants_refresh_token, settings.duckdb_path などで設定値を参照できます

2. DuckDB 接続を作成
   - import duckdb
   - conn = duckdb.connect(str(settings.duckdb_path))

3. 日次 ETL の実行（株価・財務・カレンダー・品質チェック）
   - from kabusys.data.pipeline import run_daily_etl
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - result は ETLResult オブジェクト（fetched/saved・quality issues・errors を含む）

4. ニュースの NLP（銘柄別スコア付与）
   - from kabusys.ai.news_nlp import score_news
   - written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
   - 戻り値は書き込んだ銘柄数

5. 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
   - DB の market_regime テーブルへ冪等書き込みされます

6. 監査用 DB 初期化（監査ログ）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/monitoring/audit.duckdb")

7. 研究用ファクター計算 / 正規化
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - mom = calc_momentum(conn, target_date=date(2026, 3, 20))
   - from kabusys.data.stats import zscore_normalize
   - norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])

8. 品質チェックの実行
   - from kabusys.data.quality import run_all_checks
   - issues = run_all_checks(conn, target_date=date(2026, 3, 20))
   - issues は QualityIssue のリスト（severity, detail, sample rows を含む）

注意点：
- OpenAI 呼び出しはレスポンスフォーマット（JSON mode）を前提としています。API キーは OPENAI_API_KEY 環境変数で供給するか、関数引数で渡してください。
- ETL / API 呼び出しはネットワーク・API レートに依存するため実行時にリトライ・ログを確認してください。

---

## よく使う設定/環境変数（一覧）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP/Regime) — OpenAI API キー
- KABU_API_PASSWORD — kabu ステーション API パスワード（使用時）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)

.env/.env.local にこれらを配置して使うのが簡便です。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主なファイル・モジュール構成の抜粋です。各ファイルに詳細な docstring があり、内部設計・方針が記載されています。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（OpenAI）: score_news, calc_news_window 等
    - regime_detector.py   — 市場レジーム判定: score_regime
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント / save_* / fetch_*
    - pipeline.py          — ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - etl.py               — ETLResult の再エクスポート
    - news_collector.py    — RSS 収集 / 前処理 / 保存
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - quality.py           — データ品質チェック
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py             — 監査ログ用 DDL/初期化
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py — 将来リターン, IC, factor_summary, rank
  - monitoring/ (公開される想定の監視モジュール群や実行監視部分が入る想定)
  - strategy/ (戦略層、未示のモジュール)
  - execution/ (発注・ブローカー連携、未示のモジュール)

各モジュールは DuckDB 接続オブジェクトを引数に受け取る関数が多く、バックテスト時にも DB を差し替えて利用できるよう設計されています。

---

## 運用上の注意点 / ベストプラクティス

- Look-ahead バイアス対策が各所に組み込まれています（関数は target_date を引数に取り内部で現在時刻を参照しない等）。バックテストで使う際は target_date を明示的に指定してください。
- OpenAI 呼び出しは外部サービス依存のため、テスト時は内部の _call_openai_api をモックすることを推奨します（score_news, regime_detector 内で設計済み）。
- ETL は差分更新 + バックフィル方式です。初回ロードやリストア時はバックフィル日数や最小日付を適切に設定してください（pipeline の _MIN_DATA_DATE）。
- DuckDB に対する executemany の空パラメータは一部バージョンで問題になるため、コード側で空チェックを行っています。独自に DB 操作を追加する際は注意してください。
- ニュース RSS の収集では SSRF 対策（プライベート IP 拒否、スキーム検査等）やレスポンスサイズ制限を行っています。外部ソース追加時は URL 検証ルールを守ってください。

---

もし README に追加したい情報（例: 実行スケジュールのサンプル cron、Docker コンテナ化手順、requirements.txt の具体的内容、より詳しい API 使用例など）があれば教えてください。必要に応じて追記・整備します。