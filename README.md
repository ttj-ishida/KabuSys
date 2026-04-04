# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants）・ニュース収集・LLM を用いたニュースセンチメント評価・ファクター計算・監査ログなど、取引システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能群を備えた内部ライブラリ群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）の自動取得と DuckDB への冪等保存
- RSS ベースのニュース収集（SSRF 対策・正規化・前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）とマクロレジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（信号→発注→約定のトレース用）を DuckDB に初期化するユーティリティ
- 環境変数/設定管理（.env 自動読み込み、Settings オブジェクト）

設計方針として、バックテスト時のルックアヘッドバイアスを防ぐために
内部関数は明示的な target_date を受け取り、実行時の現在時刻へ直接依存しない実装が多くされています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（レートリミット・リトライ・トークンリフレッシュ対応）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss, preprocess_text, URL 正規化、SSRF 対策
  - 品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースの LLM スコアを合成し market_regime に書き込む
- research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings オブジェクト: 環境変数から各種設定を取得（J-Quants トークン、OpenAI、DB パス 等）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、CWD 非依存）

---

## 事前準備 / セットアップ

推奨: 仮想環境を作成して実行してください。

例（UNIX 系）:
```bash
python -m venv .venv
source .venv/bin/activate
```

依存パッケージ（代表例）:
- duckdb
- openai
- defusedxml

requirements.txt がない場合は手動でインストールしてください:
```bash
pip install duckdb openai defusedxml
```

パッケージを開発モードでインストールする場合（プロジェクトルートに setup/pyproject がある想定）:
```bash
pip install -e .
```

環境変数設定:
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュール）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数一覧（主に settings で参照される）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD : kabu ステーション API パスワード（発注関連）
- KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視データ）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・プロセス管理）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-xxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は主要ユースケースの呼び出し例です。実行には適切な環境変数・DB スキーマ（必要なテーブル）が整っていることを想定します。

1) Settings の利用:
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)
```

2) DuckDB 接続と日次 ETL の実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別 ai_scores 生成）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn: duckdb.DuckDBPyConnection, target_date: date 型
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"written: {n_written}")
```

4) 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

5) 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーンに設定されます
```

6) RSS フィード取得（ニュース収集一部）:
```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    text = preprocess_text(a["title"] + " " + a["content"])
    print(a["id"], a["datetime"], text[:200])
```

7) 研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# mom は各銘柄の辞書リスト（date, code, mom_1m, mom_3m, ...）
```

---

## 環境変数と .env の細かい挙動

- config モジュールはパッケージのファイル位置からプロジェクトルート（.git または pyproject.toml）を探索し、ルート下の `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - `.env.local` は `.env` を上書きする（override=True）
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- settings のプロパティは環境変数を検証して返します（例: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか）。

---

## ディレクトリ構成（主なファイル）

以下はこの README にあるコードベースに基づく主要なディレクトリ・ファイル構成です（省略あり）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（zscore_normalize は data.stats から再利用）
- その他:
  - .env.example（プロジェクトルートに想定される雛形ファイル）

各モジュールの責務（簡易まとめ）:
- config.py: 環境変数のパース、Settings オブジェクト
- jquants_client.py: J-Quants API 呼び出し、保存関数（save_*）
- pipeline.py / etl.py: 日次 ETL パイプライン
- news_collector.py: RSS 取得・前処理・SSRF 対策
- news_nlp.py / regime_detector.py: OpenAI を用いたスコアリング（ニュース・マクロ）
- research/*: ファクター計算・特徴量分析
- audit.py: 発注・約定の監査ログスキーマ初期化

---

## 注意点 / 運用上のポイント

- OpenAI・J-Quants など外部 API のキーは厳重に管理してください（.env は .gitignore へ）。
- LLM 呼び出しはレート制限や費用が発生します。batch サイズや retry ロジックを理解した上で運用してください。
- ETL は差分取得＋バックフィル（デフォルト 3 日）を行います。初期ロード時は開始日を指定するか、十分な過去日付のデータ取得を想定してください。
- DuckDB のバージョン差異により executemany の挙動（空リスト不可等）があるため、コードはそれらを考慮していますが、運用環境の DuckDB バージョンでの動作確認を推奨します。
- ニュース収集では SSRF 対策（ホストのプライベートチェック、リダイレクト検査）・受信サイズ制限等を実装済みです。

---

## 貢献・開発

- テスト: 各モジュールは外部 API 呼び出し箇所を関数分離しており、ユニットテストでは該当関数をモックする設計になっています（例: news_nlp._call_openai_api を patch）。
- ローカル開発の際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、テスト用の環境変数注入を行うと便利です。

---

必要であれば、README に例となる .env.example、requirements.txt、簡易起動スクリプト（ETL の cron ジョブ例、監視スクリプト）を追加で作成します。どの部分を拡張したいか教えてください。