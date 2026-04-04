# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants 経由のデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（約定トレーサビリティ）など、トレーディングシステムに必要なコンポーネントを提供します。

---

## 主要な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（duckdb）
  - 差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集・NLP
  - RSS フィードからニュースを収集・前処理して raw_news テーブルへ保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（score_news）
  - マクロ記事 + ETF (1321) の MA200 乖離を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化 等

- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化
  - order_request_id を冪等キーとして二重発注防止を想定

- 設定管理
  - .env/.env.local または環境変数から設定を自動ロード（プロジェクトルート判定）
  - 必須設定は明示的に取得し不足時は例外を発生

---

## システム要件

- Python 3.10 以上（PEP 604 の型記法を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて追加ライブラリが必要になる場合があります）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 開発インストール（パッケージが setuptools/pyproject を含む場合）
python -m pip install -e .
```

---

## 環境変数（主なもの）

自動ロード順序: OS 環境変数 > .env.local > .env  
ルート判定はパッケージのファイル位置を基準に .git または pyproject.toml を探します。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（.env に設定する例）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD：kabuステーション API パスワード（注文系）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視 DB（例: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH：監視用ファイルパス
- KABUSYS_ENV：development / paper_trading / live（環境。デフォルト development）
- LOG_LEVEL：ログレベル（DEBUG, INFO, ...）

設定はコードから `from kabusys.config import settings` で参照できます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境を作成して依存をインストール
   - 例: `python -m venv .venv && source .venv/bin/activate`
   - 依存インストール: `pip install duckdb openai defusedxml`
   - （プロジェクトに pyproject.toml がある場合）`pip install -e .`
3. .env ファイルをプロジェクトルートに配置（.env.example を参照）
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（NLP を使う場合）
4. DuckDB データベース用ディレクトリを作成（デフォルトは data/）
   - 例: `mkdir -p data`
5. 必要に応じて監査DB初期化などを実行

---

## 使い方（主要な例）

以下はライブラリの代表的な呼び出し例です。各関数は DuckDB 接続（duckdb.connect(...) の返り値）を受け取るものが多いです。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア算出（OpenAI API キーは環境変数または api_key 引数で）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で設定
print(f"scored {count} codes")
# または明示的にキーを渡す:
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict リスト
```

- 監査スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

# 監査DBを別ファイルで初期化する例
audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

- RSS フィード取得（ニュースコレクタの低レベル API）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点:
- OpenAI 呼び出しは外部 API に依存するため API キーと通信可能環境が必要です。
- J-Quants API の呼び出しには有効なリフレッシュトークンが必要です（settings.jquants_refresh_token）。
- DuckDB 側のテーブルが存在しない場合、保存関数やクエリは実行時に前提テーブルがないと失敗する場合があります。ETL の初回実行前にスキーマ準備が必要なケースに留意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         -- ニュース NLP / OpenAI 呼び出し・バッチ処理
  - regime_detector.py  -- マーケットレジーム判定（MA200 + マクロ記事）
- data/
  - __init__.py
  - jquants_client.py   -- J-Quants API クライアント・保存ロジック
  - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
  - etl.py              -- ETL 結果クラスの再エクスポート
  - news_collector.py   -- RSS 収集・保存ユーティリティ
  - calendar_management.py -- 市場カレンダー管理・判定ロジック
  - stats.py            -- z-score 等の統計ユーティリティ
  - quality.py          -- データ品質チェック（欠損/スパイク/重複/日付不整合）
  - audit.py            -- 監査ログスキーマ初期化・ユーティリティ
  - (その他 jquants_client サポート関数 etc.)
- research/
  - __init__.py
  - factor_research.py  -- Momentum/Volatility/Value 計算
  - feature_exploration.py -- 将来リターン / IC / summary 等

ドキュメントや設定ファイル:
- .env, .env.local（プロジェクトルート、設定をここに置く）
- pyproject.toml（プロジェクトメタ情報。存在する場合）

---

## 実運用上の注意 / ベストプラクティス

- 環境分離: 開発 / paper_trading / live を `KABUSYS_ENV` で切り替え。live 環境では発注周りなどの取り扱いに注意。
- API キー管理: J-Quants / OpenAI キーは安全に管理し、バージョン管理には含めない（.env を .gitignore に追加）。
- フェイルセーフ: OpenAI や J-Quants の API エラーは多くの場所でフェイルセーフ（0.0 等）にフォールバックしますが、想定外の部分はログを確認してください。
- DuckDB スキーマ: ETL 実行前に requisite テーブルが存在するか、または初期スキーマを作成する手順を運用に含めてください。
- レート制限: J-Quants はレート制限（120 req/min）を守る実装になっています。アプリからの別途直接 API 呼び出しは同様に配慮してください。

---

## トラブルシューティング

- 環境変数が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD の設定を確認
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml を含むディレクトリ）に置く必要があります
- OpenAI 呼び出しで JSON パースエラーが出る場合:
  - レスポンスが JSON 以外になっている可能性があります。ログを確認し、`score_news` / `_validate_and_extract` のワーニングを参照してください
- DuckDB にテーブルが無い場合:
  - ETL 実行前にスキーマ準備が必要です。スキーマ作成ユーティリティ（ない場合はプロジェクト内の DDL を参照して作成）を利用してください

---

この README はコードベースの主要な機能と利用方法の概要を示しています。詳細な API 使用法や運用手順は各モジュールの docstring（ソース内に豊富に記載）を参照してください。質問や追加のドキュメントが必要であれば教えてください。