# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買/リサーチ基盤を提供する Python パッケージです。J-Quants / kabuステーション / OpenAI 等の外部サービスと連携し、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・研究用ファクター計算・監査ログ（発注トレース）をサポートします。

主な設計方針は「ルックアヘッドバイアスを避ける」「冪等性」「障害時のフェイルセーフ」「DuckDB を中心としたローカルデータ管理」です。

## 機能一覧

- 環境変数/設定管理（自動 .env ロード、必須チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・保存（ページネーション、リトライ、レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン（差分取得・バックフィル・品質チェック一括実行）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策、URL 正規化、トラッキングパラメータ削除）
- ニュース NLP（OpenAI による銘柄別センチメント付与、バッチ処理・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント）
- 研究用ユーティリティ（モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターン、IC、統計サマリー）
- 監査ログ（signal → order_request → execution のトレース用テーブル群、初期化ユーティリティ）
- DuckDB ベースの永続化と冪等保存ロジック

## 動作要件（概略）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス：J-Quants API、OpenAI（必要に応じて）

（プロジェクト配布に requirements.txt / pyproject.toml がある場合はそちらを使用してください）

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate
3. 依存パッケージをインストール
   - 例: pip install duckdb openai defusedxml
   - 開発用に editable インストール: pip install -e .
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須な環境変数（少なくともこれらを用意してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI を使用する機能（news_nlp / regime_detector）を使う場合に必要
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動ロード無効化
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite (monitoring 用)（デフォルト data/monitoring.db）

例 .env（参考）
OPENAI_API_KEY=sk-xxxx...
JQUANTS_REFRESH_TOKEN=jq_refresh_xxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 使い方（主要なユースケース）

以下は簡易的な Python からの利用例です。実行前に必ず環境変数をセットしてください。

- DuckDB 接続と ETL 実行（日次 ETL）
  - 目的: 市場カレンダー・株価・財務データを差分取得して保存し品質チェックを行う。

Python 例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP（銘柄ごとの AI スコアリング）
  - 目的: raw_news と news_symbols をもとに OpenAI にバッチ送信して ai_scores に書き込む。
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で解決
print("scored:", count)

- 市場レジーム判定
  - 目的: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存。
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ初期化（監査用 DuckDB の初期化）
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

- RSS ニュースの取得（ニュース収集）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# 取得した articles は NewsArticle 型（id, datetime, source, title, content, url）

注意:
- OpenAI を使う関数は OPENAI_API_KEY を環境変数に設定するか、関数引数で api_key を渡してください。
- J-Quants API へのアクセスには JQUANTS_REFRESH_TOKEN（.env）を必須とします。
- ETL や保存先は DuckDB を想定しており、settings.duckdb_path のファイルに保存されます。

## 設計/実装上のポイント（短評）

- 環境ロード:
  - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。
  - OS 環境変数 > .env.local > .env の優先順位。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を使って冪等に保存。
  - ETL の差分ロジックとバックフィルにより後出し修正を吸収。

- フェイルセーフ:
  - OpenAI / HTTP API 呼び出しはエラー時にデフォルト値（例: macro_sentiment=0.0）で継続する実装。
  - ETL は各ステップで例外を捕捉し、可能な部分は継続して処理。

- ルックアヘッドバイアス対策:
  - 日付計算は target_date を明示的に渡す設計で datetime.today() の直接参照を避ける箇所が多い。
  - ニュース・価格クエリは target_date 未満・指定ウィンドウ等でルックアヘッドを予防。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / 設定管理（.env ロード、自動設定読み込み）
- ai/
  - __init__.py
  - news_nlp.py           — ニュース NLP（OpenAI を使って銘柄別スコアを ai_scores に書込む）
  - regime_detector.py    — 市場レジーム判定（MA200 + マクロニュース LLM）
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL の公開型再エクスポート（ETLResult）
  - news_collector.py     — RSS 収集・前処理（SSRF 対策、URL 正規化）
  - quality.py            — データ品質チェック群
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py              — 監査ログスキーマ定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py    — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py— 将来リターン・IC・統計サマリー等
- (その他) strategy, execution, monitoring パッケージ等は __all__ に定義されているがここで省略

※ README に含まれるファイルリストはコードベースから抜粋した主要モジュールです。

## 開発・貢献

- コーディング規約、テスト、CI、デプロイ手順はプロジェクトの他ドキュメント（CONTRIBUTING.md, pyproject.toml 等）に従ってください（存在する場合）。
- テスト時の注意:
  - 環境変数自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OpenAI / J-Quants の外部通信部分はモックしやすいよう内部呼び出しを分離しています（ユニットテストで差し替え可能）。

## 免責事項

- 本パッケージは投資助言を行うものではありません。実運用（特に live 環境）で利用する際は十分な検証とリスク管理を行ってください。
- 外部 API の利用にはそれぞれの利用規約・料金体系に従ってください。

---

その他、具体的な実行例や追加の設定が必要であれば、用途（ETLのみ・バックテスト用データ準備・リアルタイム発注 など）を教えてください。利用シナリオに応じた手順を詳述します。