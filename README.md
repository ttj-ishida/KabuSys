# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

KabuSys は日本株向けのデータプラットフォームとリサーチ / 自動売買用ユーティリティ群を提供する Python パッケージです。J-Quants API や RSS、OpenAI（LLM）を利用した ETL、品質チェック、ニュースセンチメント、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを含みます。

主な想定用途:
- 日次 ETL による株価・財務・カレンダーの差分取得・保存
- ニュースの収集と銘柄別 AI センチメントスコアリング
- マーケットレジーム判定（MA + マクロニュースの LLM 評価）
- 研究用のファクター計算・特徴量解析（バックテスト前処理）
- 発注・約定までの監査ログ管理（DuckDB ベース）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（fetch / save 日足・財務・上場情報・カレンダー）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF・サイズ制限・トラッキング除去対応）

- データ品質
  - 欠損・重複・スパイク・日付不整合検出（quality モジュール）
  - ETL の品質チェック統合

- AI（LLM）連携
  - news_nlp: 銘柄ごとのニュースをまとめて LLM に送りセンチメントを算出（JSON Mode、バッチ、リトライ）
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを判定

- リサーチ / ファクター
  - momentum / volatility / value 等の定量ファクター算出（prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 監査 / トレーサビリティ
  - signal_events / order_requests / executions などの監査テーブル定義・初期化（DuckDB）
  - init_audit_db / init_audit_schema による冪等初期化

- その他
  - 環境設定読み込み（.env / .env.local 自動ロード、環境変数優先）
  - ログレベル・実行環境フラグ（development / paper_trading / live）

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクトでは requirements.txt や poetry/poetry.lock を用意してください。上記はコードが依存している主な外部パッケージです。）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   - venv を使用する例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt がない場合は最低限以下をインストール）
   ```
   pip install duckdb openai defusedxml
   ```
   または編集可能インストール:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（モジュール kabusys.config による自動読み込み）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL に必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（任意）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（任意）
   - DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live) （デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API とサンプル）

以下はライブラリをインポートして DuckDB 接続を作り、主要処理を実行する例です。

- 日次 ETL の実行（run_daily_etl）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
import duckdb
from kabusys.ai.news_nlp import score_news
from datetime import date
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にあれば api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書込み銘柄数:", n_written)
```

- マーケットレジーム判定（score_regime）
```python
import duckdb
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- 市場カレンダー判定ユーティリティ例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

注意点:
- LLM 呼び出し（OpenAI）はリトライやフォールバック処理を持ちますが、API キーの不足時は例外を投げます。
- ETL / API 呼び出しはネットワークや外部 API に依存するため、適切なエラーハンドリングとログ監視を行ってください。

---

## ディレクトリ構成（主要ファイルの説明）

（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
  - パッケージのバージョンと公開サブパッケージ定義

- src/kabusys/config.py
  - .env / .env.local 自動読み込み、環境変数からの設定取得用 Settings クラス

- src/kabusys/data/
  - calendar_management.py: JPX カレンダー管理（営業日判定／更新ジョブ）
  - pipeline.py: ETL パイプライン（run_daily_etl 他）
  - jquants_client.py: J-Quants API クライアント（fetch / save、認証・レート制御・リトライ）
  - news_collector.py: RSS 収集（SSRF 対策・圧縮対応・正規化）
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ（トレーサビリティ）スキーマ作成/初期化
  - etl.py: ETLResult のエクスポート

- src/kabusys/ai/
  - news_nlp.py: ニュースセンチメントスコアリング（銘柄ごと）
  - regime_detector.py: マーケットレジーム判定（MA + マクロニュース LLM）

- src/kabusys/research/
  - factor_research.py: momentum / volatility / value ファクター計算
  - feature_exploration.py: 将来リターン計算・IC・summary 等
  - __init__.py: 便利関数の再エクスポート

- その他想定サブパッケージ（strategy / execution / monitoring）
  - __init__ にリストされているものの、ここに含める各責務（売買戦略、発注実行、監視）は設計上のサブパッケージです。実装を追加することで完全な自動売買フローが構成されます。

---

## 動作設計上のポイント / 注意事項

- Look-ahead バイアス対策:
  - 日時の判定やデータ取得は target_date ベースで実装され、datetime.today() を直接参照しない設計が多くのモジュールで採用されています。
  - history データ利用時は「その時点で利用可能だったデータのみ」を用いるよう設計されています。

- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE などで冪等に保存されます。
  - audit の order_request_id は冪等キーとしての想定。

- フォールバック:
  - LLM 呼び出しで失敗した場合（リトライ後）は安全側として 0.0 を返す等、フェイルセーフを重視しています。

---

## トラブルシューティング

- 環境変数未設定エラー
  - Settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は未設定時に ValueError を投げます。`.env` を正しく配置するか環境変数を設定してください。

- OpenAI 呼び出しのエラー
  - レート制限やネットワーク障害、5xx 等はリトライされ、最終的に失敗した場合はモジュールごとに定義されたフォールバック（例: macro_sentiment = 0.0）に従います。ログを確認してください。

- DuckDB 互換性
  - 一部の executemany/リストバインドは DuckDB のバージョン依存の挙動を意識した実装になっています。問題がある場合は DuckDB のバージョンを確認してください。

---

この README は現在のコードベース（AI・Data・Research と関連ユーティリティ）に基づく概要と利用手順を記載しています。実運用を行う前に各設定（ログ出力、API キー管理、DB バックアップ、監視）を整備してください。質問や追加のドキュメント化が必要であれば教えてください。