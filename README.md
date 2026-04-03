# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ／発注トレーサビリティなど、量的投資・自動売買システム構築に必要な基盤機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・品質チェック機能を備えた日次 ETL パイプライン
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
- ニュース収集 / 前処理
  - RSS フィード取得、安全対策（SSRF ブロック、受信サイズ制限）、正規化、raw_news への冪等保存に対応
- AI（OpenAI）
  - ニュース単位のセンチメントスコア算出（銘柄別 ai_scores へ保存）
  - マクロセンチメントと ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
  - OpenAI の JSON Mode を用いた堅牢なレスポンスパースとリトライ処理
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ、Z スコア正規化
- 監査（Audit）
  - signal → order_request → execution まで追跡可能な監査テーブル定義・初期化機能（DuckDB）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、環境変数アクセスをラップする Settings クラス

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部表記と duckdb 等を想定）
- 外部依存: duckdb, openai, defusedxml （最小限。環境に応じて追加）

1. リポジトリを取得 / インストール
   - 開発中: 開発環境に editable install
     - pip install -e .
   - 必要パッケージ（一例）
     - pip install duckdb openai defusedxml

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。
   - 必須の環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
     - OPENAI_API_KEY : OpenAI 呼び出しを行う場合は必須（score_news / score_regime）
   - 任意・デフォルト値
     - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知に使用する場合
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベースディレクトリ作成
   - デフォルトの DB パス（例: data/）がない場合は作成してください。多くの初期化関数は親ディレクトリを自動作成しますが、環境によっては権限等の問題が発生するため確認を推奨します。

---

## 使い方（基本例）

以下はライブラリの代表的な使い方の例です。実行前に必要な環境変数（上記）を設定してください。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Settings から参照可能
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定するか api_key 引数で渡す
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"written: {written}")
```

- 市場レジーム（bull/neutral/bear）をスコアリング・保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ（audit）データベースの初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して監査テーブルが作成される
```

- 設定値の参照（Settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- AI を用いる機能（score_news / score_regime）は OpenAI API キーが必要です。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL・保存処理は DuckDB 接続を受け取ります。テストでは ":memory:" 接続を使うこともできます。
- OpenAI への呼び出しはリトライ・フェイルセーフを備えていますが、ネットワークや API 制限により結果が取得できない場合はスコアを 0.0 にフォールバックするなどの保守的な挙動があります。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

パッケージ: src/kabusys/

- __init__.py
  - パッケージのバージョンと主なサブパッケージ公開

- config.py
  - Settings クラス: 環境変数のラップ、.env 自動読み込み、必須変数チェック

- ai/
  - __init__.py (score_news の公開)
  - news_nlp.py
    - ニュースの集約・OpenAI 呼び出し・レスポンス検証・ai_scores への書き込み
    - calc_news_window(), score_news(), 内部でバッチ・リトライ管理
  - regime_detector.py
    - ETF（1321）200日 MA 乖離 + マクロニュース LLM センチメントを合成して market_regime に書き込む
    - score_regime()

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント: 認証（refresh）、fetch/save 関数、レート制限、リトライ
  - pipeline.py
    - 日次 ETL 実行（run_daily_etl）と個別ジョブ（run_prices_etl 等）、ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS フィード取得、前処理、SSRF 対策、raw_news 保存ロジック
  - calendar_management.py
    - market_calendar の取得／営業日判定・next/prev/get_trading_days、calendar_update_job
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）
  - audit.py
    - 監査ログテーブル定義、初期化（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily, raw_financials を参照）
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリ、ランク関数

---

## 実運用・注意事項

- 環境（KABUSYS_ENV）が "live" の場合は実際の発注や本番向けの挙動に注意してください（本コードベースは実際の発注モジュールを含める設計がある場合、さらに外部 API 連携や権限管理が必要になります）。
- OpenAI 呼び出しは外部 API 利用のためコスト・レート制限があります。試験運用は paper_trading 環境で行ってください。
- J-Quants API の利用には有効なトークンが必要です。get_id_token() は自動リフレッシュとエラーハンドリングを行いますが、API 制限に注意してください。
- DuckDB を用いた SQL 実行は、パフォーマンス観点でデータ量に応じたチューニング・インデックス作成が必要になる場合があります（audit モジュールではインデックスを定義済み）。

---

## 開発／テスト向けメモ

- .env の自動読み込みはプロジェクトルートを __file__ の親ディレクトリから探索して .git または pyproject.toml を基準に行います。これにより CWD に依存せずに設定を読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数で指定してください。
- AI 呼び出し箇所はテストでモックしやすいように内部呼び出し関数（_call_openai_api 等）を分離しています。unittest.mock.patch による差し替えを推奨します。

---

ご不明点や README に追記したい利用例（例: バックテストでの使い方、監視ジョブのデプロイ手順など）があれば教えてください。必要に応じてセクションを拡張します。