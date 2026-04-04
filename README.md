# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログなどを含み、研究（Research）から実運用（Execution / Monitoring）までを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を統合した Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB 保存、冪等化）
- RSS ニュース収集と前処理（SSRF 防御、URL 正規化）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント解析および市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレースを保持）
- 環境変数ベースの設定管理（.env 自動読み込みをサポート）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で date.today() 等を直接参照しない（呼び出し側で基準日を渡す）
- DuckDB を用いた SQL 処理中心の実装（高速・ファイルDB）
- 外部 API 呼び出しはリトライやレート制御を備える（J-Quants / OpenAI）
- モジュールごとにフェイルセーフ（API失敗時はスキップやスコア0にフォールバック）を想定

---

## 主な機能一覧

- 環境設定: `kabusys.config.settings`（.env 自動ロード、必須キーチェック）
- ETL:
  - 日次 ETL 実行: `kabusys.data.pipeline.run_daily_etl`
  - 個別 ETL: `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`
- J-Quants クライアント: `kabusys.data.jquants_client`（取得・保存関数）
- ニュース収集: `kabusys.data.news_collector.fetch_rss`, `preprocess_text`
- ニュース NLP: `kabusys.ai.news_nlp.score_news`（銘柄別 AI スコアを ai_scores テーブルへ書込）
- レジーム判定: `kabusys.ai.regime_detector.score_regime`（ma200 と マクロセンチメントの合成）
- 研究用ユーティリティ: `kabusys.research.*`（factor 計算、forward returns、IC、統計サマリ等）
- データ品質チェック: `kabusys.data.quality.run_all_checks`（QualityIssue 列挙）
- 監査ログ初期化: `kabusys.data.audit.init_audit_db` / `init_audit_schema`
- 汎用統計: `kabusys.data.stats.zscore_normalize`

---

## セットアップ手順（開発者向け）

前提: Python 3.10 以上（typing の `|` を使用しているため）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（主要なもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt がある場合はそれを利用してください。

3. パッケージのインストール（開発モード）
   - プロジェクトルートに `pyproject.toml` / setup がある想定:
     - pip install -e .

4. 環境変数の設定
   - .env または環境変数で設定します（後述の必須キーを参照）。
   - 自動ロード:
     - パッケージ初期化時にプロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます。
     - 読み込み順: OS 環境変数 > .env.local > .env
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データディレクトリの準備
   - デフォルトで DuckDB 等は `data/` 下を使用する設定値がデフォルトです。必要に応じて作成してください。
     - mkdir -p data

---

## 必須 / 推奨環境変数

主要な環境変数（settings 経由で参照）:

- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（実行モジュールで使用）

- 任意（デフォルト値あり）:
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を直接呼ぶ場合に必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用途
  - DUCKDB_PATH: デフォルト DuckDB ファイル （デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等（監視関連）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

必須変数が未設定の場合、settings のプロパティ呼び出しで ValueError を投げます。

---

## 使い方（主要な API と実行例）

以下は典型的な使い方の例です。DuckDB 接続を作成して各操作を呼び出します。

1) 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

3) 日次 ETL 実行（市場カレンダー、株価、財務の差分取得・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュースセンチメント（銘柄別）を取得して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

5) 市場レジームスコアを計算して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

6) 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルへ書き込み等を行う
```

7) 研究用ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は各銘柄ごとの dict のリスト
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を明示するか環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フォールバックロジックを備えますが、料金やレート制限に注意してください。
- ETL 系関数は J-Quants API にアクセスします。JQUANTS_REFRESH_TOKEN の設定が必要です。

---

## 自動 .env 読み込み挙動

- パッケージロード時にプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を探索し、.env / .env.local を自動読み込みします。
- 読み込み優先度:
  - OS 環境変数（最優先）
  - .env.local（上書き）
  - .env（既定）
- 無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します（テスト用途など）。

.env のパーサは export KEY=... 形式、クォート、インラインコメント等に対応しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         -- 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                      -- ニュースセンチメント（銘柄別）
  - regime_detector.py               -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                -- J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py                      -- ETL パイプライン / run_daily_etl
  - etl.py                           -- ETL 結果型再エクスポート
  - news_collector.py                -- RSS 収集 / 前処理
  - calendar_management.py           -- 市場カレンダー管理 / is_trading_day 等
  - quality.py                       -- データ品質チェック
  - stats.py                         -- zscore_normalize 等ユーティリティ
  - audit.py                         -- 監査ログスキーマの初期化
- research/
  - __init__.py
  - factor_research.py               -- モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py           -- forward returns / IC / 統計サマリ

この README は主要なエントリポイントと実行例を示しています。各モジュールには詳細な docstring と設計注釈が含まれていますので、実装を確認しながら個別ユースケースに合わせて利用してください。

---

## 注意事項 / 運用上のヒント

- OpenAI / J-Quants API のキー管理とレート/コスト管理に注意してください。テスト時は API キーを明示的に差し替えるかモックして呼び出しを抑制してください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない運用を想定しています。
- ETL の実行は cron 等で日次運用することを想定しています。run_daily_etl の戻り値 ETLResult をログまたは監視システムへ送ると良いです。
- production/live 環境では KABUSYS_ENV を `live` に設定し、追加の安全チェックや監視を有効にしてください。

---

必要があれば、README に含める具体的なコマンドや CI/CD 実行例、Dockerfile サンプル、requirements.txt の推奨内容なども作成します。どの部分を詳しく追加しますか？