# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ、マーケットカレンダー管理、監視・実行補助など、自動売買システムを構成する主要な機能群をモジュール化して提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API を使った株価・財務・カレンダーの差分取得と DuckDB への永続化（ETL）
- RSS ベースのニュース収集と前処理、銘柄との紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 / マクロ）評価
- 日次 ETL パイプライン、品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル初期化
- JPX カレンダー管理（営業日判定、next/prev trading day 等）

設計上のポイント:
- ルックアヘッドバイアス回避（内部で date.today() 等を不用意に参照しない）
- DuckDB ベースでローカルに保存・解析
- API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- 冪等性（ETL 保存は ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等）を重視

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API 取得・保存（株価 / 財務 / カレンダー / 上場銘柄）
  - pipeline: 差分 ETL / 日次 ETL（run_daily_etl）
  - news_collector: RSS 収集、前処理、raw_news 保存（SSRF 対策等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダー操作・営業日判定
  - audit: 監査ログテーブル初期化（init_audit_db / init_audit_schema）
  - stats: 汎用統計（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを銘柄別に LLM で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを統合して市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 自動 .env ロード（プロジェクトルート基準）と Settings（環境変数アクセス）

---

## セットアップ手順

以下は開発マシンでのローカル実行の基本手順です。実行環境や CI に応じて調整してください。

1. Python 環境を用意
   - 推奨: Python 3.10 以降（このコードベースは型注釈等を利用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 実際の requirements.txt がある場合は:
     - pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb openai defusedxml

3. リポジトリルートに .env を作成
   - 自動でプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データディレクトリの準備（必要なら）
   - デフォルトの DuckDB 保存先 parent ディレクトリは自動作成されますが、手動で作る場合:
     - mkdir -p data

---

## 使い方（サンプル）

以下は主要な公開 API をプログラムから呼び出す例です。Python REPL またはスクリプトで利用します。

1. DuckDB コネクションを作成して ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメント（銘柄別）を評価して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定済みである前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3. 市場レジームを判定（ETF 1321 の MA とマクロニュースを利用）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 研究用ファクター計算（モメンタム/バリュー/ボラティリティ）
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

5. 監査ログ（audit）用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.duckdb")
# conn は初期化済みの DuckDB 接続
```

6. カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 1, 5)))
print(next_trading_day(conn, date(2026, 1, 5)))
```

注意点:
- OpenAI への呼び出しは API キーを要します。api_key 引数で明示的に渡すことも可能です（関数は api_key=None のとき環境変数 OPENAI_API_KEY を参照します）。
- J-Quants の id_token は jquants_client.get_id_token で内部的に取得・キャッシュされますが、必要であれば id_token を明示的に渡してページネーション時に共有できます。
- ETL / API 呼び出しはネットワークエラーや API レートに対するリトライを実装していますが、運用時はレート制御やエラーハンドリングの監視を行ってください。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (ai 機能を使う場合は必須)
- KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
- KABU_API_BASE_URL - default: http://localhost:18080/kabusapi
- DUCKDB_PATH - default: data/kabusys.duckdb
- SQLITE_PATH - default: data/monitoring.db
- LOG_LEVEL - default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を set すると .env 自動ロードを無効化
- その他（監視関連）:
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

Settings はプログラム内で以下のように使用できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## ディレクトリ構成

主要ファイルを抜粋したツリー（root: src/kabusys 以下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py (ETLResult 再エクスポート)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他リサーチ用モジュール)
    - ai/ (LLM 関連)
    - monitoring/ (監視・実行管理用モジュール - パッケージ内で公開予定)
    - (その他 strategy / execution / monitoring モジュールは __all__ に定義)

各モジュールの責務はソース内 docstring に詳細な設計・制約・処理フローが記載されています。実装を読むことで補足的な設計意図やフェイルセーフの扱いが理解できます。

---

## 運用上の注意・ベストプラクティス

- 本ライブラリは「データ取得・研究・監査」機能を中心に提供します。実際の売買執行や本番運用（live）では、十分なテスト・監視・リスク管理・二重化対策を行ってください。
- OpenAI 呼び出しはコストとレート制限に注意してください。モデル・バッチサイズはコード内の定数で調整できます（news_nlp._BATCH_SIZE 等）。
- DuckDB ファイルは定期バックアップやスキーマ管理を検討してください。
- ETL は差分更新とバックフィルを組み合わせた設計です。ETL 実行時の target_date の扱いに注意し、バックテスト時はルックアヘッドを避ける運用を徹底してください。
- セキュリティ: news_collector は SSRF 等に注意した設計ですが、RSS ソースの管理・制限は運用側で行ってください。

---

## 参考（開発者向け）

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を読み込みます。
  - .env のパースはクォーティング・エスケープ・コメントに対応しています。
- テスト時の自動 env ロード抑止:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

README は以上です。追加で含めたいサンプルスクリプトや、requirements.txt / CI 設定、デプロイ手順（systemd / コンテナ化 など）があれば、それに合わせた追記を行います。必要でしたら実行例やユニットテストの書き方、よく使う SQL スキーマ例も用意できます。