# KabuSys

日本株向けのデータプラットフォームと自動売買 / リサーチユーティリティ群をまとめたパッケクトライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなど、バックテスト／運用に必要な基盤的処理を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・JPXマーケットカレンダーを差分取得（ページネーション対応・レートリミット対応・トークン自動リフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを一括実行

- データ品質チェック
  - 欠損（OHLC 欠落）、スパイク検出（前日比閾値）、主キー重複、日付整合性チェックを実行し QualityIssue を返却

- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、記事IDはSHA-256で冪等化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（news_nlp.score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターの統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を定義する監査スキーマ初期化と専用 DuckDB 初期化関数
  - 発注フローの UUID 連鎖によるトレース設計

- 設定 / 環境管理
  - .env（および .env.local）自動ロード（プロジェクトルート検出）と Settings オブジェクト経由の型付きアクセス
  - 自動ロード無効フラグ：KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要要件

- 推奨 Python バージョン: 3.10+
  - PEP 604 の型表記（A | B）などを使用しているため 3.10 以上を想定しています
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布に requirements.txt / pyproject.toml がある場合はそれに従ってください）

インストール例（仮に pip でインストールする場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用にパッケージをプロジェクトとしてインストールする場合（パッケージ設定があると仮定）
# pip install -e .
```

---

## 環境変数 (.env)

ルートにある `.env` および `.env.local` が自動で読み込まれます（OS 環境変数が優先、.env.local は .env を上書き）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用する環境変数（Settings で参照されるキー）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- kabu（発注）関連
  - KABU_API_PASSWORD : kabu API パスワード（必須）
  - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- Slack 通知
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベースパス
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- 監視 / PID
  - PID_FILE_PATH : 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- リソース閾値（監視）
  - CPU_THRESHOLD_PCT（例: 90.0）
  - MEMORY_THRESHOLD_PCT（例: 85.0）
  - DISK_THRESHOLD_PCT（例: 90.0）
- 実行環境 / ログ
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OpenAI
  - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime は引数で渡すことも可能）

注意: Settings は未設定の必須キーを参照すると ValueError を投げます。README には .env.example を参考に .env を作成するようメッセージが出ます。

---

## セットアップ手順（開発者向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成とパッケージインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # requirements.txt があれば
   # または必要パッケージを個別に
   pip install duckdb openai defusedxml
   ```

3. 環境変数の準備
   - ルートに `.env`（および任意で `.env.local`）を作成
   - `.env.example` がある場合はそれを参考にしてください
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（NLP を使う場合）

4. データベースディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API と例）

※ 例はいずれも Python スクリプト / REPL から実行できます。DuckDB 接続には duckdb.connect(settings.duckdb_path) を利用すると便利です。

- Settings の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログテーブル初期化（既存 DB に追加） / 監査 DB を新規作成
```python
import duckdb
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存 conn に対して
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn)

# 監査専用 DB を作る場合
audit_conn = init_audit_db("data/audit.duckdb")
```

- ファクター計算・リサーチユーティリティの使用例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
normalized = zscore_normalize(m, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## ランタイム / 運用に関する注意事項

- Look-ahead バイアス対策
  - 多くのモジュールが内部で date.today() や datetime.now() を無条件に参照しない設計（関数引数で target_date を渡す）になっています。バックテストや再現性のため、target_date を明示的に渡すことを推奨します。

- OpenAI 呼び出し
  - news_nlp/regime_detector は gpt-4o-mini を使用する想定で JSON Mode を利用します。API のレスポンス不正や API エラー時にはフェイルセーフ（スコアを 0 にフォールバック、例外を上位に伝えない設計）がありますが、API キーの管理とコストに注意してください。

- J-Quants API
  - レート制限（120 req/min）や 401 自動リフレッシュ、指数バックオフが組み込まれています。認証トークン（refresh token）は安全に保管してください。

- News collector（RSS）
  - SSRF 対策、レスポンスサイズ制限、XML パースの安全化（defusedxml）などの対策を入れていますが、外部ソースの扱いには注意してください。

---

## ディレクトリ構成（主要ファイルと役割）

（パッケージのルートが `src/kabusys` の想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py        - ニュースセンチメントの LLM スコアリング
    - regime_detector.py - マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  - J-Quants API クライアント（fetch / save）
    - pipeline.py        - ETL パイプライン(run_daily_etl 等)
    - etl.py             - ETLResult の公開ラッパ
    - calendar_management.py - マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py  - RSS 収集と前処理
    - quality.py         - データ品質チェック（missing / spike / duplicates / date_consistency）
    - stats.py           - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py           - 監査ログ（監査スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py - momentum / volatility / value の計算
    - feature_exploration.py - forward returns / IC / factor summary / rank
  - monitoring/ (パッケージとして __all__ に含まれる想定)
  - execution/  (注文実行周りの補助モジュール等、実装の有無に依存)
  - strategy/   (戦略定義層、シグナル生成など)

---

## テスト / 開発

- モジュールは外部 API 呼び出し箇所を内部関数レベルでモックしやすい設計になっています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え可能）。
- DuckDB を用いたテストは in-memory モード（":memory:"）で容易に行えます（audit.init_audit_db の引数に ":memory:" を指定可能）。

---

## 貢献 / 変更履歴

- 現在の README はコードベースから抽出した概要ドキュメントです。新機能追加や API 変更を行う際は README と settings のドキュメントを合わせて更新してください。

---

問題や追加したい利用例があれば教えてください。Example のスクリプトや .env.example のテンプレート作成などもお手伝いできます。