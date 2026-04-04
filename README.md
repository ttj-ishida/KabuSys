# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、監査ログ（発注〜約定トレーサビリティ）などを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要API例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の研究・自動売買基盤のためのライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- DuckDB を用いた時系列・ファクター計算（モメンタム、ボラティリティ、バリュー等）
- RSS ニュース収集と OpenAI による銘柄別ニュースセンチメント (ai_scores) の算出
- マクロニュースを含めた市場レジーム判定（bull / neutral / bear）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針:
- ルックアヘッドバイアスを避ける（date 引数ベース、datetime.today()/date.today() の直接参照回避）
- API 呼び出しはリトライ/バックオフ・フェイルセーフ設計
- DuckDB を主ストレージに想定（監査用DBは専用ファイルに分けられる）

---

## 主な機能（機能一覧）

- data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得・前処理・保存）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース軸の NLP スコアリング（score_news：銘柄別 ai_score を ai_scores テーブルへ）
  - 市場レジーム判定（score_regime：ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出ベース）
  - settings オブジェクトで設定値取得

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージのインストール（開発時）
   - 本リポジトリをプロジェクトとしてクローンした後、ルートでインストール:
   ```bash
   pip install -e .
   ```
   - 依存ライブラリ（代表例）:
     - duckdb
     - openai
     - defusedxml
     - これらは setup.py / pyproject に記載の想定です。必要な場合は個別に pip で追加してください:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の用意
   - プロジェクトルートに `.env`（と任意で `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB ファイルの準備
   - デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`（settings.duckdb_path）。
   - 監査ログ専用 DB を別で作ることも可能（init_audit_db で初期化）。

注意:
- .env の自動パースは quotes / コメント / export 前置に対応します。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと外部環境に依存せずに実行できます。

---

## 環境変数

主に以下の環境変数が参照されます（settings オブジェクト経由）:

必須（実行する機能により必須となるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp / regime_detector）を使う場合に必要
- KABU_API_PASSWORD: kabuステーション API を利用する場合

任意 / デフォルトあり
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知連携用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視・プロセス管理設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要API例）

以下は代表的な利用例です。関数はルックアヘッドバイアスを防ぐため date 引数を受け取り、内部で現在時刻を参照しない設計です。

- ETL（日次）を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を省略すると今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの銘柄別スコアを作る（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に api_key を渡すことも可能（None なら環境変数 OPENAI_API_KEY を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジームスコアを計算して保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成されます
```

- ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
```

- データ品質チェックを実行する
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI とのやり取りは retry/backoff を内包していますが、APIキーの制限やコストに注意してください。
- J-Quants API の呼び出しはレート制限を守る設計になっています。`JQUANTS_REFRESH_TOKEN` の設定が必要です。

---

## ディレクトリ構成

主要モジュールと役割（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースの LLM による銘柄別スコア生成（score_news）
    - regime_detector.py : ETF とマクロニュースを組み合わせた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py            : ETL パイプライン（run_daily_etl 他）
    - etl.py                 : ETLResult 再エクスポート
    - calendar_management.py : 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py      : RSS 収集・前処理・保存
    - quality.py             : データ品質チェック
    - stats.py               : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     : モメンタム / ボラティリティ / バリューの計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー 等
  - research/ その他: feature exploration 等

各モジュールは docstring で仕様・設計方針・処理フローを記載してあり、関数ドキュメントに引数・戻り値・副作用（DB 参照テーブル等）が明記されています。

---

## 開発・運用上の注意点

- Look-ahead バイアス対策のため、バックテストで使用する場合は DB に投入するデータのタイムラインに注意してください（取得時刻/fetched_at を含む）。
- OpenAI / J-Quants の API キーは安全に管理してください。ログ等に直接出力しないでください。
- DuckDB のテーブルスキーマは ETL と保存関数の前提に基づきます。初回セットアップ時は schema 作成スクリプトまたは既存スキーマの適用が必要です。
- ニュース収集は外部 RSS をダウンロードするため SSRF 対策やレスポンス制限（MAX_RESPONSE_BYTES）を設けていますが、運用時はソースリストの管理を行ってください。

---

必要に応じて README に追記します。例えば:
- 初期スキーマ作成スクリプト（raw_prices/raw_financials/raw_news 等）
- サービス（監視 / systemd）用の実行例
- よくあるトラブルシューティング（OpenAI レスポンスが JSON でない場合の対処等）

補足してほしい箇所があれば教えてください。