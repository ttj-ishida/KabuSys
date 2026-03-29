# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（監査テーブル）などの機能を含みます。

注意: このリポジトリは取引ロジック・発注処理を含む可能性があるため、本番環境（live）で使う際は十分なテストと安全対策（ペーパートレードでの検証、運用ガードレール）を行ってください。

## 主な機能
- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等的に保存（ON CONFLICT / UPDATE）
  - ETL の品質チェック（欠損・重複・スパイク・日付不整合検出）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ削除、正規化）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング（ai.news_nlp.score_news）
  - API 呼び出しのリトライとレスポンスバリデーション
- 市場レジーム判定
  - ETF 1321（Nikkei 連動 ETF）の 200 日移動平均乖離とマクロニュースセンチメントを統合して日次の市場レジーム判定（ai.regime_detector.score_regime）
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research.*）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- 監査（Audit）
  - シグナル→発注→約定までを追跡する監査テーブルの初期化ユーティリティ（data.audit.init_audit_schema / init_audit_db）
- 環境管理
  - .env / .env.local 自動ロード（プロジェクトルートを探索）
  - Settings クラス経由で環境変数にアクセス（kabusys.config.settings）

---

## 必要要件（推奨）
- Python 3.10 以上（型注釈に `X | None` を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がない場合は下記のようにインストールしてください）
例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

kabusys は環境変数またはプロジェクトルートの `.env` / `.env.local` を参照します（自動読み込み）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings で `_require` を使っているもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 認証）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等で使用する想定）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API を使う場合は必須（news_nlp / regime_detector）

任意（デフォルトあり）
- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（default: development）
- LOG_LEVEL — ログレベル: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: `data/kabusys.duckdb`）
- SQLITE_PATH — sqlite 用パス（default: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていると無効化）

サンプル `.env.example`（プロジェクトルートに配置して利用してください）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発パッケージがあれば別途追加してください。

4. 環境変数を設定
   - 上記の `.env.example` を参考に `.env` をプロジェクトルートに作成するか、環境変数を直接設定してください。
   - 自動読み込みが有効な場合、`src/kabusys/config.py` がプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を読み込みます。

---

## 使い方 - 主要な API/操作例

以下は簡単な Python スニペット例です。実行はプロジェクトの仮想環境か、適切な依存がインストールされている環境で行ってください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う例
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を今日で実行
result = run_daily_etl(conn, target_date=None)  # target_date=None -> 今日
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
ret = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime returned:", ret)
```

- 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄のモメンタムを計算しました")
```

注意点:
- OpenAI を呼ぶ関数は API キーを環境変数 `OPENAI_API_KEY` から取得しますが、関数引数で直接 api_key を渡すことも可能です（テストやキー分けに便利）。
- ETL やニューススコアリングは外部 API を呼びます。API レート制限・コストに注意してください（J-Quants は 120 req/min、OpenAI はモデル・リクエスト単位で課金）。

---

## よくある運用 / 開発上の注意

- Look-ahead バイアス防止: 多くの関数は内部で datetime.now() / date.today() を参照しない設計になっています（target_date を明示して使うことを推奨）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。CI やテストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API 呼び出しはリトライ・レート制御を内包していますが、長時間のバルク取り込みでは API の制限・接続問題に注意してください。
- OpenAI 呼び出しはレスポンスの検証とリトライロジックを備えていますが、出力フォーマットや料金に注意してください（gpt-4o-mini を想定）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード側で空チェックを行っています。DB API の互換性に注意。

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 以下に主要モジュールが配置されています。以下は本コードベースに見える主なファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
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
    - etl.py (ETLResult 再エクスポート)
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在を __all__ に含むがコードは抜粋されていません)
  - execution/, strategy/ , monitoring/ 等（パッケージ公開対象として __all__ に含まれていますが、この抜粋に含まれないファイルもあります）

上記は機能ごとにまとまっており、data は ETL とデータ品質、news_collector、jquants_client（API クライアント）などを含みます。ai は LLM を使った NLP / レジーム判定、research はファクター計算や特徴量解析を行います。audit は監査テーブルの DDL と初期化ユーティリティを提供します。

---

## ライセンス / 責任
- この README はコードベースの説明を目的としています。実運用での用法（実際の売買・発注）については、必ず専門家のレビュー、テスト、法令遵守（金融関連の規制）を行ってください。
- 外部 API（J-Quants / OpenAI / 証券会社 API 等）を利用する部分は、当該サービスの利用規約・レート制限・コストに従ってください。

---

その他ご質問や、README に載せてほしい追加の使用例（例: CI の定義、Docker 化、監査テーブルのスキーマ説明の詳細化など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt の提案も作成します。