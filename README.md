# KabuSys

日本株自動売買プラットフォームのコアライブラリ群（ETL / データ品質 / 研究 / AI スコアリング / 監査ログ / カレンダー管理 等）。

このリポジトリは DataPlatform.md / StrategyModel.md に基づいて設計された内部ライブラリで、J-Quants API・OpenAI・kabuステーション等と連携してデータ取得・前処理・特徴量計算・AIスコアリング・監査ログ保存までのパイプラインを提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants から株価（日足）、財務、上場銘柄情報、マーケットカレンダーを差分取得・保存（ページネーション・冪等処理対応）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合の検出（quality module）
- カレンダー管理
  - JPX カレンダー取得・夜間更新ジョブ、営業日／SQ判定等
- ニュース収集
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
- AI スコアリング（OpenAI）
  - ニュースベースの銘柄別センチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime） — ETF 1321 の MA とマクロニュースセンチメントを合成
  - OpenAI の JSON Mode を用いた堅牢な呼び出し・リトライ処理
- リサーチ／特徴量
  - Momentum / Volatility / Value 等のファクター計算（research パッケージ）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数からの設定ロード（自動ロードは無効化可能）

---

## 必要な環境変数

以下はコード内で参照される主要な環境変数です（README 用に抜粋）。

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など）（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' / 'paper_trading' / 'live')（デフォルト: development）
- LOG_LEVEL — ログレベル（'DEBUG','INFO',...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化フラグ（"1" を設定すると .env 自動読み込みを無効化）

自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順（開発環境）

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください（本コードスニペットは README 用の簡易例です）。

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数を用意
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 自動読み込みは .env（優先度低）→ .env.local（優先度高）の順で行われます（ただし OS 環境変数が最優先）。

5. データベース用ディレクトリ作成
   - デフォルトの DUCKDB_PATH が data/kabusys.duckdb の場合:
     - mkdir -p data

---

## 使い方（簡易例）

以下のサンプルは最小限の呼び出し例です。実際はログ設定・エラーハンドリング等を追加してください。

- DuckDB 接続を作る:

  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = settings.duckdb_path  # 環境変数で上書き可能
  conn = duckdb.connect(str(db_path))

- 日次 ETL を実行する:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が対象（内部は営業日に調整される）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（OpenAI を利用）:

  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
  print(f"scored {n} codes")

- 市場レジーム判定:

  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキーを省略すると環境変数 OPENAI_API_KEY を使用

- 監査ログスキーマ初期化:

  from kabusys.data.audit import init_audit_db, init_audit_schema

  # 監査用 DB を初期化し接続を取得
  audit_conn = init_audit_db("data/audit.duckdb")
  # ある既存接続に監査テーブルを追加したい場合:
  init_audit_schema(conn, transactional=True)

- カレンダー更新ジョブ（夜間バッチ）:

  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved {saved} calendar records")

備考:
- OpenAI 呼び出しは rate limit・ネットワークエラー等に対してリトライ・フェイルセーフ実装があります。API キーが未設定の場合は ValueError が発生します。
- settings（kabusys.config.settings）を経由して各種パスやフラグを参照できます。

---

## よくある注意点・トラブルシューティング

- 環境変数未設定に起因するエラー:
  - settings のプロパティは必須変数が無い場合 ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。
- .env 自動読み込み:
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索します。CWD に依存しない設計です。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の制約:
  - 一部の実装で空リストを executemany に渡すと失敗するため、空チェックが行われています。
- OpenAI / J-Quants API は実運用でレート制限に注意してください（実装内でスロットリング・リトライを実施しています）。
- ニュース RSS の取得には SSRF 対策や受信上限バイト数チェックがあります。外部から追加する RSS は http/https でかつパブリックなホストであることを確認してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（銘柄別センチメント）
  - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult の再エクスポート
  - calendar_management.py        — 市場カレンダー管理
  - news_collector.py             — RSS ニュース収集
  - quality.py                    — データ品質チェック
  - stats.py                      — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py            — Momentum / Volatility / Value 等
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- research/*（他研究用ユーティリティ）
- その他: strategy, execution, monitoring（パッケージ公開は __all__ で定義されていますが実装ファイルはリポジトリに依存します）

---

## 開発／拡張ポイント（参考）

- バックテスト / 実戦投入の際は Look-ahead バイアスに留意してください。本コードは多くの場所でルックアヘッドを防ぐ設計（target_date 未満のデータのみ参照）を採用しています。
- OpenAI の利用は JSON Mode を使った厳格なパース設計になっていますが、LLM の挙動は変化するため応答バリデーションの追加を推奨します。
- ETL の品質チェックは Fail-Fast を目指していません。ETL 完了後に発見された問題に基づきオペレーション側で対処してください。
- 監査ログ（order_requests 等）は冪等キーとトランザクション設計により重複発注防止を支援します。実際のブローカー連携実装時は broker 側の再試行/コールバック仕様に合わせた実装が必要です。

---

必要であれば、README に記載する .env.example のテンプレートや具体的な実行例（cron/airflow のジョブ定義例、Dockerfile、CI セットアップなど）を追加で作成します。どの追加情報が欲しいか教えてください。