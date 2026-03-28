# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。J-Quants / RSS / OpenAI（LLM）など外部データを取り込み、ETL・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログの仕組みを提供します。

主な想定用途
- J-Quants から株価・財務・カレンダーを定期取得する ETL パイプライン
- ニュース記事の収集・前処理・LLM による銘柄センチメント算出
- マーケットレジーム（強気／中立／弱気）判定（ETF + LLM）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 発注・約定の監査ログスキーマ初期化（DuckDB）

---

## 機能一覧

- 環境変数・設定読み込み（.env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants クライアント
  - 株価日足 / 財務データ / 市場カレンダー / 上場銘柄情報の取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動リフレッシュ
- ETL パイプライン（data.pipeline）
  - run_daily_etl: カレンダー -> 株価 -> 財務 -> 品質チェック の順で実行
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を ETLResult で返却
- データ品質チェック（data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合 の検出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定・前後営業日の取得・カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理
- ニュースNLP（ai.news_nlp）
  - gpt-4o-mini を用いた銘柄別センチメントスコア付与（ai_scores テーブルへ書き込み）
  - バッチ・リトライ・レスポンス検証
- レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して日次で market_regime を記録
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions といった監査テーブルの DDL と初期化ユーティリティ
  - init_audit_db で監査DB（DuckDB）を初期化

---

## 必要な環境変数（代表）

以下の環境変数が利用されます。関数によっては引数で API キーを渡すことも可能です（例: score_news, score_regime）。

必須（一般的に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で利用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知に利用する場合
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化
- KABUSYS 自動読み込み時、プロジェクトルートは .git または pyproject.toml を探索して決定

DB パス（デフォルト値あり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）

備考: リポジトリルートに .env.example を用意しておき、その内容を参考に .env を作成してください（config.Settings._require が未設定時に ValueError を投げます）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数設定
   - リポジトリルートに .env を作成（.env.example を参考に）
   - または、必要な環境変数をシェルに直接 export しても可
   - 自動 .env ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. （任意）パッケージとしてインストール（開発モード）
   - pip install -e .

---

## 使い方（主要な例）

以下は Python REPL やスクリプトから呼び出す際の例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

基本的な準備
- DuckDB 接続を作る（デフォルトの DUCKDB_PATH を使う場合）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次パイプライン）実行例
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニュースセンチメントスコア生成（LLM を使う）
- from datetime import date
- from kabusys.ai.news_nlp import score_news
- # OPENAI_API_KEY が環境変数に設定されている前提
- n_written = score_news(conn, target_date=date(2026, 3, 20))
- print(f"ai_scores に書き込んだ銘柄数: {n_written}")

市場レジーム判定（ETF + マクロニュース + LLM）
- from datetime import date
- from kabusys.ai.regime_detector import score_regime
- res = score_regime(conn, target_date=date(2026, 3, 20))
- print("score_regime 完了:", res)

監査ログ用 DB 初期化（監査専用 DB）
- from pathlib import Path
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db(Path("data/audit.duckdb"))
- # audit_conn は監査テーブルが初期化済みの接続

J-Quants の ID トークンを取得（テストや確認用）
- from kabusys.data.jquants_client import get_id_token
- token = get_id_token()  # JQUANTS_REFRESH_TOKEN を使う

ユーティリティ（リサーチ）
- from kabusys.research import calc_momentum, zscore_normalize
- momentum = calc_momentum(conn, target_date=date(2026,3,20))
- normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意点
- LLM 呼び出し（OpenAI）は API キー・コスト・レート制限に注意してください。
- 関数は Look-ahead バイアス対策として内部で datetime.today() を参照しない設計のものが多く、target_date を明示することを推奨します。
- score_news / score_regime は api_key を引数で渡すことも可能（環境変数に頼らないテスト時に便利）。

---

## 開発者向けの挙動メモ

- 設定モジュール (kabusys.config) は .env / .env.local を自動的にプロジェクトルートから読み込みます（CWD に依存しない探索）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を用いる関数は多くが executemany / トランザクションを用いて冪等性を保つよう設計されています。
- ニュース収集は SSRF・gzip爆弾・トラッキングパラメータ除去などの安全対策を備えています。
- OpenAI 呼び出しは JSON mode を使い、レスポンスの厳密なバリデーションを行っています。API 障害時はフェイルセーフ（0.0 フォールバック 等）として続行する設計です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメント（LLM）処理
  - regime_detector.py     # マーケットレジーム判定
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py               # 監査ログスキーマ / init
  - jquants_client.py      # J-Quants API クライアント（取得・保存）
  - news_collector.py      # RSS 収集・前処理
  - pipeline.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ名は README の先頭の __all__ に合わせて利用される想定)
- execution/（発注関連は別モジュールで実装予定）
- strategy/（戦略定義用モジュール）

※ 上記は主要モジュールを抜粋したものです。実装詳細は各モジュールの docstring を参照してください。

---

## ライセンス・貢献

README にライセンス表記が含まれていない場合はリポジトリの LICENSE を確認してください。バグ報告や機能改善のプルリクエストは歓迎します。

---

もし特定の機能（例: ETL の cron 実行例、news_collector を DB に永続化する具体的手順、kabu API とブローカー連携方法など）について README に追加したい場合は、どの機能の使用例をより詳しく記載するか教えてください。