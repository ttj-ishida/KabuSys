# KabuSys

KabuSys は日本株の自動売買インフラ向けライブラリです。データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。バックテスト・リサーチ環境と本番運用でのデータパイプライン・監査を想定した設計になっています。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、内部で datetime.today()/date.today() を不用意に参照しない設計
- DuckDB をデータ層に利用し SQL＋Python で高速処理
- 外部 API 呼び出しに対する堅牢なリトライ・フェイルセーフ実装
- 冪等性を考慮した保存ロジック（ON CONFLICT / 冪等キー）

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価（日次 OHLCV）、財務データ、JPX カレンダーの差分取得・保存（`kabusys.data.jquants_client`, `kabusys.data.pipeline`）
  - ニュース RSS 取得と raw_news 登録（`kabusys.data.news_collector`）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）（`kabusys.data.quality`）
  - 市場カレンダーの管理（営業日判定、next/prev/trading days）（`kabusys.data.calendar_management`）

- AI（OpenAI）連携
  - ニュースを銘柄ごとにまとめて LLM に投げ、センチメントを ai_scores に保存（`kabusys.ai.news_nlp`）
  - マクロニュースと ETF（1321）の MA200 乖離から市場レジーム（bull/neutral/bear）を判定（`kabusys.ai.regime_detector`）
  - モデル呼び出しは堅牢なリトライ・タイムアウト制御あり。API 失敗時は安全側にフォールバック

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（`kabusys.research`）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化（`kabusys.research.feature_exploration`, `kabusys.data.stats`）

- 注文監査（監査ログ）
  - シグナル→発注要求→約定を UUID 階層で追跡する監査テーブル定義・初期化（`kabusys.data.audit`）
  - 監査用専用 DuckDB への初期化補助

- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（`kabusys.config`）
  - 環境切替（development / paper_trading / live）、ログレベル検証

---

## セットアップ手順

前提
- Python 3.10 以降（ソースは | 型や union を使用）
- duckdb, openai, defusedxml などの依存パッケージ
- OpenAI API キー（LLM 呼び出し用）
- J-Quants のリフレッシュトークン（データ ETL 用）
- 必要に応じて kabuステーション API パスワード、Slack トークン等

1. リポジトリをクローン / 入手し、パッケージをインストール（プロジェクトに pyproject.toml があれば editable install 推奨）
   ```
   git clone <repo>
   cd <repo>
   pip install -e .
   ```
   （pyproject.toml/setup.cfg 等がない場合は、必要なライブラリを直接インストールしてください）
   ```
   pip install duckdb openai defusedxml
   ```

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

   必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants 認証リフレッシュトークン
   - OPENAI_API_KEY          (必要: AI 機能を使う場合)
   - KABU_API_PASSWORD       (必須: kabuステーション API を使う場合)
   - KABU_API_BASE_URL       (任意: デフォルト http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN         (必須: Slack 通知を使う場合)
   - SLACK_CHANNEL_ID        (必須: Slack 通知先)
   - DUCKDB_PATH             (任意: デフォルト data/kabusys.duckdb)
   - SQLITE_PATH             (任意: デフォルト data/monitoring.db)
   - KABUSYS_ENV             (任意: development | paper_trading | live, デフォルト development)
   - LOG_LEVEL               (任意: DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト INFO)

   例 .env（プロジェクトルート）:
   ```
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=jq-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB 初期化（スキーマは ETL 実行時や audit 初期化時に作成される想定）
   - 監査データベースを手早く作るには:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 基本的な使い方（サンプル）

以下は Python スクリプト / REPL から直接利用する例です。

- 共通準備:
```python
import duckdb
from kabusys.config import settings

# DuckDB に接続（settings.duckdb_path を利用）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（内部で営業日に調整されます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（AI）で銘柄ごとのスコアを算出して保存:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を使用するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

- 監査スキーマ初期化（既存接続に対して）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- カレンダー / 取引日判定:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- リサーチ用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

recs = calc_momentum(conn, date(2026, 3, 20))
# recs は各銘柄の dict のリスト
```

注意：
- AI 呼び出し部分は OpenAI SDK（openai パッケージ）を想定しています。API 失敗時は多くの処理で安全側（0.0 など）にフォールバックします。
- ETL / 保存処理は DuckDB のテーブルスキーマに依存します。スキーマ定義はプロジェクト内のスクリプト（または別途提供される schema 初期化）で作成してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルートは src/kabusys として想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・管理（.env 自動読み込み・検証）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を銘柄ごとにまとめて OpenAI に投げ、ai_scores テーブルへ書込
    - regime_detector.py
      - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数・認証・レート制御）
    - pipeline.py
      - run_daily_etl / 個別 ETL ジョブ（prices, financials, calendar）
    - etl.py
      - ETLResult の公開エイリアス
    - news_collector.py
      - RSS フィード収集、前処理、raw_news 登録
    - calendar_management.py
      - market_calendar 管理・営業日判定・calendar_update_job
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - audit.py
      - 監査ログ用テーブル定義・初期化（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク変換
  - research/...（その他ファイル）

---

## 実運用上の注意 / トラブルシューティング

- 環境変数は必須項目（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を必ず設定してください。設定漏れは Settings のプロパティで ValueError が発生します。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は内部で制御しますが、短時間に大量リクエストを発行しない設計にしてください。
- OpenAI 呼び出しでのレスポンスパース失敗や API エラーは、多くの場合フェイルセーフでスキップされます（0.0 を使う等）。ログを確認して異常がないか定期的に監視してください。
- DuckDB バージョン差異により executemany の空リスト取り扱いが厳密に異なるため、コード側で空リストを回避するガードがあります。DuckDB のバージョンを固定しておくと想定通り動きます。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

README はここまでです。実行例や追加のセットアップ（DB スキーマ初期化スクリプトや systemd ジョブ、CI 設定など）が必要であれば、使用用途に合わせて追記できます。