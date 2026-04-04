# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL、ニュースNLP、ファクター計算、監査ログ等を含むモジュール群を提供します。本リポジトリはバックテスト／リサーチ環境と実取引（kabuステーション）連携を想定した設計になっています。

---

## プロジェクト概要

KabuSys は以下の役割を持つ Python パッケージ群です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集・前処理（RSS）と OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を格納する DuckDB スキーマ初期化

設計上の共通方針：
- ルックアヘッドバイアスを防ぐ（target_date のみを参照し datetime.today() などは内部で参照しない実装）
- フェイルセーフ（API 失敗時はスキップまたは中立値で継続）
- DuckDB を永続ストレージ／分析基盤として利用
- 冪等性を考慮した保存ロジック（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（missing, spike, duplicates, date_consistency）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント解析（OpenAI）
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成した市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings（環境変数ラッパ）

---

## 必要条件（Prerequisites）

- Python 3.8+（コードは型ヒントと標準ライブラリ中心に記述）
- DuckDB (Python パッケージ: duckdb)
- OpenAI Python SDK (openai) — news_nlp / regime_detector で使用
- defusedxml — RSS XML の安全パース
- ネットワークアクセス：J-Quants API / OpenAI API / RSS フィード
- J-Quants のリフレッシュトークン、OpenAI API キー 等の環境変数

インストール例（最低限の依存）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# あるいはプロジェクトに pyproject/requirements.txt があればそれを使う
# pip install -e .
```

---

## 環境変数（主なもの）

パッケージはプロジェクトルート（.git または pyproject.toml）を探し `.env` / `.env.local` を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。

主要な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL で使用）

- OPENAI_API_KEY (必須 for AI モジュール呼び出し時)  
  OpenAI API キー（score_news / score_regime のデフォルト）

- KABU_API_PASSWORD (必須 for 発注モジュール（未掲載の execution モジュール等）)  
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi

- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb  
- SQLITE_PATH (任意) — 監視 DB など（data/monitoring.db）

- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境を作る・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # あるいはプロジェクトに requirements.txt/pyproject があればそれを使う
   ```

4. 環境変数を設定（.env またはシェル環境）
   - .env をプロジェクトルートに作成（.env.local は .env を上書きする）
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（AI を使う場合）

5. DuckDB ファイルのディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから主要機能を使う例です。

- 設定・接続の例
```python
from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB 接続（settings.duckdb_path は Path を返す）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に API キーを渡すことも可能（None -> OPENAI_API_KEY 環境変数を使用）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

# settings.sqlite_path / settings.duckdb_path 等を使って初期化可能
audit_conn = init_audit_db(settings.duckdb_path)  # :memory: も可
```

- RSS フィード取得（ニュースコレクタの低レベルAPI）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注：
- score_news / score_regime は OpenAI への API 呼び出しを行います。単体テストでは内部の _call_openai_api をモックすることが想定されています。
- ETL や保存関数は DuckDB 上のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を前提とします。スキーマ初期化が必要な場合は別途スキーマ定義（data.schema 等）を実行してください（本 README に収録されているファイル群に schema 初期化コードが含まれている可能性があります）。

---

## 実装上の注意点 / ヒント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込みます。テスト中に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはモジュールレベルでレートリミッタとトークンキャッシュを持っており、401 では自動リフレッシュを行います。
- OpenAI 呼び出しのエラー（ネットワーク、429、5xx）については指数バックオフでリトライする実装があります。API 失敗時は多くの関数が中立値で継続する設計です（例: macro_sentiment=0.0）。
- DuckDB に対する executemany の挙動やバージョン差異に配慮してコードが書かれています（空リストの executemany 回避など）。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベートIPブロック）や XML の安全パースを行っています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数設定読み込み & Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの銘柄別センチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック（missing, spike, duplicates, date_consistency）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー

（strategy / execution / monitoring 系のモジュールは __init__ の __all__ に含まれていますが、このコード抜粋には含まれていません。リポジトリ全体を参照してください。）

---

## 開発・テストについて

- OpenAI 呼び出しや外部 API はテストでモックする設計です（news_nlp._call_openai_api, regime_detector._call_openai_api などを patch して振る舞いを制御できます）。
- DuckDB を :memory: モードで使うと高速にユニットテストを実行できます（init_audit_db(":memory:") など）。
- ETL や品質チェックは副作用があるためテスト用のサンプル DB を用意してから実行してください。

---

## ライセンス / 貢献

（この README のテンプレートにはライセンスや貢献ガイドを入れていません。実際のリポジトリでは LICENSE ファイルや CONTRIBUTING.md を追加してください。）

---

不明点や追加で README に載せたい運用手順（cron ジョブ例、監視設定、CI/CD、スキーマ定義ファイルの初期化方法など）があれば教えてください。README に追記して構築手順や運用ガイドを具体化します。