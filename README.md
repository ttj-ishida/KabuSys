# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL（J-Quants）による市場データ収集、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

主な設計思想：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を盲目的に参照しない）
- DuckDB を中心にしたローカルデータ管理（冪等保存）
- 外部 API は慎重にラップ（レート制御、リトライ、トークン自動更新）
- API 失敗時はフェイルセーフ（スコア 0.0 やスキップ）でパイプライン継続

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルートを探索、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- データ取得 / ETL（J-Quants）
  - 株価日足（raw_prices）取得・保存（差分＆ページネーション）
  - 財務データ取得・保存（raw_financials）
  - JPX マーケットカレンダー取得・保存
  - ETL パイプライン（run_daily_etl） + 品質チェック（quality）
- ニュース収集 / NLP
  - RSS 取得（SSRF対策、サイズ上限、トラッキング除去）
  - ニュースの銘柄紐付けおよび ai_scores への書き込み
  - OpenAI（gpt-4o-mini）を使ったバッチセンチメント評価（JSON Mode）
- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離 + マクロニュースの LLM センチメントから daily レジーム判定（bull/neutral/bear）
- リサーチ（ファクター計算）
  - Momentum / Value / Volatility 等の計算（prices_daily, raw_financials 参照）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルと初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注から約定までのトレーサビリティ確保
- 共通ユーティリティ
  - 統計ユーティリティ、カレンダー管理、J-Quants クライアント、OpenAI 呼び出しラッパー（各モジュール独立）

---

## 必要な環境変数

主に以下を使用します（プロジェクトでは .env を用意して設定するのが想定されています）。

必須（Settings._require で必須チェックされるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト：development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする場合は `1` を設定
- KABUSYS の DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- OPENAI_API_KEY — ai モジュールで使用（関数に直接 api_key を渡すことも可能）

.env の取り扱い:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- `.env.local` は `.env` の上書き（override）に使えます。
- テスト時などに自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発環境向け）

1. Python 3.10+ を用意（typing の union | を用いるコードが含まれます）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb openai defusedxml
   - ※ 実プロジェクトでは requirements.txt / pyproject.toml に依存を追加してください
4. パッケージをインストール（開発時）
   - pip install -e .
5. .env を作成（または環境変数を設定）
   - .env.example があれば参照してください（本コードベースは例示のみ）
   - 最低限 JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD を設定してください

注意点:
- OpenAI 呼び出しを行うには OPENAI_API_KEY を設定するか、score_news / score_regime に api_key を渡してください。
- J-Quants API の呼び出しはレート制限があるため、run 系は慎重に運用してください。

---

## 使い方（主なユーティリティ例）

以下は Python REPL / スクリプトからの利用例です。共通して duckdb の接続を渡します。

- DuckDB 接続を作る（ファイル DB）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（データ取得・品質チェック）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースの NLP スコアリングを実行（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - score_count = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"scored {score_count} symbols")

  - 直接 API キーを渡す場合:
    - score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
  - res = score_regime(conn, target_date=date(2026,3,20))
  - print("done", res)

- 監査ログ用 DB 初期化（発注／約定トレース用）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - ※ init_audit_db は transactional=True でスキーマを作成します

- ニュース RSS を取得して raw_news に保存するワークフロー
  - RSS の取得は kabusys.data.news_collector.fetch_rss を使い、取得記事を DB に保存するロジックを組みます（この README の範囲外ですが、fetch_rss は記事の正規化・SSRF 対策・サイズ制限を行います）。

ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（OpenAI バッチ処理）
  - regime_detector.py — 市場レジーム判定ロジック（MA + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定、update job）
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore 正規化）
  - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
  - audit.py — 監査ログスキーマ定義・初期化（signal/order/execution）
  - jquants_client.py — J-Quants API クライアント（取得＋DuckDB 保存）
  - news_collector.py — RSS 収集・正規化・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ等の計算
  - feature_exploration.py — 将来リターン / IC / サマリー 等
- research/*, data/* はリサーチ／データ基盤関連のユーティリティ群

ドキュメント / 設定ファイル（プロジェクトルート、例示）
- .env, .env.local（任意）
- pyproject.toml / setup.cfg（パッケージ管理）

---

## 実装上の注意点（運用時のポイント）

- Look-ahead バイアスを避けるため、関数は target_date を明示受け取り、内部で現在時刻を乱用しません。テストやバックテストでは必ず target_date を固定してください。
- API 呼び出しには各種リトライとレート制御が組み込まれていますが、運用時は実際の API 制限に対して十分に余裕を持たせてください（J-Quants: 120 req/min 等）。
- OpenAI 呼び出しはレスポンスの JSON 検証を行い、不正なレスポンスや API 失敗時は安全側でフォールバックします（ゼロスコアやスキップ）。
- DuckDB に対する複数行挿入の扱い（executemany 等）やバージョン差異に注意してください（コード中に互換対応あり）。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。より詳細な設計仕様（StrategyModel.md / DataPlatform.md 等）や実運用手順は別途ドキュメント化することを推奨します。質問や追加で欲しい使い方例があれば教えてください。