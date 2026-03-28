# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買基盤向けライブラリです。J-Quants からのデータ取得・ETL、ニュースの NLP によるスコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）や市場カレンダー管理など、取引システムを構成する主要コンポーネントを提供します。

主な目的
- データ収集（株価／財務／カレンダー／ニュース）
- ETL パイプラインとデータ品質チェック
- ニュース/NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（ETF MA + マクロニュース）
- 研究用ファクター群（モメンタム／ボラティリティ／バリュー等）
- 監査ログ（シグナル→発注→約定 のトレース）

---

## 機能一覧

- data
  - J-Quants API クライアント（fetch / save 関数）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取り込み・前処理・SSRF 対策）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュースセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini 想定）呼び出しラッパー＋リトライ/フォールバック設計
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量解析・IC 計算・統計サマリー（calc_forward_returns / calc_ic / factor_summary / rank）
- audit / monitoring
  - 取引監査用テーブルの DDL／インデックス定義、初期化ユーティリティ
- 設定管理
  - 環境変数読み込み（.env / .env.local の自動読み込みをサポート）
  - settings オブジェクトで環境値を型安全に取得

---

## 必要条件（推奨）

- Python 3.10+
- 必要なパッケージ（一例）
  - duckdb
  - openai
  - defusedxml

環境に合わせて requirements.txt を用意してインストールしてください（本リポジトリに同梱されていない場合は手動で追加）。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または pip install -r requirements.txt
```

---

## 環境変数 / 設定

Settings（kabusys.config.settings）が環境変数から値を読み取ります。主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
- OPENAI_API_KEY (推奨)：OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD (必須)：kabuステーション API パスワード
- KABU_API_BASE_URL (任意)：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)：Slack 通知に使用
- DUCKDB_PATH (任意)：デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH (任意)：監視 DB パス（data/monitoring.db）
- KABUSYS_ENV (任意)：development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml の所在ディレクトリ）から .env を読み込み、さらに .env.local を上書きで読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env ファイルの例（.env.example を参照してください）:
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install -r requirements.txt   # ある場合
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（必須キーを含む）を用意するか、
   - OS 環境変数として設定します。

5. DuckDB（監査 DB 等）の格納ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API の例）

以下は簡単な使用例です。すべての関数は duckdb 接続（kabusys 内部では duckdb.DuckDBPyConnection）を受け取ります。

- DuckDB を開いて ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {count} symbols")
```

- 市場レジーム算出（ETF 1321 とマクロ記事を利用）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# schema が作成され、conn をそのまま使えます
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list[dict] -> 各銘柄ごとの mom_1m, mom_3m, mom_6m, ma200_dev 等
```

---

## 主要ディレクトリ構成（src/kabusys の概観）

- kabusys/
  - __init__.py (パッケージ定義、__version__ = "0.1.0")
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP / OpenAI を用いた銘柄センチメント算出（score_news）
    - regime_detector.py — ETF MA とマクロニュースを合成する市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limiter）
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 取得・前処理・SSRF 対策
    - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - ai, research, data 以外にも strategy / execution / monitoring 用の空インターフェースを __all__ に含める（将来的機能や別モジュールで拡張予定）

---

## 動作設計上の注意点（重要）

- Look-ahead バイアス対策:
  - 多くの関数（score_news, score_regime, ETL, ファクター計算）は内部で datetime.today() / date.today() を直接参照しない、または明示的な target_date を受け取る設計です。バックテスト等では target_date を明示して使ってください。
- OpenAI / J-Quants 呼び出し:
  - ネットワークエラー・レート制限・5xx を考慮したリトライ・フォールバックを実装していますが、実行時は API キーやレート制限に注意してください。
- DuckDB executemany の挙動:
  - 一部の関数では DuckDB のバージョン差分 (例: executemany に空リスト不可) を考慮してガードしています。
- 自動 .env 読み込み:
  - パッケージはデフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。CI やテストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## テスト / 開発

- 単体テストは本 README の対象コードベースに含まれていませんが、モジュール単位でテスト可能な形（依存注入 / API 呼び出しラッパーの差し替え）になっています。
- OpenAI 呼び出しやネットワーク IO 部分はモックしやすいように実装が分離されています（例: news_nlp._call_openai_api をパッチ可能）。

---

## 参考・追加情報

- .env.example を参考に環境変数を整備してください。
- DB スキーマ（raw_prices / raw_financials / market_calendar / ai_scores / market_regime / audit テーブル等）はコード中の DDL / INSERT ロジックを参照してください。
- 本パッケージは研究（research）と運用（data/etl / audit）双方を念頭に設計されています。運用環境（live）では SLACK 通知や発注系の安全措置を適切に組み合わせてください。

---

必要であれば、README に含める例の .env.example、requirements.txt の候補、または具体的な DB スキーマ抜粋やコマンドラインツール例（CLI）の追加を作成します。どの情報を優先して補足しますか？