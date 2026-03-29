# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買サブシステム群。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI（LLM）等と連携してデータ取得（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログ管理を行います。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ ETL
  - J-Quants からの日次株価（OHLCV）、財務データ、JPX市場カレンダー取得（差分・ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT / upsert）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次パイプライン run_daily_etl による一括処理
- ニュース収集 / 前処理
  - RSS からの収集、URL 正規化、SSRF 対策、記事ID（SHA-256）による冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM へ投げ、センチメント（ai_scores）を算出（score_news）
  - マクロニュースを LLM で評価しETF（1321）の MA200 乖離と合成して市場レジーム判定（score_regime）
  - API エラー時のリトライ・フォールバックロジック装備
- リサーチ系ユーティリティ
  - モメンタム、ボラティリティ、バリューなどのファクター算出（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env（プロジェクトルート）自動ロード（OS 環境変数優先）。テスト時に自動ロード無効化可能

---

## 要件 / 依存ライブラリ（主要）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ

（実行環境ではネットワークアクセス、OpenAI API キー、J-Quants リフレッシュトークン等が必要）

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   # 開発時はローカルパッケージとしてインストール
   pip install -e .
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml を利用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合（score_news / score_regime に未指定時に参照）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH / SQLITE_PATH: データベースパス（デフォルトは data/kabusys.duckdb / data/monitoring.db）
   - 簡易 `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB 初期化（監査DB など）
   - 監査用 DB を初期化する例（Python）
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB コネクションへスキーマのみ追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプト例です。多くの関数は DuckDB コネクション（duckdb.connect(...) の戻り値）と target_date（datetime.date）を受け取ります。

1. DuckDB に接続する
   ```python
   import duckdb
   from kabusys.config import settings
   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメントの算出（OpenAI API キーが必要）
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
   print(f"scored {n} symbols")
   ```

4. 市場レジーム判定
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

5. ファクター計算 / リサーチ
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from datetime import date
   mom = calc_momentum(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

6. 品質チェックを個別または一括で実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)
   ```

注意:
- score_news / score_regime は OpenAI への呼び出しを行います。実行時に API キーを明示するか環境変数に設定してください。
- 多くの処理は「ルックアヘッドバイアス」を避けるため target_date を明示して実行する設計です。内部で datetime.today()/date.today() を直接参照しないよう配慮されています（ただし run_daily_etl は省略時に date.today() を使用します）。

---

## 自動 .env 読み込みについて

- モジュール起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、`.env` → `.env.local` の順で自動読み込みします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きできます（ただし OS 環境変数は保護される）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## 開発上の注意点 / 設計方針（抜粋）

- Look-ahead bias を避けるため、バックテスト用途ではデータ取得日・target_date の管理に注意してください。多数の関数は target_date 未満／以前等の条件を厳格に扱います。
- OpenAI / J-Quants 呼び出しはリトライと指数バックオフを持ち、失敗時はフェイルセーフ（多くの場合ゼロスコアやスキップ）を採用しています。
- DuckDB へは executemany を使った冪等保存を行います。DuckDB のバージョン依存（executemany の空リスト等）に注意してコードが書かれています。
- ニュース収集には SSRF や XML 攻撃対策（defusedxml、ホスト/リダイレクトの検査、最大受信サイズ制限）を実装しています。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュースセンチメント（score_news）
  - regime_detector.py      — マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch / save）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETLResult 再エクスポート
  - news_collector.py       — RSS 収集
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
  - audit.py                — 監査ログスキーマ / init_audit_db
- research/
  - __init__.py
  - factor_research.py      — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

（上記は主要モジュールの抜粋です。実行には各テーブルスキーマの作成や DuckDB データベースの初期化が必要です）

---

## 参考 API のエントリポイント / 例

- ETL（全体）: kabusys.data.pipeline.run_daily_etl
- 日次株価 ETL: kabusys.data.pipeline.run_prices_etl
- 財務 ETL: kabusys.data.pipeline.run_financials_etl
- カレンダー ETL: kabusys.data.pipeline.run_calendar_etl
- ニューススコア: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査DB初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- ファクター計算: kabusys.research.factor_research.calc_momentum / calc_value / calc_volatility

---

README 上の説明はコードの主要設計方針・使用方法のサマリです。実際の運用では環境（API キー、DB パス、ログ設定等）とデータスキーマの初期整備を行ってから実行してください。必要であれば、README にサンプル .env.example、DDL（テーブル作成脚本）、運用手順（cron / Airflow ジョブ等）を追加できます。希望があれば追記します。