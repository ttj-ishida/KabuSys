# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のパッケージです。  
ETL（J-Quants からのデータ取得）、ニュース収集・AI によるニュースセンチメント評価、ファクター計算、監査ログ（発注〜約定トレーサビリティ）など、自動売買システムで必要な主要機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数／.env 自動読み込み（.env / .env.local、CWD 非依存）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー取得
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT 相当）
- ETL パイプライン
  - 市場カレンダー、日次株価、財務データの差分取得と保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETLResult による実行結果集約
- ニュース収集（RSS）とニュース前処理
  - URL 正規化、SSRF 防止、XML 安全パース、サイズ上限
  - raw_news / news_symbols への冪等保存想定
- ニュース NLP（OpenAI を用いたセンチメント評価）
  - 銘柄ごとのニュースをまとめて LLM に渡し ai_scores に書き込み
  - バッチ・リトライ・レスポンス検証付き
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースの LLM センチメントを合成して日次で bull/neutral/bear を判定
- 研究用ユーティリティ
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC、統計サマリー
  - Z スコア正規化（クロスセクション）
- 監査（Audit）スキーマ
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- DuckDB を中心とした軽量 DB 利用（監査用 DB の初期化関数あり）

---

## 必要な環境変数（主なもの）

必須（利用する機能に応じて必須）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API（発注等に使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意・デフォルトあり:

- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う際）

.env 読み込みについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` → `.env.local` の順で自動読み込みします。
- OS 環境変数は上書きされません（.env が override されない）。`.env.local` は override=True（ただし OS 環境変数は保護）。
- 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## セットアップ手順

1. Python 環境
   - Python 3.10+ を推奨（typing の型記載から互換性を想定）
   - 仮想環境作成（venv / pyenv / conda 等）

2. 依存パッケージのインストール（例）
   - 必要なパッケージ例（本リポジトリに requirements.txt がある場合はそれを利用してください）:
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリ外のパッケージ
   - 例:
     pip install duckdb openai defusedxml

   （パッケージの正確なリストはプロジェクトの setup / pyproject.toml / requirements.txt を参照してください）

3. パッケージのインストール（開発モード）
   - プロジェクトルートで:
     pip install -e .

4. 環境変数の設定
   - .env.example を参考に .env（および必要なら .env.local）を作成してください。
   - OpenAI を利用する場合は OPENAI_API_KEY を設定します。

---

## 使い方（簡単な例）

以下はライブラリの主要ユースケースのサンプルコードです。実行前に環境変数（JQUANTS_REFRESH_TOKEN など）を準備してください。

- DuckDB に接続して ETL を走らせる

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  # DuckDB に接続
  conn = duckdb.connect(str(settings.duckdb_path))

  # 日次 ETL を実行（target_date を指定せずに実行すると今日が対象）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 監査（audit）用 DB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # settings.duckdb_path に監査用 DB を作ることもできる（別 DB を推奨）
  conn = init_audit_db(settings.duckdb_path)
  # conn は DuckDB 接続。テーブルが作成されている
  ```

- ニュース NLP スコアを生成する（OpenAI API を利用）

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

注意:
- これらはライブラリ API を直接利用する例です。実運用ではログ、例外処理、トランザクション管理、スケジューラ（cron / Airflow 等）を組み合わせて運用してください。
- OpenAI 呼び出しや外部 API 呼び出しはレート制限・コストが発生します。ローカル実行時はテストキー・モックを用いることを推奨します。

---

## 設定と挙動のポイント

- KABUSYS_ENV（development / paper_trading / live）により実行モードを切り替えられます。settings.is_live / is_paper / is_dev で判定できます。
- LOG_LEVEL は `DEBUG/INFO/WARNING/ERROR/CRITICAL` を受け付けます。
- settings.duckdb_path / sqlite_path はデフォルトで data/ 配下を指します。必要なら環境変数で上書きしてください。
- .env の自動読み込み: プロジェクトルート（.git か pyproject.toml を基準）を自動で探し .env を読み込みます。テスト時に自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下の主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック
    - news_collector.py     — RSS ニュース収集 / 正規化 / 保存ロジック
    - audit.py              — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - ai/（上に同じ）
  - その他（execution / monitoring / strategy 等のパッケージは __all__ に含める設計）

---

## テスト・開発時のヒント

- 環境変数の自動ロードを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑止できます（ユニットテストで推奨）。
- OpenAI 呼び出しを含むユニットテスト:
  - news_nlp._call_openai_api や regime_detector._call_openai_api をモックする設計になっています。API 呼び出しの外部依存を差し替えてテストしてください。
- DuckDB のテスト用に ":memory:" を使うとインメモリ DB が利用できます（init_audit_db(":memory:") 等）。

---

## 参考 / 備考

- 各モジュールの docstring に設計方針や処理フローが詳細に記載されています。実装や拡張を行う際は docstring を参照してください。
- 実運用での「発注（kabu ステーション）」「Slack 通知」「本番口座接続」などは本リポジトリの他モジュールや外部サービスと組み合わせる前提です。live モードでは十分な安全対策（資金管理、リスク管理、テスト済みのハンドラ）を行ってください。

---

必要であれば、README に以下を追加できます：
- インストール用の pyproject.toml / requirements.txt の想定内容
- CI / テストの実行例（pytest 等）
- 実行スクリプト（CLI）やデプロイ手順のテンプレート

追加したい情報があれば教えてください。