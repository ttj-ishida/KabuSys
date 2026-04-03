# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants）→ データ品質チェック → 研究用ファクター計算 → ニュースNLP / 市場レジーム判定 → 監査ログ（発注/約定トレーサビリティ）までの主要機能を含みます。

---

## 特徴（概要）

- J-Quants API から株価・財務・マーケットカレンダーを差分取得し DuckDB に保存する ETL パイプライン
- ニュース記事の収集／前処理／銘柄紐付け（RSS）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング（銘柄単位）とマクロセンチメント評価による市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）のスキーマ定義と初期化ユーティリティ
- 設定は .env / 環境変数で管理（プロジェクトルートを自動検出して .env を読み込み）

設計上の留意点：
- ルックアヘッドバイアス防止（target_date を外部から明示、内部で date.today() を避ける）
- 冪等性（DB への保存は ON CONFLICT で上書き）
- API 呼び出しはリトライ／バックオフとレート制御を備える
- 外部リソースアクセスに対する安全対策（RSS の SSRF 検査等）

---

## 機能一覧

- data
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（取得 + DuckDB 保存）
  - カレンダー管理 / 営業日判定 / calendar_update_job
  - ニュース収集（RSS）と前処理
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC 計算 / 統計サマリー
- ai
  - ニュースセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime）
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）と各種設定アクセス（settings）

---

## セットアップ手順

前提
- Python 3.10 以上（構文で | 型ヒントを使用）
- DuckDB を利用（ローカルファイルに保存）

1. リポジトリをクローン
   - 例: git clone <repo-url> && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がない場合の最低依存例:
     - pip install duckdb openai defusedxml
   - 開発中は editable install:
     - pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（代表的な）環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携する場合）
- その他（任意・デフォルトあり）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - LOG_LEVEL（DEBUG/INFO/...）、KABUSYS_ENV（development/paper_trading/live）

.env の読み込み優先順位:
- OS 環境変数 > .env.local > .env

---

## 使い方（例）

以下は簡単な Python スニペット例です。適切に環境変数を設定してから実行してください。

- ETL を日次で実行する（DuckDB 接続を渡す）
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（指定日分）をスコアリングして ai_scores テーブルへ保存
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定を実行（ETF 1321 の MA とマクロニュースを合成）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリが無ければ自動作成
```

- データ品質チェックを実行
```
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注:
- OpenAI 呼び出し関数は api_key を引数で上書きできます（テストや複数キー運用時に便利）。
- ETL や AI 処理は外部 API に依存しているため、実行環境でネットワークアクセス可能か確認してください。

---

## 設定詳細（まとめ）

主要な settings プロパティ（kabusys.config.Settings）:
- jquants_refresh_token: J-Quants のリフレッシュトークン（必須）
- kabu_api_password: kabu API パスワード（発注連携時）
- kabu_api_base_url: kabu API のベース URL
- line_channel_access_token, line_user_id: LINE 通知設定
- duckdb_path: DuckDB のデータファイルパス（Path オブジェクト）
- sqlite_path: 監視用 SQLite パス
- PID / KILL フラグ / リソース閾値（監視用）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル

.env パースは細かいケース（export プレフィックス、クォート、行内コメント）に対応しています。

---

## ディレクトリ構成（主要ファイル）

（抜粋、重要モジュール中心）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメントスコアリング
    - regime_detector.py           — マクロセンチメント＋MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py                  — ETL パイプライン & run_daily_etl
    - etl.py                       — ETLResult の公開
    - calendar_management.py       — 市場カレンダー管理、営業日判定、calendar_update_job
    - news_collector.py            — RSS 収集・前処理・保存
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - research/*

この README にないユーティリティやモジュールは src/kabusys 以下を参照してください。

---

## 運用上の注意・設計メモ

- Look-ahead バイアスに注意：AI / ファクター計算 / ETL は target_date を外部から与える設計です（内部で無条件に現在時刻を参照しない）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- J-Quants API 呼び出しは内部的に固定間隔レートリミッタと再試行ロジックを備えています。401 はトークン自動リフレッシュを試みます。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの検証・フォールバック（0.0）を行います。API 失敗時でも処理を中断せず継続する設計の箇所が多いです（フェイルセーフ）。
- RSS 収集は SSRF 対策・受信サイズ制限・XML 脆弱性対策を実施しています。

---

## 追加情報 / 開発

- テストコード / CI 設定が無ければ、ユニットテストは各モジュールの公開関数をモックして実行してください（例: news_nlp._call_openai_api のモック）。
- データベーススキーマ（raw_prices / market_calendar 等）は ETL / audit モジュールと整合性を保ってください。
- 変更を加える際は、look-ahead バイアスと冪等性（ON CONFLICT）を意識してください。

---

必要に応じて README の実例コマンド（requirements.txt の内容、推奨構成、デプロイ手順など）を追加できます。どの情報をより詳しく書くか指定してください。