# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ群（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど、アルゴリズム取引基盤に必要な機能をモジュール化して提供します。

---

## プロジェクト概要

KabuSys は次のような関心事を分離して実装した Python モジュール群です。

- データ収集／ETL（J-Quants API 経由の株価・財務・市場カレンダー取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- リサーチ（モメンタム／バリュー／ボラティリティ等のファクター計算）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 各種ユーティリティ（カレンダー管理、統計ユーティリティ等）

モジュールは duckdb ベースでデータを保持し、OpenAI（gpt-4o-mini）を利用した JSON Mode 呼び出しを行います。

---

## 主な機能一覧

- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - 差分取得、backfill、品質チェック、カレンダー先読み
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、未来日付・非営業日データ検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news への冪等保存
- ニュース NLP（kabusys.ai.news_nlp.score_news）
  - 銘柄ごとのセンチメントを OpenAI で評価して ai_scores に書き込み
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - ETF（1321）200 日移動平均乖離とマクロニュースを合成してレジーム判定
- リサーチ / ファクター（kabusys.research）
  - Momentum / Value / Volatility 等の計算、IC 計算、統計サマリー
- 監査ログ初期化（kabusys.data.audit.init_audit_db）
  - signal_events, order_requests, executions などの監査テーブルを初期化

---

## 前提条件 / 必要環境

- Python >= 3.10（typing の | 演算子などを使用）
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由で外部 API（J-Quants、OpenAI）へ接続できること

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルート）や OS 環境変数を読み込みます。自動読み込みはデフォルト有効で、無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須／任意）:

- 必須（ETL や J-Quants 利用時）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード（発注統合等）
- OpenAI 関連
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector のデフォルト）
- オプション
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
  - DUCKDB_PATH — デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — 環境 (development | paper_trading | live)
  - LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

サンプル .env（プロジェクトルート `.env`）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソース配置
2. Python 仮想環境作成・有効化
3. 依存パッケージをインストール（duckdb / openai / defusedxml 等）
4. プロジェクトルートに `.env` を作成して必要なキーをセット
5. DuckDB ファイル用ディレクトリ作成（例: data/）
6. 必要に応じて監査 DB 初期化（下記参照）

---

## 使い方（主要な呼び出し例）

以下は Python REPL やスクリプトから呼び出す簡単な例です。

- DuckDB に接続して ETL を実行（日次ETL）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP によるスコア付与（指定日）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
# OPENAI_API_KEY は環境変数か api_key 引数で指定可能
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログテーブルの初期化（独立 DB を使う例）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings
from pathlib import Path

audit_conn = init_audit_db(Path(settings.duckdb_path).with_suffix(".audit.duckdb"))
# これで signal_events / order_requests / executions 等が作成されます
```

- 自動 .env 読み込みを無効にする（テスト等）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print(settings.log_level)"
```

---

## ディレクトリ構成（主要ファイルと役割）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージ宣言（version 等）
- config.py
  - 環境変数読み込み・Settings クラス（自動 .env ロード、必須チェック）
- ai/
  - news_nlp.py : ニュースの銘柄別センチメント付与（OpenAI 呼び出し、バッチ処理、検証）
  - regime_detector.py : 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - jquants_client.py : J-Quants API クライアント（レート制御、リトライ、保存ロジック）
  - pipeline.py : 日次 ETL パイプライン（prices/financials/calendar + 品質チェック）
  - etl.py : ETLResult の再エクスポート
  - news_collector.py : RSS フィード取得・前処理・raw_news 保存（SSRF 保護）
  - calendar_management.py : 市場カレンダー管理（営業日判定、next/prev 等）
  - stats.py : z-score 正規化などの統計ユーティリティ
  - quality.py : データ品質チェック（欠損/重複/スパイク/日付不整合）
  - audit.py : 監査ログ（DDL / 初期化ユーティリティ）
- research/
  - factor_research.py : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン、IC、統計サマリー、ランク変換
  - __init__.py : 研究系ユーティリティの再エクスポート

この README は主要モジュールの概要を示すもので、詳細な API 仕様は各モジュールの docstring を参照してください。

---

## 注意事項 / 運用上のポイント

- OpenAI / J-Quants など外部 API キーは厳重に管理してください。テストや CI ではモック可能な設計になっています（モジュール内の _call_openai_api 等を patch）。
- データの取得タイミング・ウィンドウはルックアヘッドバイアスを避ける設計です。関数は内部で datetime.today() を極力参照しない設計になっています（target_date を明示）。
- DuckDB への insert は冪等（ON CONFLICT DO UPDATE）を基本にしているため、ETL の再実行が安全です。
- news_collector は SSRF / XML Bomb / レスポンスサイズ等の安全対策を実装していますが、運用環境での固有リスクは別途評価してください。

---

必要に応じて README を拡張して、実運用手順（cron / systemd の例）、監視（monitoring）や発注（execution）モジュールの利用方法、CI テスト方法なども追加できます。必要であれば追記します。