# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ファクター計算、ニュースNLP（OpenAI）や市場レジーム検出、監査ログ（約定トレーサビリティ）など、一連の処理をモジュール化して提供します。

---

## 主要な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダーの取得・ページネーション対応
  - レート制御・リトライ・トークン自動リフレッシュを備えた堅牢なHTTPクライアント
- ETLパイプライン
  - 日次差分ETL（市場カレンダー → 株価 → 財務）
  - バックフィル、品質チェック統合、結果集約（ETLResult）
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付整合性・非営業日検出
- ニュース処理（News Collector & NLP）
  - RSS 収集（SSRF対策、トラッキングパラメータ除去、サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア（ai_scores への書き込み）
- 市場レジーム判定
  - ETF(1321)のMA乖離とマクロニュースセンチメントを組み合わせて日次で 'bull' / 'neutral' / 'bear' を判定
- 研究用ユーティリティ
  - ファクター計算（Momentum, Value, Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - シグナル→発注要求→約定までの完全トレース可能な監査テーブル定義および初期化ユーティリティ

---

## 必要要件

- Python 3.10 以上（typing の `X | Y` 表現を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

推奨: 仮想環境（venv / pipenv / poetry 等）でインストールしてください。

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを編集インストールする場合:
# pip install -e .
```

---

## 環境変数と設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（デフォルト）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注連携の際）
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（オプション）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視等用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START : 実行監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV            : 実行環境 (development / paper_trading / live)。無効な値は例外
- LOG_LEVEL              : ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)

設定は `kabusys.config.settings` 経由で参照できます。

使用例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

.project ルートの検出方法:
- `.git` または `pyproject.toml` を基準に親ディレクトリを探索します。見つからない場合、自動 `.env` ロードはスキップされます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成して依存をインストール
2. プロジェクトルートに `.env`（もしくは `.env.local`）を作成し必要な環境変数を設定
   - 最低限: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（NLP を使う場合）
3. DuckDB データベースディレクトリを作成（settings.duckdb_path の親ディレクトリ）
4. 必要に応じて監査DBを初期化

例（.env の最低例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

基本的にモジュールをインポートして関数を直接呼び出します。以下に代表的な利用例を示します。

- DuckDB に接続して日次ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- J-Quants から株価を取得する（直接利用）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

- OpenAI を用いたニューススコアリング（銘柄別）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込み件数:", n_written)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査DB（order/audit）を初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用 DuckDB 接続
```

テストや CI では、OpenAI などの外部呼び出しはモックしやすいよう設計されています（例: news_nlp._call_openai_api のパッチ）。

---

## 主要なモジュールとディレクトリ構成

以下はソースツリーの主要ファイル・モジュール（抜粋）です。パッケージは `src/kabusys` に配置されています。

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースのNLPスコアリング（OpenAI）
    - regime_detector.py         -- 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                -- ETL パイプライン（run_daily_etl など）
    - etl.py                     -- ETL の公開インターフェース（ETLResult 等）
    - news_collector.py          -- RSS 取得／記事前処理（SSRF対策等）
    - calendar_management.py     -- 市場カレンダー管理 / 営業日判定 / 更新ジョブ
    - quality.py                 -- データ品質チェック（欠損・重複・スパイク等）
    - stats.py                   -- 統計ユーティリティ（Zスコア）
    - audit.py                   -- 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         -- Momentum / Value / Volatility 等の計算
    - feature_exploration.py     -- 将来リターン / IC / 統計サマリ 等

各モジュールは DuckDB 接続や API キー（環境変数）を受け取り、ルックアヘッドバイアスの回避や冪等性を考慮して実装されています。

---

## 開発・テストに関する注意点

- 外部API呼び出し（OpenAI、J-Quants、HTTP）はリトライとフォールバック処理を備えていますが、テストではモックしてください。
  - 例: unittest.mock.patch で news_nlp._call_openai_api や jquants_client._request を差し替え可能
- .env 自動ロードは `.git` か `pyproject.toml` をプロジェクトルートとして探索します。テストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の `executemany` はバージョン差異による制約があるため、コード内で空パラメータのチェック等が行われています。DuckDB のバージョン互換性を確認してください。

---

## ライセンス・貢献

（ここにライセンスや貢献方法を記載してください。リポジトリに LICENSE ファイルがあればその内容を反映してください。）

---

README に掲載してほしいサンプルや、CI 手順、Dockerfile、または特定機能の詳細な使用例（発注連携、LINE 通知等）があればお知らせください。README を拡張して追加します。