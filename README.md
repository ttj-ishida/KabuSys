# KabuSys

日本株向け自動売買 / データプラットフォームのライブラリ集合です。  
J-Quants API からのデータ ETL、ニュース収集と LLM によるセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）等の機能を提供します。

主な設計方針：自動化と安全性（レート制御・リトライ・SSRF対策）、冪等性（DB 書き込みの ON CONFLICT）、およびバックテスト時のルックアヘッドバイアス防止。

Version: 0.1.0

---

## 主な機能一覧

- 環境変数・設定管理（自動 .env ロード / Settings）
- J-Quants API クライアント
  - 株価日足（OHLCV）の差分取得（ページネーション対応）
  - 財務データの取得
  - JPX マーケットカレンダー取得
  - レート制御、リトライ、トークン自動更新
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去、圧縮処理制限）
- ニュース NLP（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメント併合で bull/neutral/bear を判定：score_regime）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- マーケットカレンダー管理・営業日判定ユーティリティ
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化と専用 DB 初期化支援
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー計算、将来リターン、IC 計算、Z スコア正規化）

---

## 前提・準備

- Python 3.10 以上（PEP 604 の型 | を使用）
- ネット接続（J-Quants API、OpenAI、RSS フィード）
- DuckDB（Python パッケージ）、openai（OpenAI Python SDK）、defusedxml などの依存

例（pip）:
```
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt / pyproject.toml に依存を追加して管理してください
```

---

## 環境変数（.env）

プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須・推奨のキー例:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（利用する場合）
- SLACK_BOT_TOKEN: Slack 通知用（使用する場合）
- SLACK_CHANNEL_ID: Slack チャネル ID（使用する場合）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=＜your_jquants_refresh_token＞
OPENAI_API_KEY=＜your_openai_api_key＞
KABU_API_PASSWORD=＜your_kabu_password＞
SLACK_BOT_TOKEN=＜your_slack_token＞
SLACK_CHANNEL_ID=＜your_channel_id＞
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   # または個別に
   pip install duckdb openai defusedxml
   ```
4. `.env` を作成（プロジェクトルートに置く）
5. DuckDB ファイル用のディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```
6. （任意）自動 .env ロードを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（主要な利用例）

以下はライブラリを Python スクリプトから直接呼び出す例です。多くの API は DuckDB の接続オブジェクト（duckdb.connect(...).cursor() などではなく直接 duckdb.connect() が返す接続）を受け取ります。

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使う）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を None にすると環境変数 OPENAI_API_KEY を使用
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（1321 MA200 + マクロセンチメント）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions のスキーマが作成されます
```

- マーケットカレンダー／営業日判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を想定しており、API の失敗時はフェイルセーフで 0.0 を返すなど堅牢化が施されています。
- 多くの処理はルックアヘッドバイアスを避ける実装（target_date 未満のデータのみを使用）になっています。
- DuckDB の executemany による空リストバインドに注意した実装がされています（一部関数で明示的に空チェックあり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py               : 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py           : ニュースセンチメント（score_news）
    - regime_detector.py    : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント / 保存ロジック
    - pipeline.py           : ETL パイプライン（run_daily_etl など）
    - etl.py                : ETLResult 再エクスポート
    - news_collector.py     : RSS ニュース収集
    - calendar_management.py: マーケットカレンダー管理・営業日判定
    - quality.py            : データ品質チェック
    - stats.py              : 統計ユーティリティ（zscore_normalize）
    - audit.py              : 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    : モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py: 将来リターン/IC/統計サマリー 等

---

## 実運用に関する注意事項

- セキュリティ
  - news_collector は SSRF を防ぐためリダイレクト先の検証、ホストのプライベートアドレスチェック、受信サイズ制限を実装。
  - .env の取り扱いは慎重に（トークンは機密情報）。
- API レート制御・リトライ
  - J-Quants / OpenAI の呼び出しは適切なリトライとバックオフ、レート制御が実装されていますが、本番での大量呼び出し時は追加監視を推奨します。
- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING により冪等に設計されています。
- バックテスト
  - 各モジュールはルックアヘッドバイアスを極力排除するように設計されています。バックテストの際はデータの取得タイミング（fetched_at 等）に注意してください。
- トランザクション
  - 重要な書き込みは BEGIN / DELETE / INSERT / COMMIT のパターンで冪等操作を行います。DDL 初期化時の transactional フラグや ROLLBACK 処理に注意。

---

## 追加情報 / 貢献

バグ報告・改善提案は issue を立ててください。設計方針（Look-ahead 防止、冪等性、フェイルセーフ等）を尊重した PR を歓迎します。

---

README の内容はコードベースの実装に基づいて作成しています。特定の運用フロー（kabu ステーションとの約定連携、Slack 通知のワークフロー等）は環境・運用要件に応じて追加実装してください。