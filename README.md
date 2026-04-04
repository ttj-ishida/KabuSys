# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集合です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants 接続、カレンダー管理などを含みます。

## 主な特徴
- J-Quants API 経由の差分 ETL（株価・財務・カレンダー）と品質チェック
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント（銘柄別 ai_score）生成
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究（research）用のファクター計算・特徴量探索・IC/統計ユーティリティ
- DuckDB を用いた冪等保存（ON CONFLICT）と監査用スキーマ（signal → order → execution トレーサビリティ）
- 設定は環境変数 / .env(.local) から自動読み込み（配布後も動作するようにプロジェクトルートを探索）

## 必要要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt や pyproject.toml に従ってください）

## 環境変数（主なもの）
設定は environment またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます。
自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD     : kabu ステーション API パスワード（約定連携など）

任意（デフォルトあり）
- KABU_API_BASE_URL     : デフォルト `http://localhost:18080/kabusapi`
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用、関数引数で上書き可）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用
- DUCKDB_PATH           : デフォルト `data/kabusys.duckdb`
- SQLITE_PATH           : デフォルト `data/monitoring.db`
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
- KABUSYS_ENV           : `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL             : `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）

設定オブジェクトは `from kabusys.config import settings` で参照できます。

## セットアップ手順（開発環境向けの一例）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - または pyproject.toml / requirements.txt があればそれに従う
4. プロジェクトを editable インストール（任意）
   - pip install -e .

5. 環境変数を用意（例 `.env`）
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - DUCKDB_PATH=data/kabusys.duckdb

自動で `.env` / `.env.local` を読み込む仕組みは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に探索します。

## 使い方（代表的な例）

- 共通：DuckDB 接続を作って各 API に渡す
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

### 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())
```

### ニュースセンチメント（銘柄単位 ai_score）を生成する
- OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で指定可能
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,19))
print("書き込み銘柄数:", n_written)
```

### 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,19))
```

### 監査ログスキーマの初期化 / 監査 DB の作成
- 既存接続にスキーマを追加:
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```
- 監査専用 DuckDB を作成して初期化（ファイルパスの親ディレクトリを自動作成します）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

### 設定読み取り例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.jquants_refresh_token)  # 必須。未設定だと ValueError
```

## 主要モジュールとディレクトリ構成
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースの集約 / OpenAI による銘柄別センチメント -> ai_scores 書込
    - regime_detector.py  : ETF 1321 の MA + マクロニュース LLM を合成して market_regime 書込
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - pipeline.py          : ETL の差分取得 / run_daily_etl など
    - etl.py               : ETL 結果クラスの公開（ETLResult）
    - news_collector.py    : RSS 収集・前処理・raw_news 保存
    - calendar_management.py: 市場カレンダー判定・更新ジョブ
    - quality.py           : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             : zscore_normalize 等の統計ユーティリティ
    - audit.py             : 監査ログ（signal / order_requests / executions）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   : Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク変換
  - research/... (他ユーティリティ)
  - （その他: strategy, execution, monitoring パッケージが __all__ に存在する想定）

各モジュールは設計方針コメントを含み、ルックアヘッドバイアス対策やフェイルセーフ処理、DuckDB 上での冪等保存・トランザクション制御に配慮されています。

## テスト / 開発上の注意
- .env 自動読み込みはプロジェクトルートを基準に行います。テストでこれを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。
- OpenAI 呼び出し部分（news_nlp / regime_detector）はユニットテスト時に内部の API 呼び出しラッパーをモック (patch) できるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api を差し替え）。
- DuckDB の executemany の挙動に関するコメントや、API リトライロジック・RateLimiter は実運用を想定して実装されています。実際の運用前に小規模データで動作確認をしてください。

## 参考（実装上の重要点）
- ETL は差分更新＋バックフィル（デフォルト 3 日）を行い、後出し修正を吸収する設計です。
- ニュースウィンドウは JST を基準に定義され、内部では UTC naive datetime に変換して DB と比較します（ルックアヘッド防止）。
- OpenAI とのやり取りは JSON mode（response_format）を使用し、レスポンスのバリデーションと冗長なテキスト排除ロジックを実装しています。
- J-Quants クライアントは 120 req/min のレートを守るため固定間隔スロットリングを行い、401 時は自動リフレッシュを試みます。

---

不明点や README に追加したい利用例（例: CLI スクリプト、Docker 化、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example や簡易セットアップスクリプトの例も作成します。