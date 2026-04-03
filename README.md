# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ管理など、バックテスト／運用で必要となる主要機能を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の取得とバリデーション

- Data（データ・ETL）
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
    - レートリミット対応、リトライ、トークン自動リフレッシュ
  - ETL パイプライン（差分取得／保存／品質チェック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS -> raw_news、SSRF 対策、前処理）
  - 監査ログテーブル初期化 / 監査 DB ユーティリティ（シグナル→注文→約定のトレーサビリティ）

- AI（OpenAI）
  - ニュースセンチメント: raw_news を銘柄ごとにまとめて LLM へ投げ、ai_scores に保存
  - レジーム判定: ETF(1321) の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
  - OpenAI 呼び出しはリトライやフォールバック実装済み

- Research（研究用ユーティリティ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - 汎用 zscore 正規化ユーティリティ

---

## 必須要件 / 依存（概略）

- Python >= 3.10（| 記法や型注釈を使用）
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリを多用する設計のため、追加依存は限定的です。実際の requirements.txt があればそちらを利用してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウトして作業ディレクトリへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを使ってください）
   また、パッケージを編集しながら開発するなら：
   - pip install -e .

4. 環境変数を用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を配置すると、自動で読み込まれます。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）

必須（機能利用時に必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL, jquants_client）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携をする場合）
- OPENAI_API_KEY : OpenAI を使う機能（news_nlp / regime_detector）を使う場合

推奨／任意:
- KABUSYS_ENV : one of `development`, `paper_trading`, `live`（デフォルト `development`）
- LOG_LEVEL : `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : 監視用 SQLite のパスなど
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視関連のオプション

.env の例（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な利用例）

注意: 各例は最低限のサンプルです。実際にはロギング設定や例外処理、APIキー管理等を適切に行ってください。

- DuckDB 接続を作って ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（ai_scores への書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を None にすると環境変数 OPENAI_API_KEY が使われる
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（market_regime への書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルに対する操作やクエリが可能
```

- 研究用：ファクターや統計ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
# conn は duckdb 接続、target_date は date オブジェクト
records = calc_momentum(conn, target_date)
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 自動 .env 読み込みについて

- 実装はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。
- 読み込み順序は OS 環境変数 > .env.local > .env（.env.local は上書き）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト時や CI で有用）。

---

## ディレクトリ構成（主要ファイル・モジュール）

（ソースは `src/kabusys` 以下に配置されています）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py : 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（fetch/save）
    - pipeline.py        : ETL パイプライン（run_daily_etl など）
    - etl.py             : ETLResult の公開
    - stats.py           : 統計ユーティリティ（zscore_normalize）
    - quality.py         : データ品質チェック（欠損・スパイク等）
    - calendar_management.py : 市場カレンダー管理（営業日判定等）
    - news_collector.py  : RSS ニュース収集（SSRF 対策・前処理）
    - audit.py           : 監査ログ（DDL・初期化関数）
  - research/
    - __init__.py
    - factor_research.py : ファクター計算（momentum/volatility/value）
    - feature_exploration.py : 将来リターン、IC、統計サマリー
  - monitoring/ (パッケージ配下に示唆されているがここでは省略)
  - execution/, strategy/ など（上位モジュールとの連携を想定）

この README は主要な公開 API とワークフローの概要を示しています。各関数やクラスはソース内にドキュメント（docstring）が豊富にありますので、詳細は該当モジュールの docstring を参照してください。

---

## 開発時の注意点 / ベストプラクティス

- Look-ahead バイアス回避設計に配慮されています：
  - 各処理は target_date を明示的に受け取り、内部で date.today() を使わないことが多いです。バックテスト用途でも target_date を明示的に与えること。
- DuckDB に対する executemany の空リスト扱い（バージョン依存）に注意。既に実装側で考慮されていますが、運用中の DB バージョン確認は推奨。
- OpenAI / J-Quants API 呼び出しはリトライ・フォールバック実装があるため、失敗しても致命的でない場合はログを確認して継続する設計になっています。

---

必要に応じて README を拡張（設定ファイル例の追加、CI / デプロイ手順、具体的な SQL スキーマ文の抜粋など）できます。追加してほしい項目があれば教えてください。