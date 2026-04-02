# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL、ニュース収集とAIによるニュースセンチメント評価、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

## 概要
KabuSys は以下の機能を組み合わせて、日本株レイヤーのデータ取得・品質管理・リサーチ・監査・AI 評価までを扱える内部ライブラリです。

主な設計方針:
- Look-ahead bias を避ける（内部で date.today() を不用意に使わない設計）
- DuckDB を用いたローカルデータ格納・分析
- J-Quants API を用いた差分 ETL（レート制限、リトライ、トークンリフレッシュ対応）
- OpenAI（gpt-4o-mini）によるニュースセンチメント・マクロ判定（JSON Mode + フォールバック）
- 冪等性（ON CONFLICT / idempotent 保存）と監査ログ（発注〜約定までのトレーサビリティ）

## 機能一覧
- 環境変数 / .env 読み込み・管理（自動ロード / 無効化オプション）
- J-Quants API クライアント（株価・財務・上場情報・市場カレンダーの取得）
- ETL パイプライン（run_daily_etl をエントリポイントとして株価/財務/カレンダーを差分更新）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS 取得、SSRF 対策、記事正規化、raw_news / news_symbols への保存ロジックを前提）
- AI ニュース NLP（銘柄ごとニュースを集約して OpenAI でスコア化）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成してレジームを決定）
- 研究用ユーティリティ（モメンタム・バリュー・ボラティリティ等のファクター計算、forward returns、IC、統計サマリ）
- 監査ログスキーマ（signal_events / order_requests / executions の DDL と初期化ユーティリティ）
- DuckDB を用いたデータ保存ユーティリティ（冪等性を考慮）

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型注釈 (A | B) を使用）
- Git（プロジェクトルート検出 .git または pyproject.toml に依存）

1. 仮想環境を作成・有効化
   - venv の例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 必要最低限（代表）:
     pip install duckdb openai defusedxml
   - 開発パッケージやテストフレームワークはプロジェクトの要件に応じて追加してください。

3. パッケージをインストール（開発モード）
   - プロジェクトルート（pyproject.toml 等があるディレクトリ）で:
     pip install -e .

4. 環境変数 / .env 設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の主な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（ETL）
- KABU_API_PASSWORD: kabuステーション API のパスワード（注文実行等）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視通知等）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
（その他は config.Settings でデフォルト値が設定されているかオプションです）

主要な設定キー（Settings から参照）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト data/monitoring.db）
- PID_FILE_PATH（実行プロセス監視用）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

## 使い方（例）

以下は簡単な Python スクリプト例です。DuckDB 接続を取得して ETL を実行したり、AIスコアを生成したりする流れを示します。

1) 日次 ETL 実行（run_daily_etl）
- ETL は DuckDB 接続を受け取り、差分取得→保存→品質チェックを実行します。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースの AI スコアリング（news_nlp）
- OpenAI API キーを環境変数に設定してから呼び出します。戻り値は書き込み件数。

例:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)

3) 市場レジーム判定（regime_detector）
- ETF 1321 の MA200 とマクロセンチメントを合成して market_regime テーブルへ書き込みます。

例:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログスキーマ初期化
- 監査用 DB を作り、テーブルを初期化するユーティリティがあります。

例（同一 DB に追加する場合）:
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

例（監査専用 DB を初期化して接続を取得）:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

5) RSS ニュース収集（news_collector）
- fetch_rss を用いて RSS を取得し、DB 保存処理（raw_news への保存）はプロジェクト側で実装される想定です。
- fetch_rss は SSRF対策 / GZIP 対応 / サイズチェックを行います。

注意事項
- OpenAI 呼び出しは外部 API に依存するため、API エラー時はフォールバック（0.0）となる設計です。テスト時は _call_openai_api をモックしてください。
- ETL / API 呼び出しはログとエラー処理が組み込まれています。実稼働時はログ設定と監視を整備してください。

## .env の自動読み込み
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、 .env → .env.local の順で自動読み込みを行います。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 読み込みの挙動: OS 環境変数 > .env.local > .env（.env.local は上書き、ただし OS 環境変数のキーは保護）

.env の記述例（抜粋）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py
  - Settings: 各種環境変数を取得するユーティリティ
- ai/
  - __init__.py
  - news_nlp.py         : ニュースのセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector.py  : ETF + マクロセンチメントで市場レジームを判定
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（取得/保存機能）
  - pipeline.py         : ETL パイプラインのエントリポイント（run_daily_etl 等）
  - etl.py              : ETLResult の公開
  - news_collector.py   : RSS 取得・正規化・記事ID生成等
  - calendar_management.py : 市場カレンダー管理（営業日判定・更新ジョブ）
  - quality.py          : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py            : zscore_normalize 等の統計ユーティリティ
  - audit.py            : 監査ログ（DDL / 初期化ユーティリティ）
- research/
  - __init__.py
  - factor_research.py  : モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration.py : forward returns, IC, factor summary, rank

（未記載の補助モジュールが他にも存在する可能性があります）

## 開発とテスト
- 外部 API（OpenAI / J-Quants / RSS）呼び出し部分はモック化して単体テストを作成してください。
- news_nlp / regime_detector の _call_openai_api はテスト時に差し替えられるよう設計されています（unittest.mock.patch などで置換）。

## 注意点・運用上のヒント
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コードでは空チェックを行っています。
- J-Quants のレート制限（120 req/min）に対して固定間隔スロットリングを実装済みです。
- OpenAI へのリクエストは JSON Mode を利用し、厳密な JSON レスポンスを期待する仕様です。パースに失敗した場合はフォールバックして処理を継続します。
- 監査ログは削除しない運用を想定しています（FK は ON DELETE RESTRICT）。

---

問題や追加で README に入れたい内容（例: 実行用 CLI、CI 設定、追加の依存パッケージ一覧）があれば教えてください。README に追記します。