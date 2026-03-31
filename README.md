# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価（日足）、財務情報、上場銘柄情報、JPX カレンダー取得
  - レート制限遵守・リトライ・トークン自動リフレッシュを備えたクライアント
- ETL パイプライン
  - 日次差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult として返却
- データ管理ユーティリティ
  - カレンダー管理（営業日判定、次/前営業日取得、カレンダー更新ジョブ）
  - ニュース収集（RSS）と前処理（SSRF 対策・サイズ制限・URL 正規化）
  - 監査ログ（signal / order_request / execution）のスキーマ作成と DB 初期化
- AI（LLM）連携
  - ニュースを銘柄ごとにまとめて LLM でセンチメント評価（gpt-4o-mini を想定）
  - マクロニュースと ETF の MA200 乖離を合成して市場レジーム判定
  - 再試行・フォールバック（API 失敗時は中立扱い）などの安全設計
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- DuckDB を中心としたデータ永続化（冪等保存を前提）

---

## 必須環境変数

以下はコード内で参照される主要な環境変数です（README 用に抜粋）。

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants のリフレッシュトークン
- OPENAI_API_KEY（LLM を使う場合、score_news/score_regime の引数でも渡せる）
- KABU_API_PASSWORD（kabuステーション API 用）
- KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（Slack 通知を使う場合）
- SLACK_CHANNEL_ID（Slack 通知先）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

自動で .env/.env.local をプロジェクトルートから読み込みます（ルート判定は .git または pyproject.toml に基づく）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向けの例）

1. Python 環境を準備（推奨: 3.10+）
2. リポジトリをクローンしてパッケージをインストール
   - pip を使う例:
     - pip install -r requirements.txt  がある場合はそれに従ってください。
     - 最低限必要なパッケージ（例）:
       - duckdb
       - openai
       - defusedxml
   - 開発インストール:
     - pip install -e .
3. 環境変数を設定
   - プロジェクトルートに `.env` を作成して上記の必須変数をセットしてください。
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
4. DuckDB ファイル用ディレクトリを作成（必要なら）
   - mkdir -p data

注意: ネットワーク API（J-Quants / OpenAI / RSS フィード）を使う機能は実ネットワーク接続と有効な API キーが必要です。テストではモックを利用する設計になっています（コード内に差し替えポイントあり）。

---

## 使い方（主要 API サンプル）

以下は代表的な利用例です。各関数は duckdb 接続や target_date（date オブジェクト）を受け取ります。

- DuckDB 接続の作成（例）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントを評価して ai_scores に書き込む
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - print(f"scored {count} symbols")

- 市場レジーム判定を実行する
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 研究用ファクター計算（例: モメンタム）
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # 既に存在する DuckDB 接続にスキーマを追加する場合:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- J-Quants ID トークンを明示的に取得する
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()  # settings.jquants_refresh_token を使用

注意点:
- score_news / score_regime は OpenAI API 呼び出しを行います。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。空文字列も未設定として扱われます。
- 多くの機能はローカル DB（DuckDB）上のテーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を前提とします。ETL を先に実行してデータを揃えてください。
- ETL / データ処理関数はルックアヘッドバイアス防止のため内部で datetime.today() を直接参照しない方針です（target_date を明示してください）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（LLM）と ai_scores 書き込み
  - regime_detector.py — ETF MA200 とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - etl.py — ETL インターフェース（ETLResult 再エクスポート）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - stats.py — Zスコア正規化など統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - jquants_client.py — J-Quants API クライアント（取得 / 保存ロジック）
  - news_collector.py — RSS ニュース収集（SSRF 対策・前処理）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク
- research/（内部ユーティリティ）
  - ...（上記参照）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る設計で、外部ステートを最小化しています。AI 関連は OpenAI の Python SDK を使う想定（呼び出し時に OpenAI クライアントを内部生成）。

---

## テスト・開発向けヒント

- API 呼び出し部分（OpenAI / J-Quants / HTTP）には差し替え用ポイント（関数レベルでのモック）が用意されています。ユニットテストでは unittest.mock.patch() で外部依存をモックしてください。
- .env 自動読み込みはプロジェクトルートを .git または pyproject.toml から検出します。テスト実行時に自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に対する互換性対応がコード内にあるため、最新環境でも動作しますが、DuckDB のバージョン差異に注意してください。

---

README の内容はコードの実装に基づく概要です。詳細な API 引数や返り値、テーブルスキーマは各モジュールの docstring / 関数コメントを参照してください。もし README にサンプルスクリプトや requirements.txt、実行時の推奨コマンド（例: systemd / cron / Airflow での運用例）を追加したい場合は用途（運用：ETLジョブ、研究：単体利用、製品：本番運用）を教えてください。