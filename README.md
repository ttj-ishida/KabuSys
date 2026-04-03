# KabuSys

KabuSys は日本株向けのデータ基盤と自動売買（研究・実行）を支援する Python ライブラリです。  
ETL、データ品質チェック、ニュース収集・NLP（LLM）によるセンチメント評価、ファクター計算、監査ログなどを備え、DuckDB を中心としたワークフローで設計されています。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、JPXマーケットカレンダーを差分取得
  - 差分保存（冪等性: ON CONFLICT DO UPDATE）
  - 日次パイプライン（run_daily_etl）と個別 ETL ジョブ
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
- ニュース収集 & 前処理
  - RSS 収集（SSRF対策、トラッキングパラメータ除去、前処理）
- ニュース NLP（OpenAI）
  - 銘柄別センチメントを LLM（gpt-4o-mini）で評価して ai_scores に保存（score_news）
  - マクロニュースと ETF 1321 の MA乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal → order_request → executions までトレーサビリティを担保する監査スキーマと初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API

---

## 必須（推奨）依存関係

- Python 3.10+（PEP 604 の union 型などを利用）
- duckdb
- openai
- defusedxml

（プロジェクトでの利用に合わせて追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な主要環境変数（例）:

.env.example の例:
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API（必要に応じて）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LINE通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# データベース / ファイルパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# 実行環境・ログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（抜粋）

以下は主要ユーティリティの簡単な利用例です。実運用ではログ設定や例外ハンドリングを追加してください。

- DuckDB 接続を作成して ETL を実行する（run_daily_etl）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み件数:", n_written)
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査専用DBを作る）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb 接続
```

- ファクター計算（例: モメンタム）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
```

- news_collector で RSS を取得して保存するには、fetch_rss を呼んで raw_news テーブルへの保存ロジックを組み合わせてください（保存関数はプロジェクト固有に実装してください）。

注意:
- OpenAI の呼び出し関数群は api_key を引数で注入できる設計です（テストやキーを切り替えるときに便利）。
- LLM 呼び出しは失敗に寛容に設計されており、API 失敗時はフェイルセーフ値を使って継続します。

---

## 設定管理

- settings オブジェクト: `from kabusys.config import settings` でアクセスできます。
  - 主なプロパティ:
    - settings.jquants_refresh_token (必須)
    - settings.kabu_api_password
    - settings.kabu_api_base_url
    - settings.line_channel_access_token
    - settings.line_user_id
    - settings.duckdb_path (Path)
    - settings.sqlite_path (Path)
    - settings.pid_file_path / kill_flag_path
    - settings.env (development | paper_trading | live)
    - settings.log_level

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS環境変数 > .env.local > .env
  - テストや特殊用途で自動ロードを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの一覧です（抜粋）。

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
    - etl.py
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (その他: pipeline に関連する ETLResult 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは data.stats を利用してファクター計算や探索的解析を提供します。

パッケージの __all__ では "data", "strategy", "execution", "monitoring" が公開対象になっていますが、このリポジトリ内では data と research / ai が主に実装されています。strategy / execution / monitoring 層は上位設計（実運用との接続）としてのエントリポイントや将来実装を想定しています。

---

## 注意事項 / ベストプラクティス

- Look-ahead bias（ルックアヘッドバイアス）回避: 多くの関数は date を明示で受け取り、内部で datetime.today() を使用しない設計になっています。バックテストでは必ず過去時点の情報のみを使うようにしてください。
- LLM 呼び出し: レスポンスのパースや API エラーに対して多重のフォールバックを実装していますが、API 利用時のコスト・レート制限に注意してください。
- DuckDB の executemany はバージョン差異で挙動が異なる場合があるため、空リストの渡し方など注意して実装されています（既存コードを参照してください）。
- セキュリティ:
  - news_collector は SSRF 対策（ホスト検査、リダイレクト検査）や XML の安全処理を組み込んでいます。
  - 外部 API の認証情報は .env に保管し、リポジトリに含めないでください。

---

## 貢献 / 拡張案

- strategy / execution 層の具現化（kabuステーション等への接続、注文処理）
- モジュール単位の CLI / ワーカー化（ETL スケジューラ統合）
- 単体テスト・統合テストの整備（モック注入を前提とした設計になっています）
- メトリクス / モニタリングの強化（Prometheus 等）

---

README に含めてほしい追加情報や、特定の使い方（例: kabuステーション連携、LINE通知の実装）などがあれば教えてください。必要に応じてサンプルスクリプトや CLI 例も作成します。