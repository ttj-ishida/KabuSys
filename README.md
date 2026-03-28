# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / RSS / OpenAI 等を利用してデータを収集・品質検査・特徴量生成・AIスコアリングを行い、監査ログ／ETL／リサーチ処理を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する（ETL）
- ニュース収集（RSS）と LLM（OpenAI）を用いたニュースセンチメントの銘柄スコア化
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量探索（forward returns, IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の特徴：

- ルックアヘッドバイアスに注意（内部で date.today() を無差別に参照しない、ETL/スコア生成は target_date を明示）
- DuckDB を主要な永続層として使用
- OpenAI は JSON Mode を用いる想定で堅牢なパース・リトライ処理を実装
- J-Quants API 呼び出しはレート制限とリトライを備える
- 冪等（idempotent）な保存ロジック（ON CONFLICT / DELETE → INSERT など）

---

## 機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- データ品質管理
  - run_all_checks（kabusys.data.quality）: 欠損・重複・スパイク・日付不整合検出
- ニュース処理
  - RSS 収集（kabusys.data.news_collector）
  - ニュース NLP（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - kabusys.ai.regime_detector.score_regime
- 監査ログ / トレーサビリティ
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- リサーチ / ファクター計算
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- 設定読み込み
  - 環境変数 / .env 自動ローディング（kabusys.config）

---

## 必要条件（推奨）

- Python 3.10+
- 依存ライブラリ（代表）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（pyproject.toml / requirements.txt があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは個別に: pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（少なくとも開発で必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（利用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（利用する場合）
     - KABU_API_PASSWORD — kabu API パスワード（kabu ステーションとの連携がある場合）
     - OPENAI_API_KEY — OpenAI 呼び出しを行う場合に必要（score_news / score_regime 等）
   - 任意（デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - LOG_LEVEL (default: INFO)

   例 .env（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化（監査ログ等）
   - 監査ログ用 DB を初期化する:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   -（別途）プロジェクトが必要とするテーブルスキーマを作成する初期化スクリプトを用意して実行してください（本リポジトリ内に schema 初期化ユーティリティがあればそちらを利用）。

---

## 使い方

以下は代表的な利用例です。実行は Python スクリプトやジョブランナーから行います。

- 日次 ETL 実行（DuckDB 接続を渡す例）
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの生成（score_news）
```py
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```py
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn を使って監査テーブルへ書込みが可能
```

- ファクター計算 / リサーチ例
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点:
- OpenAI 呼び出しはコストとレート制限があるため、テスト時はモック (_call_openai_api を patch) して実行することを推奨します。モジュール内でテスト用に差し替えやすい設計になっています。
- run_daily_etl 等は外部 API の失敗を内部でハンドルしつつエラー情報を ETLResult に格納します。運用上は result.has_errors / result.has_quality_errors を確認してください。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリングに必要）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- KABU_API_PASSWORD — kabu API 接続で必要な場合

オプション（デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

設定は .env / .env.local から自動読込されます（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。

---

## テスト & 開発時のヒント

- OpenAI / J-Quants 呼び出しはリトライ・フェイルセーフ設計ですが、ユニットテストでは外部呼び出しをモックしてください（各モジュールに _call_openai_api 等の差し替えポイントがあります）。
- .env 読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テストで環境を汚さないため）。
- DuckDB はインメモリ接続(":memory:") をサポートするため、テスト時はファイルを作らずに使用できます。

---

## ディレクトリ構成

（主要ソースのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  - 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py              - ニュース NPL（score_news）
    - regime_detector.py       - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API client / 保存ロジック
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   - 市場カレンダー管理
    - news_collector.py        - RSS 収集
    - quality.py               - データ品質チェック
    - stats.py                 - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 - 監査ログスキーマ初期化
    - etl.py                   - ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算
    - feature_exploration.py   - 将来リターン / IC / 統計サマリー
  - (execution, monitoring, etc.)  - 実運用・モニタリング層（公開 API に含まれる想定）

---

## 運用上の注意

- 実際に売買を行うパイプライン（execution）は本 README の示す範囲外であり、実際の注文送信は重大なリスクを伴います。live 環境での運用時は十分な検証・ログ・監査を行ってください。
- OpenAI API キーは機密情報です。ログやパラメータに露出しないよう取り扱ってください。
- J-Quants API のレート制限を尊重してください（本クライアントは 120 req/min を想定した RateLimiter を組み込んでいます）。

---

## ライセンス / 貢献

- （ここにライセンス情報を記載してください）
- バグ報告・機能提案は Issue でお願いします。

---

README に記載した使い方・環境変数はソース中の docstring / コメントと整合するように作成しています。追加でサンプルスクリプトやスキーマ初期化スクリプトを README に付けたい場合は指示してください。