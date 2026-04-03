# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。J-Quants や RSS、OpenAI 等を利用してデータ取得・品質チェック・ニュース NLP・市場レジーム判定・ファクター研究・監査ログ管理を行うモジュール群を提供します。

主な想定用途:
- 日次 ETL（株価・財務・市場カレンダー）パイプライン
- ニュース収集と LLM を用いた銘柄センチメント算出
- 市場レジーム判定（ETF + マクロニュースのハイブリッド）
- ファクター計算 / 研究用ユーティリティ（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- J-Quants API クライアント（取得・保存・リトライ・レート制御）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須変数チェック付き Settings クラス（kabusys.config.settings）
- データ ETL / Data Platform
  - J-Quants からの差分取得 & DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去（kabusys.data.news_collector）
  - raw_news / news_symbols 連携で冪等保存
- AI（OpenAI）連携
  - 銘柄単位ニュースセンチメント算出（score_news）
  - マクロ + ETF(1321) による市場レジーム判定（score_regime）
  - 再試行・JSON mode 利用・レスポンス検証等の安全対策
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算・IC（情報係数）・統計サマリ・Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義 & 初期化ユーティリティ
  - init_audit_db / init_audit_schema による冪等初期化
- J-Quants クライアント
  - fetch/save のラッパー（レート制御、リトライ、401 自動リフレッシュ）
  - listed info / daily quotes / financial statements / market calendar の取得・保存

---

## セットアップ手順

前提:
- Python 3.10+ 推奨
- DuckDB を利用（pip 経由でインストールされます）
- OpenAI API キー（news & regime の LLM 呼び出しに使用）
- J-Quants のリフレッシュトークン

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール:
   - プロジェクトに requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - ない場合、少なくとも以下をインストールしてください:
     ```bash
     pip install duckdb openai defusedxml
     ```
   （実際の利用機能に応じて追加パッケージが必要になる可能性があります）

4. データディレクトリを作成:
   ```bash
   mkdir -p data
   ```

5. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 例（.env.example）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI
     OPENAI_API_KEY=sk-...

     # kabu API
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # LINE通知（任意）
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=

     # DB / ファイルパス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag

     # 動作環境 / ログ
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 利用可能な環境変数は `kabusys.config.Settings` のプロパティを参照してください。

---

## 使い方（簡単な例）

以下はライブラリ API を直接利用する最小例です。実運用ではエラーハンドリングやロギング設定を適切に行ってください。

1. DuckDB 接続を開く（ファイル DB を使用）:
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）:
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定することも可能
   print(result.to_dict())
   ```

3. ニュースセンチメント算出（OpenAI API キーが必要）:
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   count = score_news(conn, target_date=date(2026, 3, 20))
   print("scored:", count)
   ```

4. 市場レジーム判定（ETF1321 + マクロニュース、OpenAI API キー必要）:
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. ファクター計算 / 研究:
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
   from datetime import date
   m = calc_momentum(conn, date(2026, 3, 20))
   v = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

6. 監査ログ DB 初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   ```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数で直接キーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 関連は JQUANTS_REFRESH_TOKEN を設定しておく必要があります。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須で ETL を使う場合）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- KABU_API_BASE_URL: kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             # ニュースセンチメント算出（LLM）
    - regime_detector.py      # 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - quality.py              # 品質チェック
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - news_collector.py       # RSS ニュース収集（SSRF 対策等）
    - calendar_management.py  # 市場カレンダー管理 / 営業日判定
    - audit.py                # 監査ログスキーマ / 初期化
    - etl.py                  # ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py      # モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py  # 将来リターン / IC / 統計・ランク関数
  - ai/、research/、data/ 以下にさらに補助関数とユーティリティ群が含まれます。

（実際のファイル一覧はリポジトリを参照してください）

---

## 運用上の注意 / 設計方針（要約）

- Look-ahead バイアス対策:
  - 各アルゴリズムは target_date を明示的に受け取り、datetime.today()/date.today() の直接参照を避ける設計になっています。
  - DB クエリは target_date より前のデータのみを使用する等、バックテストに向いた安全な実装です。
- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を使い冪等的に保存します。
  - ニュース記事 ID は正規化 URL のハッシュで生成し重複挿入を防ぎます。
  - 監査ログの order_request_id / broker_execution_id 等は冪等キーとして設計されています。
- API 呼び出し:
  - J-Quants は固定間隔スロットリングとリトライ、401 自動リフレッシュ対応。
  - OpenAI 呼び出しは JSON mode を想定し、429/ネットワーク/5xx に対して指数バックオフで再試行します。失敗時は安全側にフォールバック（例えば macro_sentiment=0.0）します。
- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト検査 / プライベート IP ブロック）や XML パーサの安全実装（defusedxml）を行っています。
  - .env の読み込みは OS 環境変数を保護する仕組みがあります。

---

## 貢献 / 開発メモ

- テスト: 各 API 呼び出しは差し替え可能（内部の _call_openai_api などをモックできるよう設計）。
- ロギング: ロガー名はモジュール名（例: kabusys.ai.regime_detector）を使用しているため、ロギング設定で個別制御が容易です。
- 拡張:
  - 新しいニュースソース追加、LLM モデルの切替、kabu ステーション連携などを想定して拡張可能です。

---

質問や具体的な利用例（ETL スケジュール、OpenAI のコスト/バッチ戦略、DuckDB スキーマ初期化など）について必要であれば、実行例や詳細手順を追加で作成します。