# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ実装（参考実装）。  
本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP / LLM を用いた銘柄・市場センチメント評価、監査ログ（発注→約定トレーサビリティ）などを含みます。

## プロジェクト概要
KabuSys は以下の機能を持つモジュール群から構成される Python ライブラリです。

- J-Quants API からの差分取得／保存（株価・財務・上場情報・マーケットカレンダー）
- DuckDB を利用したデータ格納および ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニューステキストの前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（銘柄別 ai_scores、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 × LLM マクロセンチメント）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、前方リターン、IC、Zスコア正規化 等）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- 冪等性（DB への保存は ON CONFLICT を利用）
- フェイルセーフ（API 失敗時の適切なフォールバック、部分失敗の許容）
- 外部サービス呼び出し部分にリトライ＆バックオフ実装

---

## 主な機能一覧
- data.jquants_client: J-Quants API 呼び出し（fetch / save）・認証トークン管理・レートリミット
- data.pipeline: 日次 ETL （run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
- data.news_collector: RSS 取得・正規化・raw_news 保存補助
- data.calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
- data.audit: 監査ログのスキーマ作成・監査DB初期化（init_audit_schema / init_audit_db）
- ai.news_nlp: 銘柄別ニュースセンチメント算出（score_news）
- ai.regime_detector: 市場レジーム判定（score_regime）
- research: ファクター計算（momentum, value, volatility）と解析ユーティリティ
- config: .env 自動読み込み、環境変数ラッパー（settings オブジェクト）

---

## セットアップ手順

前提:
- Python 3.9+（タイプヒントで | を使用しているため 3.10 以降を推奨する場合があります）
- ネットワーク接続（J-Quants / OpenAI 等）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .\.venv\Scripts\activate
3. 依存パッケージをインストール
   例（必要なパッケージを最低限列挙）:
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）
4. 環境変数の設定
   - プロジェクトルートの .env または OS 環境変数で設定します。
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に使用）
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: データ保存先 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, ...（実行監視用）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   簡易的な .env.example:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な API/コマンド例）

※ 以下は Python REPL やスクリプトからの利用例です。適宜 import 文やモジュール接続を行ってください。

- DuckDB に接続して ETL を実行（日次 ETL）
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（銘柄別）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数で用意
print("scored:", n_written)
```

- 市場レジーム判定（ETF 1321 を使う）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DuckDB を初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

- J-Quants ID トークンを明示的に取得
```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照
```

注意点:
- OpenAI 呼び出しは cost が発生します。テスト時は API 呼び出し部分をモックすることを推奨します（モジュール内の _call_openai_api をパッチ可能）。
- ETL・API 呼び出しは長時間走ることがあるためログ出力とリトライ挙動に注意してください。
- DuckDB の executemany に空リストを渡すとエラーになる箇所があるため、空チェックが組み込まれています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py           # 銘柄別ニュースセンチメント算出（score_news）
      - regime_detector.py    # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（fetch / save / auth / rate limit）
      - pipeline.py          # ETL パイプライン（run_daily_etl 等）
      - etl.py               # ETLResult の公開（再エクスポート）
      - news_collector.py    # RSS 収集・前処理
      - calendar_management.py # JPX カレンダー管理（営業日判定等）
      - quality.py           # データ品質チェック
      - stats.py             # 共通統計ユーティリティ（zscore_normalize）
      - audit.py             # 監査ログスキーマ / 初期化
    - research/
      - __init__.py
      - factor_research.py   # momentum/value/volatility の計算
      - feature_exploration.py # forward returns / IC / factor_summary / rank

---

## 開発・テストのヒント
- API 呼び出し（OpenAI, J-Quants, RSS）部分はモックしやすいように内部呼び出しを切り出しています。ユニットテスト時は該当関数を patch して副作用を制御してください。
- 環境変数自動読み込みはパッケージがインポートされるタイミングで行われます。テストで環境を制御する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化してください。
- DuckDB を利用した処理は SQL を多用しており、デバッグは conn.execute(...) の結果を直接参照するのが便利です。
- LLM を使う処理（news_nlp, regime_detector）はレスポンス形式の検証やリトライロジックを実装済みですが、実運用時はプロンプトやモデル選択、バッチサイズのチューニングが必要です。

---

## ライセンス・注意事項
- 本実装はリファレンス実装です。商用利用・実運用の前には十分なレビュー・テストを行ってください。
- OpenAI / J-Quants など外部サービスの利用にはそれぞれの利用規約、レート制限、料金体系を確認してください。

---

ご要望があれば、README にコマンドライン実行例（CLI スクリプト）や .env.example の完全テンプレート、サンプル SQL スキーマ（DuckDB 初期化用）などを追記します。