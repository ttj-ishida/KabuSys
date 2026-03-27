# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。J-Quants / kabuステーション / OpenAI（LLM）等と連携して、データ取得（ETL）、品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどの機能を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を用いたローカルデータレイク」「API 呼び出しの堅牢なリトライ・フェイルセーフ」です。

---

## 機能一覧

- 環境変数 / .env 自動ロード（`kabusys.config`）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報
  - レート制限・認証リフレッシュ・ページネーション対応
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新／バックフィル／品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）と NLP（OpenAI）
  - RSS の安全取得（SSRF 対策、サイズ制限、トラッキング除去）
  - ニュースを銘柄と紐付け、`raw_news`／`news_symbols` を更新
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント集約（`score_news`）

- マーケットレジーム判定（`score_regime`）
  - ETF (1321) の 200 日 MA 乖離とマクロニュース LLM センチメントを合成してレジーム判定

- リサーチ / ファクター計算（`kabusys.research`）
  - Momentum, Volatility, Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブルを初期化するユーティリティ
  - すべて UTC タイムスタンプ、冪等性を考慮した設計

---

## 要件

- Python 3.10+
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

※ 実行環境によって追加パッケージが必要になる場合があります。自由に requirements.txt を作成してください。

---

## セットアップ手順

1. リポジトリをクローン（もしくはプロジェクトに追加）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最小例）
   ```
   pip install duckdb openai defusedxml
   # 開発インストール (パッケージ化されている場合)
   pip install -e .
   ```

4. 環境変数（.env）の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（`kabusys.config`）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env` の最小例
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化・DB 操作

- 監査ログ用の DuckDB を初期化する（ファイル版 / メモリ版両対応）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: を指定してメモリ DB にすることも可
```

- プロジェクトが使用するデータベース接続の例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

---

## 使い方（代表的な API）

以下はライブラリ関数の簡単な利用例です。スクリプトやジョブから呼び出して使います。

- 日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を実行する:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {n_written}")
```

- レジーム判定を実行する:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（リサーチ用）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は [{ "date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

---

## 環境変数（主に必須なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系で利用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に必要
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

注意: 必須の設定（`_require` を使用しているもの）は不足すると起動時に例外が発生します。

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動ロード、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの収集ウィンドウ定義、OpenAI を用いた銘柄別センチメント取得（score_news）
    - regime_detector.py
      - ETF の MA 乖離とマクロニュース LLM を統合して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得関数・保存関数（save_*）
    - pipeline.py
      - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
    - news_collector.py
      - RSS 取得、安全性チェック、記事正規化、raw_news への保存ロジック
    - calendar_management.py
      - market_calendar の管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）および calendar_update_job
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py
      - 監査ログテーブルのDDL・初期化ユーティリティ（init_audit_schema, init_audit_db）
    - etl.py
      - pipeline.ETLResult の公開再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、rank、統計サマリー
  - research, monitoring, strategy, execution 等のパッケージは __all__ で公開される想定（コードベース依存）

---

## 運用上の注意・ベストプラクティス

- Look-ahead 防止:
  - 本ライブラリは内部で target_date 未満のみ参照する等、ルックアヘッドバイアスに配慮した実装がされています。バックテストで使用する際は ETL データをバックテスト開始日以前の状態に合わせて用意してください。

- OpenAI / J-Quants の API 呼び出し:
  - レート制限・課金に注意してください。`score_news` / `score_regime` は外部 API を呼び出します。テスト時は `_call_openai_api` をモックしてください（コード内で差し替え可能）。

- 自動 .env 読み込み:
  - テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、自前で環境変数注入を行うのが安全です。

- DuckDB の executemany 空リスト問題:
  - 一部 DuckDB バージョンでは executemany に空リストを渡せない箇所があります（コード内でチェック済み）。

---

## 貢献・開発

- コーディング規約、ユニットテスト、CI 設定等はリポジトリの方針に従ってください。
- 外部 API を使う部分はモック化しやすい設計になっています（テスト時はネットワーク呼び出しを差し替えてください）。

---

## トラブルシューティング

- 環境変数不足でエラーが出る場合は `kabusys.config.settings` の各プロパティを参照し、必要なキーを `.env` に追加してください。
- OpenAI レスポンスのパース失敗や API エラーはフェイルセーフで 0.0 を返す等の保護が入っていますが、繰り返し失敗する場合は API キーやネットワーク、モデル名（gpt-4o-mini）が利用可能か確認してください。
- J-Quants API の 401 は自動でリフレッシュを試みますが、リフレッシュトークンが無効な場合は `JQUANTS_REFRESH_TOKEN` を更新してください。

---

README はここまでです。より詳細な使い方（スケジューリング例、Slack 通知、kabuステーション 経由の注文フローなど）が必要であれば、想定ユースケースを教えてください。さらに具体的なセットアップ手順やサンプルスクリプトを追加します。