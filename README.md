# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集、LLM を用いたニュースセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレース）など、運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場情報、JPX カレンダー）
  - 差分取得・バックフィル・冪等保存（DuckDB へ ON CONFLICT で保存）
  - 日次 ETL の統合エントリーポイント（run_daily_etl）
- ニュース処理
  - RSS からのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- 自然言語処理（LLM）
  - ニュースを銘柄ごとに統合し LLM でセンチメント算出（score_news）
  - マクロニュース + ETF（1321）200日MA乖離を組み合わせた市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を想定し、JSON Mode を用いた厳格パース・リトライを実装
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、Z スコア正規化など
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（quality モジュール）
  - 品質チェックを集約して返す run_all_checks
- カレンダー管理
  - JPX カレンダーの保存・営業日判定・next/prev_trading_day 等
- 監査ログ（Audit）
  - signal_events / order_requests / executions を中心に監査スキーマ初期化と監査 DB の作成補助
  - init_audit_db で監査専用の DuckDB を初期化
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定は Settings 経由で取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

---

## セットアップ手順（開発 / 実行）

前提
- Python 3.10 以上（ソースで | 型ヒントを使用）
- DuckDB をローカルで使用（組み込みモジュールとして Python パッケージ duckdb を使用）

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトがパッケージ化されていれば）pip install -e .

   ※ 実行環境に応じて他の依存が必要になる場合があります。logging 等は標準ライブラリで動作します。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` や `.env.local` を置くと自動で読み込まれます（環境変数が優先されます）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxx
   - OPENAI_API_KEY=sk-xxxx
   - KABU_API_PASSWORD=xxxx
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=xoxb-xxxx
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト / REPL での利用例です。

- DuckDB 接続を使った日次 ETL 実行
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（特定日）の評価（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡す）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- マーケットレジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB ファイルで管理）
```
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使って監査テーブルに書き込めます
```

- ファクター計算（research）
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
print(len(records))
```

開発時のヒント
- テスト時は OpenAI 呼び出し箇所（_kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）を unittest.mock.patch で差し替えて依存を切り離せます。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースの LLM センチメント処理（score_news）
    - regime_detector.py            -- マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETL 結果型再公開（ETLResult）
    - news_collector.py             -- RSS 収集（SSRF 対策・前処理）
    - calendar_management.py        -- マーケットカレンダー管理（営業日判定等）
    - stats.py                      -- zscore_normalize 等統計ユーティリティ
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Volatility/Value の計算
    - feature_exploration.py        -- 前方リターン計算、IC、統計サマリー
  - ai/, data/, research/ の他に strategy/ execution/ monitoring などのサブパッケージが想定（パッケージ __all__ に含まれる）

各モジュールは設計文書（README コメント）で「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」「テスト容易性」などの方針に従って実装されています。

---

## 開発上の注意点 / 仕様のポイント

- Look-ahead バイアス防止
  - AI / リサーチ系の関数は内部で datetime.today() を直接参照しない設計（必ず target_date を明示的に渡す）。
- 冪等性
  - J-Quants から取得したデータは DuckDB 側で ON CONFLICT DO UPDATE により上書きされるため、再取得が安全。
- LLM 呼び出し
  - レスポンスは JSON のみを期待、パース失敗や API エラー時はログに残してフォールバック（多くのケースで 0.0 を返す等）する設計。
- セキュリティ / 安全対策
  - news_collector は SSRF 対策・最大受信サイズ制限・XML の安全パーサ（defusedxml）を使用。
- ログレベル / 環境
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL により挙動やログ出力を制御。

---

必要に応じて README を拡張して、使い方（CLI スクリプト、スケジューラ設定例、DB スキーマ初期化手順、CI/Terraform などの運用手順）を追加できます。ご希望があればその内容で追記します。