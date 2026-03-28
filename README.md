# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のモジュール群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、
監査ログ（発注/約定トレーサビリティ）、市場レジーム判定などを含みます。

このリポジトリはライブラリとして Python から利用することを想定しています。
設計上のキーポイント：ルックアヘッドバイアス回避、冪等（idempotent）保存、API のレート制御・リトライ、ログ・品質チェック。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダーの取得（ページネーション対応、トークンリフレッシュ、レート制御、リトライ）。
  - ETL パイプライン（差分取得、バックフィル、品質チェック）。
- ニュース関連
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理、raw_news 保存、news_symbols との紐付け）。
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集約（銘柄ごとに ai_scores を生成）。
- AI / 市場レジーム
  - マクロニュース＋ETF（1321）200日移動平均乖離を合成した市場レジーム判定（bull/neutral/bear）。
- リサーチ（研究用）
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC 計算、Zスコア正規化、統計サマリー。
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などの検出と QualityIssue レポート。
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化ユーティリティ（DuckDB 用）。
- 設定管理
  - .env（.env.local）または環境変数からの設定読み込み（プロジェクトルート自動検出）。自動ロードは無効化可能。

---

## セットアップ手順

前提: Python 3.10+ を想定。DuckDB、OpenAI SDK などが必要です。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install -e .[dev]   （プロジェクトが setuptools/pyproject を持つ想定で editable install）
   - 必要な主な依存例:
     - duckdb
     - openai
     - defusedxml

   （ローカルに pyproject.toml / setup.cfg 等がない場合は必要なパッケージを個別に pip install してください）

3. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 (.env):
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

   注意:
   - 必須の値は実行時に Settings（kabusys.config.settings）が検証します。
   - OPENAI_API_KEY は ai モジュールの関数に引数で渡すことも可能です（引数優先、環境変数フォールバック）。

4. DB ディレクトリ作成（必要なら）
   - DUCKDB_PATH に指定したパスの親ディレクトリを作成してください（audit.init_audit_db などは親ディレクトリを自動作成しますが、用途によって手動確認を推奨）。

---

## 使い方（代表的な例）

下記はライブラリをインポートして呼び出すサンプルです。日時は date オブジェクトを使って明示的に与えることでルックアヘッドを避けます。

- DuckDB 接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```
  - J-Quants の認証トークンは settings.jquants_refresh_token により自動で取得されます（get_id_token）。

- ニュースのスコアリング（銘柄ごとの AI スコア）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で指定
  print(f"scored {written} codes")
  ```
  - API キーは引数 api_key で渡すか環境変数 OPENAI_API_KEY を使います。
  - 処理はチャンク・リトライ・レスポンス検証を行い、取得したスコアを ai_scores テーブルへ置換的に書き込みます。

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```
  - 成果は market_regime テーブルへ冪等的に書き込まれます。

- 監査ログテーブル初期化（独立 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  ```
  - init_audit_schema は UTC タイムゾーン固定や必要なインデックス作成を行います。

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)
  ```

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス防止
  - 各 AI / ETL / リサーチ関数は明示的な target_date を受け取り、内部で現在時刻を参照しない設計（バックテスト向け）。
- 冪等性
  - DB への保存は可能な限り ON CONFLICT（UPSERT）で行い、再実行に耐えるようにしています。
- レート制御・リトライ
  - J-Quants クライアントは固定間隔レートリミター（120 req/min）と指数バックオフリトライを備えています。OpenAI 呼び出しもリトライロジックがあります（429 や 5xx 対応）。
- フェイルセーフ
  - AI 呼び出し失敗時はゼロ値でフォールバック（スコア 0.0 等）し、パイプライン全体が停止しないようにしています（ただし重大な DB 書き込みエラーは例外伝播）。
- セキュリティ
  - news_collector は SSRF 対策（ホストチェック、リダイレクト検査）、XML 防御（defusedxml）、受信サイズ制限などを実装しています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル配置（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    # .env / 環境変数読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースのセンチメント集約 / score_news
    - regime_detector.py         # マーケットレジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch/save）
    - pipeline.py                # ETL パイプライン run_daily_etl 等
    - etl.py                     # ETLResult 再エクスポート
    - news_collector.py          # RSS 収集
    - calendar_management.py     # 市場カレンダー管理 / is_trading_day 等
    - quality.py                 # データ品質チェック
    - stats.py                   # zscore_normalize 等統計ユーティリティ
    - audit.py                   # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py     # calc_forward_returns / calc_ic / factor_summary / rank
  - research/（その他ファイル）
  - その他: strategy / execution / monitoring（パッケージ公開対象リストに含まれるが本コードサンプルでは一部のみ）

（実際のリポジトリにはさらにサブモジュールやユーティリティが含まれます）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に自動的に .env をロードします。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 例外でスコアが取得できない
  - モジュールは一部の失敗時にゼロフォールバックします。ログを確認して原因（認証・レート・レスポンスパースなど）を特定してください。テスト時は _call_openai_api をパッチしてモックできます。
- DuckDB にテーブルがない（ETL やチェックが失敗する）
  - 初期スキーマが必要な場合は別途 schema 初期化処理を実行するか、監査用は init_audit_db を利用してください。ETL は既定のテーブルに書き込みを行います。

---

## 開発・貢献

- コードは単体テストが容易になるよう設計されています（API 呼び出しは差し替え可能、time/datetime の直接参照を避けるなど）。
- 大型の外部依存（OpenAI, J-Quants）へはインターフェース層を設けており、モックやテスト用スタブを差し替えやすくしています。
- バグ報告、機能提案は Issue を作成してください。

---

README は以上です。必要であれば以下の追記を作成できます:
- pyproject.toml / setup.cfg のサンプル
- .env.example のテンプレート
- 各モジュールの API リファレンス（関数一覧と引数説明）
- 実行時のログ設定例（logging 設定）