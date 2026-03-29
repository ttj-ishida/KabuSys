# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、リサーチ・ファクター計算、監査ログ（監査テーブル初期化）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、内部で日時を直接参照する処理は最小化／設計上回避しています（target_date を明示的に与える設計）。
- DuckDB をデータ層に用い、ETL は冪等（ON CONFLICT / INSERT … DO UPDATE）を意識しています。
- 外部 API 呼び出し（J-Quants / OpenAI）には堅牢なリトライ・バックオフ・レートリミット・フェイルセーフを導入しています。

---

## 機能一覧

- データ ETL
  - J-Quants からの株価日足（OHLCV）、財務、JPX カレンダーの差分取得・保存（duckdb）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比）、日付整合性チェック（quality モジュール）
- ニュース収集
  - RSS フィードの取得と前処理（SSRF 対策・受信サイズ制限・URL正規化）
- ニュース NLP
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント集計（ai_score → ai_scores）
  - バッチ送信・JSON Mode 用の堅牢なレスポンス検証・リトライ実装
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを合成して market_regime に記録
- 研究用ユーティリティ
  - ファクター算出（モメンタム、バリュー、ボラティリティ等）、将来リターン、IC 計算、Z スコア正規化 等
- 監査（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化ユーティリティ
- J-Quants クライアント（jquants_client）
  - 認証（refresh token → id_token）、ページネーション対応、保存ヘルパー（raw_prices/raw_financials/market_calendar）

---

## 前提・依存

推奨 Python バージョン：3.10 以上（typing の `X | Y` を使用しているため）  
主な依存パッケージ（最低限）：
- duckdb
- openai
- defusedxml

例（pip）:
```
pip install duckdb openai defusedxml
```

※ 実行環境に応じて他ライブラリや OS 側の設定が必要になることがあります（DuckDB のネイティブ依存等は通常不要）。

---

## 環境変数（主要）

プロジェクトは .env / .env.local / 環境変数から設定を読み込みます（自動ロード）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（注文連携等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン／取得してパッケージをインストール
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

   または、依存を直接インストール:
   ```
   pip install duckdb openai defusedxml
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` を配置する（上記の必須変数を設定）
   - 自動ロードを無効にしたいテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

3. DuckDB（監査用 DB 等）の格納先ディレクトリを作成（例: data/）
   ```
   mkdir -p data
   ```

4. OpenAI / J-Quants の認証情報を用意する

---

## 使い方（主な例）

以下は Python REPL やスクリプトから呼ぶ例です。

- DuckDB 接続の作成（設定 DUCKDB_PATH を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントをスコアリング（ai.news_nlp.score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベースを初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへアクセス可能
```

- ETL の戻り値クラス（ETLResult）
```python
from kabusys.data.etl import ETLResult  # pipeline から re-export
# ETLResult の has_errors や to_dict を利用
```

注意事項：
- OpenAI を使う関数（score_news, score_regime）はデフォルトで環境変数 OPENAI_API_KEY を参照します。引数で api_key を明示的に渡すことも可能です。
- ETL / API 呼び出しはネットワーク・認証に依存します。エラーはログに出力され、可能な限りフェイルセーフ（処理継続）になりますが、必須認証情報がない場合は例外を投げます。

---

## 典型的なワークフロー（例）

1. .env を作成して J-Quants / OpenAI のキーを設定
2. 日次バッチで run_daily_etl を実行して DuckDB を更新
3. ニュース収集ジョブで raw_news を更新（news_collector を使う）
4. score_news を実行して ai_scores を更新
5. score_regime を実行して market_regime を更新
6. research モジュールを使ってファクター分析やバックテストの入力を作成
7. 戦略レイヤ → 監査テーブル → 実行（order_requests / executions）という流れで監査を残す

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/ の機能: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- data/ の機能: ETL（run_daily_etl 等）、J-Quants クライアント、品質チェック、ニュース収集、監査テーブル初期化 など

（ファイル一覧は README 作成時点の主要モジュールを抜粋しています。詳細はソースコードを参照してください。）

---

## 運用上の注意

- 自動売買・実運用を行う場合は必ず paper_trading 環境で十分な検証を行ってください（KABUSYS_ENV=paper_trading を使用）。
- OpenAI 呼び出しはコストが発生します。batch サイズやリトライ設定を環境に合わせて調整してください。
- J-Quants の API レート制限に従うよう RateLimiter が組み込まれているものの、大量同時実行は避けてください。
- DuckDB のスキーマ／マイグレーションは慎重に扱ってください。監査テーブルは削除しない運用を想定しています。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。詳細な API 仕様や運用フローはソースコード中の docstring（各モジュール冒頭）を参照してください。問題や追加で欲しいセクションがあれば教えてください。