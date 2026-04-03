# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理など、アルゴリズムトレードの基盤的処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主眼に設計されたモジュール群です。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）と DuckDB への冪等保存
- RSS によるニュース収集と OpenAI を使ったニュースセンチメント（銘柄別）スコアリング
- マクロニュースと ETF の 200 日移動平均乖離を組み合わせた市場レジーム判定
- 研究（Research）用ファクター計算・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引シグナルから約定に至る監査ログテーブルの初期化・管理
- セットアップ時に .env/.env.local から環境変数を自動ロード（プロジェクトルートを探索）

設計方針の特徴：ルックアヘッドバイアス回避、冪等性重視、API リトライ・レート制御、外部呼び出しを分離した安全な実装。

---

## 主な機能一覧

- data/
  - ETL パイプライン（日次 ETL: run_daily_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - market calendar 管理（営業日判定・更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
  - 統計ユーティリティ（z-score 正規化）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA200 とマクロニュースを組合せ市場レジーム判定（bull/neutral/bear）
- research/
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（forward returns、IC、統計サマリー等）
- config.py
  - 環境変数の管理、.env/.env.local の自動読み込み（プロジェクトルートを基準）
  - settings オブジェクト経由で設定にアクセス

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union 型表記等が使われています）
- DuckDB が使える環境
- OpenAI API キー（ニュース/レジーム機能を使う場合）
- J-Quants リフレッシュトークン（ETL を実行する場合）

1. リポジトリをクローン／配置
   - 開発時: pip editable install などでローカル環境にインストールできます。

2. 依存パッケージのインストール（例）
   - requirements ファイルは同梱されていないため、以下をインストールしてください（例）:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、自動的に読み込まれます。
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>

   # Kabu Station（発注 API）
   KABU_API_PASSWORD=<your_kabu_api_password>
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI（AI モジュールを使う場合）
   OPENAI_API_KEY=<your_openai_api_key>

   # optional: LINE 通知
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

   # DB パスなど
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境設定
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

4. プロジェクトルートの検出
   - config._find_project_root() は `.git` または `pyproject.toml` を探索してプロジェクトルートを決定します。パッケージ配布後や CI ではルートが見つからない場合、自動ロードはスキップされます。

---

## 使い方（代表的な例）

以下は Python から本ライブラリを利用する簡単な例です。

1) DuckDB 接続と ETL（日次パイプライン）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 当日分の日次 ETL を実行（target_date を明示して過去日で実行可能）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI 必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に api_key を渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

3) 市場レジーム判定（OpenAI 必要）
```python
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)
# 監査テーブルが作成されます
```

5) J-Quants の API を直接呼ぶ（例: 一覧取得）
```python
from kabusys.data.jquants_client import fetch_listed_info
from kabusys.config import settings

records = fetch_listed_info(date_=date(2026,3,20))
print(len(records))
```

注意:
- OpenAI 呼び出しは外部 API に依存します。テスト時は内部の _call_openai_api をモックすることを想定しています。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを行いますが、実行には有効な JQUANTS_REFRESH_TOKEN が必要です。

---

## 主要な設定項目（settings）

settings オブジェクト経由で参照します（kabusys.config.settings）。

主なプロパティ:

- jquants_refresh_token: J-Quants のリフレッシュトークン（必須）
- kabu_api_password: kabu ステーション API のパスワード（必須）
- kabu_api_base_url: 発注 API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token, line_user_id: 通知用
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- pid_file_path, kill_flag_path, kill_flag_clear_on_start: 実行監視設定
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct: 監視閾値
- env: KABUSYS_ENV（development | paper_trading | live）
- log_level: LOG_LEVEL（DEBUG | INFO | WARNING | ERROR | CRITICAL）

必須の環境変数が未設定のときは settings のプロパティアクセスで ValueError が発生します。

---

## テスト・デバッグのヒント

- 自動 .env ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出しは外部 API 依存部分をモックしてユニットテストを行うことが推奨されます（モジュール内で _call_openai_api をパッチする等）。
- DuckDB のバージョン差や executemany の仕様に依存する箇所があるため、DuckDB は推奨バージョンを固定して運用してください。
- news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）を実装しているため、内部ネットワークへのアクセスが心配な環境でも比較的安全に動きます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py

src/kabusys/ai/
- __init__.py
- news_nlp.py         — ニュース NLP（score_news）
- regime_detector.py  — 市場レジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- jquants_client.py    — J-Quants API クライアント（fetch_* / save_*）
- pipeline.py         — ETL パイプライン（run_daily_etl 等）
- etl.py              — ETLResult 再エクスポート
- news_collector.py   — RSS ニュース収集
- quality.py          — データ品質チェック
- stats.py            — 統計ユーティリティ（zscore_normalize）
- calendar_management.py — 市場カレンダー管理（is_trading_day など）
- audit.py            — 監査ログテーブル定義・初期化
- (他モジュールが存在する場合あり)

src/kabusys/research/
- __init__.py
- factor_research.py  — ファクター計算（momentum/value/volatility）
- feature_exploration.py — forward returns / IC / summary / rank

（上記はコードベースから抜粋した主要ファイル一覧です）

---

## ライセンス・貢献

（この README にはライセンス情報が含まれていません。実運用・公開時は LICENSE ファイルを追加してください。）

貢献方法、Issue、PR の流れ等はリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

---

必要であれば README に動作例や API リファレンス（関数説明・返り値の仕様）を追記します。どのセクションを詳しくしたいか教えてください。