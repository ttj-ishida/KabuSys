# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュース NLU（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプラインとリサーチ・自動売買に必要な共通処理をまとめた Python パッケージです。主に次を目的としています。

- J-Quants API からの差分データ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いた ETL 保存・品質チェック
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント解析（銘柄毎スコア）
- ETF ベースの移動平均とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ作成ユーティリティ
- 環境設定管理（.env 自動読み込み等）

設計上、バックテストや運用での Look-ahead バイアスを避ける仕組みや、API 呼び出しのリトライ / フェイルセーフ動作を重視しています。

---

## 主な機能一覧

- data:
  - J-Quants クライアント（fetch/save の idempotent 実装）
  - ETL パイプライン（run_daily_etl）
  - カレンダー管理（営業日判定、更新ジョブ）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）

- ai:
  - ニュース NLP（銘柄毎のセンチメントスコアを ai_scores に書き込む: score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースで daily regime を判定: score_regime）
  - OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode を利用

- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Information Coefficient）計算
  - ファクター統計サマリ

- config:
  - .env ファイル自動読み込み（プロジェクトルート基準、.env.local が .env をオーバーライド）
  - 環境変数アクセスラッパ（settings）

---

## 必須・推奨依存パッケージ

（実際の package 配布時は requirements.txt / pyproject.toml を用意してください。ここは最低限の例）

- python >= 3.10
- duckdb
- openai
- defusedxml

インストール例:

```bash
# 開発環境向け（ソースからインストール）
git clone <repo>
cd <repo>
python -m pip install -e ".[dev]"  # もし pyproject.toml/setup.cfg がある場合

# 必要最低限パッケージを個別に入れる例
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）にある `.env`／`.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化）。

主な設定キー:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（score_news / score_regime 実行時）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を利用する場合）
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知が必要な場合
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- KABUSYS_ENV — 環境 (development / paper_trading / live)

簡単な .env 例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を用意して必要な環境変数を設定
5. DuckDB 用のデータディレクトリを作成（例: data/）

例:

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
python -m pip install duckdb openai defusedxml
mkdir -p data
# .env を作成
```

---

## 使い方（主要ユースケース）

以下は代表的な呼び出し例です。各関数は DuckDB の接続オブジェクトを引数に取る設計です。

- 設定と接続の準備

```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# 今日分を取得（target_date を指定して過去日を処理可能）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（監査スキーマ作成）

```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 既存の DuckDB 接続にスキーマを追加する
init_audit_schema(conn, transactional=True)

# 監査専用に新しい DuckDB ファイルを作る場合
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:

- score_news / score_regime は OpenAI API を使用するため `OPENAI_API_KEY` を環境変数で設定するか、api_key 引数で渡してください。設定がないと ValueError が発生します。
- J-Quants API を呼ぶ ETL は `JQUANTS_REFRESH_TOKEN` を要求します。
- ETL や保存処理は冪等（idempotent）を意識して実装されています（ON CONFLICT 等）。

---

## 実装上の設計メモ（運用者向け）

- .env 自動読み込み
  - 読み込み順: OS 環境 > .env.local > .env
  - テストで自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Look-ahead バイアス対策
  - モジュール内の関数は内部で datetime.today() を直接参照しない方針（target_date を外部から与える）。
  - prices / news の取得・評価は「対象日以前」のデータのみを参照するよう実装。

- API リトライ / フェイルセーフ
  - J-Quants クライアント、OpenAI 呼び出しはリトライロジックを備え、一定のエラー時にはフェイルセーフで中立値を返す実装（例: macro_sentiment=0.0）。
  - J-Quants は 401 を検出すると自動でトークンをリフレッシュし 1 回リトライします。

- データ品質と ETL
  - ETL 実行後に品質チェック（欠損・スパイク・重複・日付不整合）を実行可能。問題の重大度は QualityIssue オブジェクトで返却されます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / settings 管理（.env 自動ロードロジック含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・OpenAI 呼び出し、ai_scores への書込みロジック
  - regime_detector.py — ETF MA とマクロニュースで日次市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / rate limiting / retry）
  - pipeline.py — ETL のメインロジック（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー関連ユーティリティ（is_trading_day 等）
  - news_collector.py — RSS 取得と前処理、raw_news への保存ロジック
  - quality.py — データ品質チェック（QualityIssue / run_all_checks）
  - stats.py — zscore_normalize 等の汎用統計関数
  - audit.py — 監査ログ（signal/order_request/executions）スキーマ定義と初期化
  - etl.py — pipeline.ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ等の実装
  - feature_exploration.py — 将来リターン / IC / 統計サマリ 等

（上記は主要ファイルの一覧です。詳細はソースコード内の docstring を参照してください。）

---

## トラブルシューティング / 注意事項

- OpenAI のレスポンスは JSON モードを使いますが、稀に余分なテキストが混入するためパース処理は頑健化されています。パースに失敗した場合は該当チャンクをスキップし、全体処理は継続します。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、コード内で空チェックを行っています。運用時は duckdb のバージョン互換性に注意してください。
- J-Quants の API レート制限（120 req/min）を厳守するよう内部でスロットリングを行います。大量の同時処理を行う場合は設計に注意してください。
- ニュース収集では SSRF 対策（リダイレクト先の検証 / private IP ブロック / URL トラッキングパラメータ除去）を実装していますが、運用する RSS ソースは信頼できるものを設定してください。

---

## 開発貢献

バグ報告・機能追加の提案はプルリクエストまたは Issue を通してお願いします。内部設計に関する説明は各モジュールの docstring を参照してください。

---

以上。必要であれば README に以下を追記できます：
- 具体的な例テーブルスキーマ（DuckDB DDL）
- よくあるコマンド例（cron / systemd での ETL 定期実行）
- テスト・モックの方法（OpenAI / J-Quants のモック化）