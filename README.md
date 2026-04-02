# KabuSys

日本株向けのデータ・研究・自動売買プラットフォームのライブラリ群です。ETL（J-Quants からのデータ取得 / DuckDB への保存）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（発注・約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ ETL
  - J-Quants API から株価（日次 OHLCV）、財務指標、JPX カレンダーを差分取得して DuckDB に冪等保存
  - 差分取得 / バックフィル機能、ページネーション対応、レート制御・リトライ実装
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア化（ai_scores テーブル）
  - ニュースウィンドウの厳密定義（Look-ahead バイアス防止）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュース（LLM によるセンチメント）を合成して日次レジーム（bull/neutral/bear）を判定
  - API フェイルセーフや再試行ロジックを備える
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク（急変）、将来日付/非営業日データの検査
  - QualityIssue データ構造で詳細を返す
- 監査ログ（Audit）
  - signal → order_request → execution の階層でトレース可能な監査テーブル群
  - DuckDB に監査スキーマを冪等初期化するユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（プロジェクトルート検出：.git または pyproject.toml）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化

---

## 必要条件

- Python 3.10 以上（型アノテーションに | 演算子を使用）
- 依存パッケージ（例）
  - duckdb
  - openai （OpenAI Python SDK）
  - defusedxml
  - （標準ライブラリのみで動作するモジュールも多く含む）
- J-Quants / OpenAI / Slack の API キー（用途に応じて）

※ 実行環境により追加のパッケージが必要になる場合があります。プロジェクトの pyproject.toml / requirements.txt があればそちらを参照してください。

---

## インストール（開発環境）

1. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -e .   （プロジェクトに setuptools/poetry 等の設定がある想定）
   - 主要依存の個別インストール例:
     - pip install duckdb openai defusedxml

---

## 環境変数（.env の例）

config.Settings が参照する主な環境変数（最低限必要なもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能利用時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース / レジーム判定で使用）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（省略時: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

自動ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）から `.env` → `.env.local` の順に自動ロードします。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な .env 例（README 用: 実際の値は秘匿してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（初期 DB 作成等）

1. DuckDB ファイルの準備
   - settings.duckdb_path を確認または .env に設定
   - パスの親ディレクトリは自動で作成されるユーティリティがあるモジュール（例: init_audit_db）が存在します

2. 監査ログスキーマ初期化（例）
   - Python REPL やスクリプトで:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可
     # init_audit_db は transactional=True 相当でスキーマを作成します
     ```
   - あるいは既存の DuckDB 接続に対して:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=False)
     ```

3. ETL 初期実行（データの初回ロード）
   - run_daily_etl を使って日次 ETL を実行:
     ```python
     from kabusys.data.pipeline import run_daily_etl
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
     print(result.to_dict())
     ```

注意: J-Quants の初回取得には JQUANTS_REFRESH_TOKEN が必要です。

---

## 使い方（主要 API の例）

以下はライブラリを直接インポートして利用する基本例です。CLI は用意されていないため、スクリプト化して実行するか REPL から呼び出してください。

- DuckDB 接続取得:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 今日の日付を対象に ETL を実行
  ```

- ニュース NLP スコア付与（ai_scores への書き込み）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 19))
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 19))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  date0 = date(2026, 3, 19)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

- ニュース収集（RSS）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  # 得られた articles を raw_news テーブルへ保存するロジックは別実装（jq.save 等）
  ```

- カレンダー判定ユーティリティ:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date
  d = date(2026, 3, 19)
  is_trade = is_trading_day(conn, d)
  next_d = next_trading_day(conn, d)
  days = get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))
  ```

注意点（挙動・設計上のポイント）:
- 多くの関数は内部で datetime.today() / date.today() を直接参照しない設計（Look-ahead バイアス対策）。必ず target_date を明示するか、パイプラインのデフォルト挙動を理解してください。
- OpenAI 呼び出しはリトライやフェイルセーフを備えますが、API キー未設定時は ValueError が発生します。
- ETL / 保存処理は可能な限り冪等（ON CONFLICT）で実装されています。

---

## ディレクトリ構成

主要モジュールとファイルの概観（省略形）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン / run_daily_etl 等
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS 収集
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
    - etl.py                  — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 計算
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary 等
  - ai、data、research 以下に細かい実装が多数存在します。

---

## 運用上の注意・ベストプラクティス

- 認証情報は必ず安全に管理し、リポジトリにコミットしないでください（.env を .gitignore に入れるなど）。
- バックテストや再現性のある研究を行う場合、データの取得日時（fetched_at）と Look-ahead バイアスに注意してください。
- DuckDB ファイルは定期バックアップを推奨します（ストレージ障害対策）。
- 本ライブラリは発注/実売買に関わる機能を含む想定があります。live 環境で実行する際は KABUSYS_ENV を `live` に設定し、十分なテストと監査を行ってください。
- 自動ロードされる .env の扱い: テスト実行時などでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑止できます。

---

## 参考（実装上の設計思想）

- Look-ahead bias を避けるため、多くの処理は「target_date を外部から与える」形で実装されています。
- API 呼び出しはリトライ（指数バックオフ）、レート制御（J-Quants）、および 401 のトークンリフレッシュ対応を備えています。
- DuckDB 側はできる限り冪等な保存（ON CONFLICT）を行い、ETL は部分失敗を許容して残りを継続します（Fail-Fast ではない）。
- ニュース収集は SSRF 等の攻撃に対する防御を含みます（リダイレクト検査、プライベートアドレス遮断、受信サイズ制限など）。

---

必要であれば、この README をベースに具体的な CLI スクリプト例やユニットテストのサンプル、docker-compose や systemd ユニットの起動例なども追加できます。どの部分を詳しく補足しましょうか？