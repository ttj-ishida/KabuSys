# KabuSys

日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算・リサーチユーティリティ、監査ログ（オーダー→約定のトレーサビリティ）、および市場レジーム判定などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主要目的とする Python モジュール群です。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄毎・マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算、特徴量探索、IC 計算等のリサーチユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査（signal → order_request → execution の追跡）用テーブル生成・初期化

設計上の特徴:
- ルックアヘッドバイアス回避（内部処理で datetime.today() の無秩序参照を避ける）
- DuckDB を主なローカルデータストアとして使用
- OpenAI 呼び出しは JSON モード + 再試行を含む堅牢な実装
- J-Quants API はレートリミット遵守とトークン自動リフレッシュ対応

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（fetch_* / save_*）
- データ品質
  - check_missing_data / check_duplicates / check_spike / check_date_consistency
  - run_all_checks
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存（設計に基づく）
- ニュース NLP（OpenAI）
  - score_news: 銘柄別センチメントを ai_scores テーブルに書き込み
  - JSON モード + バッチ処理 + リトライ
- 市場レジーム判定
  - score_regime: ETF（1321）の MA200 乖離とマクロセンチメントを合成
- 研究／ファクター
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- 監査（audit）
  - init_audit_schema / init_audit_db: signal_events / order_requests / executions テーブルの初期化

---

## 必須環境・依存ライブラリ

- Python >= 3.10（型ヒントで | を使用しているため）
- 必要なパッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

プロジェクトの実行に必要なパッケージはプロジェクトで管理されているはずです（requirements.txt / pyproject.toml を参照してください）。ない場合は下記のようにインストールできます:

python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml

（パッケージの正確なセットアップはプロジェクトの pyproject.toml/requirements.txt に従ってください）

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化可能）。

必須（アプリケーションで参照される代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知（Bot）用トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に参照）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1）

.env の読み込み挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。
- `.env.local` は既存 OS 環境変数を上書きできますが、既存の OS 環境は保護されます。
- コメント・クォート・export KEY=val 形式などに対応したパーサを内蔵しています。

---

## セットアップ手順（開発／ローカル実行向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .\.venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -e .
   - または個別に: pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記の必須変数を設定してください。
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=CXXXXX

5. DuckDB データベースファイルの準備（デフォルトは data/kabusys.duckdb）
   - データ格納ディレクトリを作成: mkdir -p data
   - 初期スキーマや監査用 DB を作る場合は下記を参照

---

## 使い方（代表的な API 実行例）

以下は Python REPL やスクリプト内での利用例です。

- DuckDB 接続を作成して ETL を実行する（例: 当日の ETL）
  - import duckdb
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- news_nlp（ニュースセンチメント）を実行する
  - from kabusys.ai.news_nlp import score_news
  - import duckdb
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026,3,20))
  - print("書き込んだ銘柄数:", n_written)

- 市場レジーム（MA200 とマクロセンチメントの合成）を評価する
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20))

- 監査ログスキーマを初期化する（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn をそのまま運用で利用できます

- jquants_client を直接利用してデータを取得する
  - from kabusys.data.jquants_client import fetch_daily_quotes
  - data = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,19))

注意点:
- OpenAI を用いる処理（score_news, score_regime）は API キー（OPENAI_API_KEY）を必要とします。関数の api_key 引数で直接渡すこともできます。
- J-Quants API 呼び出しはリクエストレート制限（120 req/min）を守る実装になっています。
- DuckDB の executemany に空リストを渡すと互換性の問題が生じる箇所があるため、内部で保護ロジックがあります。呼び出し側は通常意識する必要はありません。

---

## ディレクトリ構成（主要ファイルと説明）

（ソースは src/kabusys 以下に配置）

- src/kabusys/__init__.py
  - パッケージのメタデータ（__version__）およびサブパッケージ公開

- src/kabusys/config.py
  - 環境変数 / .env ロードと Settings クラス（J-Quants, kabu API, Slack, DB パス 等）

- src/kabusys/ai/
  - news_nlp.py: ニュースの集約・OpenAI での銘柄別スコアリング（score_news）
  - regime_detector.py: MA200 とマクロセンチメントを合成して市場レジーム判定（score_regime）
  - __init__.py: score_news の再エクスポート

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（fetch / save / auth / rate limiting）
  - pipeline.py: ETL パイプラインのメイン（run_daily_etl など）と ETLResult
  - etl.py: ETLResult の公開（再エクスポート）
  - news_collector.py: RSS 取得・正規化・raw_news 保存ロジック（SSRF 対策、gzip 上限等）
  - calendar_management.py: JPX カレンダー管理、営業日判定・next/prev/get_trading_days、calendar_update_job
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: zscore_normalize 等の汎用統計ユーティリティ
  - audit.py: 監査ログ用テーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
  - __init__.py: 主要関数のエクスポート

（その他）
- monitoring, strategy, execution 等のサブパッケージは __all__ に含まれていますが、ここに示したソース一覧は本リポジトリ内に存在する主要モジュールに基づいています。

---

## 運用上の注意・ベストプラクティス

- ローカル実行やバックテストの際は Look-ahead バイアスに注意してください。score_news / score_regime 等は内部で「対象日の前日データのみを使用する」等の措置が取られていますが、外部から不適切に未来データを与えないでください。
- OpenAI 呼び出しは API 利用料が発生します。バッチサイズ・チャンク数に注意してください（news_nlp は最大 20 銘柄チャンクなど制御あり）。
- J-Quants API を頻繁にコールする場面では rate limit（120 req/min）を意識してください。jquants_client にレート制御がありますが、高頻度実行時は十分に注意してください。
- 本番（live）環境では KABUSYS_ENV を `live` に設定し、ログ・監視設定や発注フローの安全性を確保してください（発注機能は別モジュールで実装されている場合があります）。

---

## さらに詳しく / 参照

- 各モジュール内の docstring に設計方針・詳細処理フローが記載されています。実装の挙動やリトライ条件、クリッピングルールなどはソースコードのコメントを参照してください。
- .env.example や pyproject.toml / requirements.txt（プロジェクト内にある場合）を参照して環境を整えてください。

---

もし README に追加してほしい項目（発注フローの使い方、Slack 通知設定例、より詳細な ETL 実行手順など）があれば教えてください。必要に応じてサンプルスクリプトやデプロイ手順も追加します。