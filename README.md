# KabuSys

KabuSys は日本株向けのデータプラットフォーム／研究・自動売買基盤のコアライブラリです。  
主に以下を目的に設計されています：

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- ETL パイプラインとデータ品質チェック
- ニュース収集と LLM によるニュースセンチメント評価
- ファクター計算・特徴量探索・リサーチユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）
- 市場レジーム判定（MA + マクロニュースの LLM 評価）

この README はコードベース（src/kabusys 以下）に基づく概要、セットアップ、使い方、ディレクトリ構成を記載します。

注意: パッケージには strategy / execution / monitoring 用のエントリが想定されていますが（kabusys.__all__ にそれらが含まれます）、本リポジトリで提供されている主要モジュールは data / ai / research / config などです。

## 主な機能一覧

- 環境変数／設定の自動読み込み（.env / .env.local、自動ロードは無効化可能）
- J-Quants API クライアント（認証、レート制御、リトライ、ページネーション）
- ETL パイプライン（市場カレンダー、日足、財務データの差分取得と保存）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI を使った銘柄別センチメント算出・ai_scores 書き込み）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究ユーティリティ（モメンタム／バリュー／ボラティリティ計算、forward returns、IC、統計サマリ）
- 監査ログスキーマ作成（signal_events / order_requests / executions）と監査 DB 初期化ユーティリティ
- DuckDB を第一級でサポート（永続・クエリ処理・バルク保存）

## 前提条件

- Python 3.10+
  - 型ヒント（X | Y など）と標準ライブラリ機能を利用しています
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）を利用するため、適切な API キーが必要です。

（プロジェクトで使う実際の requirements はリポジトリ側で管理してください）

## 環境変数（主なもの）

kabusys.config.Settings で参照される主要な環境変数は次の通りです。README に記載のキーは .env.example を参考に .env に置くことが推奨されます。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可能、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）ファイルパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動で .env / .env.local をプロジェクトルートから読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

## セットアップ手順（開発向け）

1. Python のインストール（推奨: 3.10 以上）
2. 仮想環境作成・有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （その他、logging/urllib などは標準ライブラリ）
4. プロジェクトルートに .env を作成 (.env.example がある場合は参照)
   - 例:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
5. DuckDB 初期化（監査ログ用 DB など）
   - Python REPL またはスクリプトで以下を実行:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # :memory: も可
6. （任意）ETL の実行権限・スケジューリングを用意（cron など）

## 基本的な使い方（コード例）

以下は代表的な利用例です。必要に応じてログ設定や例外処理を追加してください。

- DuckDB 接続の作成と ETL 実行（日次 ETL）

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア計算（OpenAI 必須）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジーム判定（MA + マクロニュース）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- J-Quants ID トークン取得 & 個別 ETL 呼び出し

  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.config import settings
  import duckdb
  from datetime import date

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  conn = duckdb.connect("data/kabusys.duckdb")
  save_count = save_daily_quotes(conn, records)
  ```

- 監査ログスキーマの初期化（監査専用 DB）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

## ETL と品質チェックの考え方（要点）

- run_daily_etl は市場カレンダー → 日足 → 財務 → 品質チェックの順で実行します（個別ジョブも呼べます）。
- 差分更新を行い、バックフィル日数（デフォルト 3 日）で後出し修正を吸収します。
- 品質チェックは Fail-Fast ではなく、検出された全問題を収集して ETLResult に格納します（呼び出し元が対処を決定）。

## ログと監視

- LOG_LEVEL 環境変数でログレベルを設定できます。
- 監視用の閾値（CPU/MEM/DISK 等）は環境変数で設定可能（Settings の cpu_threshold_pct 等）。

## ディレクトリ構成

概略（主要ファイル／モジュールのみを抜粋）:

- src/kabusys/
  - __init__.py                      - パッケージメタ情報（__version__ 等）
  - config.py                        - 環境変数／設定管理（.env 自動読み込み, Settings）
  - ai/
    - __init__.py
    - news_nlp.py                    - ニュースセンチメント算出（gpt-4o-mini 使用）
    - regime_detector.py             - マーケットレジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント（取得 / 保存 関数）
    - pipeline.py                    - ETL パイプライン（run_daily_etl 等）
    - etl.py                         - ETL インターフェイス（ETLResult 再エクスポート）
    - calendar_management.py         - マーケットカレンダー管理・営業日ユーティリティ
    - news_collector.py              - RSS 取得・正規化・raw_news への保存
    - quality.py                     - データ品質チェック（欠損、重複、スパイク 等）
    - stats.py                       - 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                       - 監査ログスキーマ & 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py         - forward returns, IC, factor_summary, rank
  - (strategy/, execution/, monitoring/ 映像上のエントリは __all__ にありますが、本リポジトリに含まれる実装に依存します)

各モジュールはドキュメント（docstring）で設計方針、入力テーブル、出力形式（多くは list[dict]）が明記されています。

## 注意事項 / ベストプラクティス

- Look-ahead bias に注意して設計されています。対象日より先のデータを参照しないよう各モジュールで配慮しています（target_date を明示的に渡す設計）。
- OpenAI API 呼び出しは外部キー（API キー）を必要とします。テスト時は内部の _call_openai_api をモックしてください（docstring に記載あり）。
- DuckDB の executemany には空リストを渡せない制約があるため、該当箇所では事前チェックが入っています。
- ニュース取得には SSRF 対策（スキーム検証・プライベートホスト検査・リダイレクト検査）や受信サイズ制限などの防御機構があります。
- J-Quants API はレート制限（120 req/min）に従う実装になっています（固定間隔スロットリング）。

## 貢献 / 拡張

- strategy / execution / monitoring 層を実装して注文フローやブローカー連携を追加できます（監査テーブルはその前提で設計されています）。
- OpenAI のモデルやプロンプトは実運用に合わせて調整可能です（news_nlp / regime_detector の SYSTEM_PROMPT）。
- ETL のスケジューリングや監視は外部ツール（Airflow, cron, systemd など）で運用してください。

---

不明点や README に追記してほしい内容があれば教えてください。必要であれば各モジュールの API 使用例（より詳細なコードスニペット）も追加します。