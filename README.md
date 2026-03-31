# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
DuckDB を用いたデータレイク、J-Quants / RSS からの ETL、ニュースの LLM ベースセンチメント解析、研究用ファクター計算、監査ログ（発注→約定の追跡）などを提供します。

主な想定用途
- データ収集（株価・財務・マーケットカレンダー・ニュース）
- ニュースベースの銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF + マクロ記事の LLM 評価）
- 研究（ファクター計算、将来リターン、IC 等）
- 監査ログ用 DB の初期化・管理

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）
  - 必須環境変数チェック（settings オブジェクト）

- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの差分取得（株価・財務・カレンダー）
  - DuckDB への冪等保存（ON CONFLICT を使用）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、安全対策（SSRF / private host / gzip / XML Bomb 対策）
  - 記事IDは正規化 URL のハッシュで冪等化

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で記事を銘柄ごとにスコアリング
  - バッチ処理・リトライ・レスポンスバリデーション・スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロ記事の LLM センチメントを合成
  - market_regime テーブルへの冪等書き込み

- 研究用ツール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義
  - 監査 DB の初期化ユーティリティ（DuckDB）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証トークン管理（リフレッシュ）、ページネーション対応、レート制御、リトライ

---

## セットアップ手順

前提: Python 3.10+（型アノテーションに Path|None などを利用）、およびパッケージ管理環境。

1. リポジトリをクローン／取得

2. 必要パッケージをインストール
   - 最低依存（コード内 import に基づく）:
     - duckdb
     - openai
     - defusedxml
   - 例（pip）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用途や仮想環境の利用を推奨します。

3. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（パッケージ配布後も動作するよう設計）。
   - 自動ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD — kabu API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（任意）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル（任意）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

   - .env の書式は shell 風（export を許容、クォート・コメント対応）です。

4. DuckDB スキーマ／監査 DB 初期化（必要に応じて）
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 等で使用するスキーマは別途用意する想定です（本リポジトリに schema 初期化関数がある場合はそれを利用してください）。

---

## 使い方（主要 API と例）

以下は基本的な呼び出し例です。実行は適切な環境変数（特に API キー）を設定したうえで行ってください。

- settings の利用（環境変数取得）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)
  ```

- 日次 ETL を実行（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB 初期化（別 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成されます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点
- OpenAI API へのコールはレスポンスのバリデーションやリトライを行っていますが、キーが未設定だと ValueError を投げます。
- ETL / ニュース / レジーム判定は「ルックアヘッドバイアス防止」のため、内部で date.today() を不用意に参照しない設計になっています。必ず target_date を明示するか、ドメイン知識に基づいて利用してください。
- テスト時は OpenAI 呼び出しをモックしやすい設計（モジュール内の _call_openai_api をパッチ）になっています。

---

## 簡易 CLI / ジョブ化（例）

プロジェクトには CLI 実装は含まれていませんが、簡単なスクリプトで定期ジョブ化できます（cron / Airflow / GitHub Actions 等）。例:
```bash
# 日次 ETL を実行する Python スクリプト例
python - <<'PY'
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())
PY
```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの LLM スコアリング
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存ロジック
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL インターフェース再エクスポート
    - news_collector.py            — RSS ニュース収集
    - calendar_management.py       — 市場カレンダー管理（営業日判定等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py       — 将来リターン / IC / rank / summary
  - monitoring/ (該当モジュールがある場合)

各モジュールは DuckDB 接続や外部 API キーを引数化しており、テストしやすい設計になっています。

---

## テスト／開発上のメモ

- OpenAI 呼び出しは内部で _call_openai_api を通しており、ユニットテストではこの関数を patch して疑似レスポンスを返すことでテスト可能です。
- news_collector は defusedxml を利用し XML 攻撃対策をしています。RSS のフェッチ時にネットワーク・圧縮・リダイレクトの安全性チェックを行います。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、コード内で空チェックが入っています（互換性配慮）。

---

もし README に追加したい「例: systemd / cron によるジョブ設定」「詳細なスキーマ定義」「依存パッケージの固定バージョン」などがあれば教えてください。必要に応じて追記します。