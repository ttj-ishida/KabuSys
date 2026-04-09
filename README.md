# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI 経由）、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの差分 ETL（株価日次・財務・市場カレンダー）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価（gpt-4o-mini 想定）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- Kabusys 用の設定管理・環境変数自動ロード（.env, .env.local）

設計上の特徴として、ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）、フェイルセーフ（API 失敗時のデフォルトフォールバック）、DuckDB を使ったローカル DB 管理、冪等保存（ON CONFLICT / upsert）などを備えます。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・レート制御・保存関数）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news(conn, target_date): 銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date): ETF(1321) の MA とマクロニュースを統合して市場レジーム判定を保存
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラスでアプリ設定を環境変数から取得（.env 自動ロード対応）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型注釈を使用）
- システムに DuckDB をインストール済みならより良い（pip パッケージで十分）

例: 仮想環境を作成して依存関係を入れる

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発・配布用に pyproject.toml があれば:
     ```
     pip install -e .
     ```
     を推奨します（editable install）。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 必須例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     ```
   - よく使う環境変数（config.py を参照）
     - JQUANTS_REFRESH_TOKEN（必須）
     - OPENAI_API_KEY（AI 機能で必須）
     - KABU_API_PASSWORD（kabuステーション API 用）
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、default: data/monitoring.db）
     - PAPER_FILL_MODE（paper_trading の模擬約定挙動: instant/partial/never/reject）
     - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT など（監視関連）

---

## 使い方（簡単な例）

以下は Python REPL またはスクリプトから呼ぶ例です。DuckDB 接続は settings.duckdb_path を利用するのが推奨。

1) DuckDB 接続を開く（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略すると today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメントスコアを作成（ai_scores テーブルへ書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

4) 市場レジーム判定を実行（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト：各要素に 'code' や 'mom_1m' 等が含まれます
```

6) 監査 DB の初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル群が作成されます
```

7) ニュース RSS 収集（news_collector モジュールを使用）
- モジュール内の fetch_rss / 保存処理を組み合わせて使います。fetch_rss は URL 検証・SSRF 対策済みです。

---

## 設定（.env の例）

例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxx

# OpenAI
OPENAI_API_KEY=sk-xxxx

# kabu
KABU_API_PASSWORD=xxxx
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# KabuSys
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
PAPER_FILL_MODE=instant
```

注意:
- config.Settings はいくつかの必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を _require() で取得します。未設定時は ValueError が発生します。
- 自動ロード: .env / .env.local はプロジェクトルート（.git または pyproject.toml がある場所）から読み込まれます。テスト時などに自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発・テストのヒント

- OpenAI の呼び出しや HTTP クライアントは各モジュールで分離されており、テスト時は内部の _call_openai_api や _urlopen 等を unittest.mock.patch で差し替え可能です。
- DuckDB に対する executemany の挙動（バージョン差異）を考慮した実装があり、空のリストでの executemany を行わないよう注意しています。
- ETL は冪等設計（ON CONFLICT DO UPDATE）で実装されているため、複数回実行しても既存データは上書きまたはスキップされます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - audit.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ想定：実行監視関連)
- execution/ (パッケージ想定：発注実行関連)
- strategy/ (パッケージ想定：戦略関連)

（README 上では主要モジュールのみ抜粋しています。実際のツリーはリポジトリルートの構成に準じます。）

---

## 最後に（注意点）

- 本パッケージは実際の売買や資金移動に関わる機能を含むため、live モードでの使用は十分な検証と安全対策（テスト、監査、アクセス制御）を行ってください。
- OpenAI や J-Quants の API 使用にはそれぞれの利用規約や料金体系が適用されます。API キーの管理に注意してください。
- この README はコードベースの主要機能をまとめたものであり、詳細な API 仕様やスキーマ定義は各モジュール（ソースコード内の docstring）を参照してください。

必要であれば、この README をベースに「.env.example」や「簡易 CLI 実行例スクリプト」を作成する補助もできます。どのドキュメントを優先して追加しますか？