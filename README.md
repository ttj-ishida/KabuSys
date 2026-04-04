# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants API からのデータ ETL、ニュース NLP（OpenAI を使用したセンチメント解析）、市場レジーム判定、研究用ファクター計算、監査ログ用スキーマなどを提供します。

主な目的は「データ収集 → 品質チェック → 特徴量算出 → シグナル生成 → 発注／監査」という自動売買プラットフォームの基盤機能をモジュール化して提供することです。

---

## 主な機能（抜粋）

- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、JPX カレンダーを差分取得し DuckDB に保存
  - 差分更新・バックフィル（後出し修正吸収）・ページネーション対応
  - 保存は冪等（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損（OHLC）検出、日付整合性、主キー重複、スパイク検出などを実施
  - 問題は QualityIssue リストで返却（error / warning）

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、XML パース防御）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores テーブルへ保存）
  - ニュースウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（DB 比較は UTC naive）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で regime を判定（bull / neutral / bear）

- 研究用モジュール
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算、IC（Spearman）計算、ランキング、Z スコア正規化、統計サマリ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions など監査用テーブルを作成する DDL と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化

- 設定管理
  - .env/.env.local の自動読み込み（優先度: OS env > .env.local > .env）
  - 必須環境変数の明示的チェック
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 管理

---

## 必要条件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他: 標準ライブラリの urllib, json 等

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトがパッケージ化されている場合）
   - pip install -e .

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（読み込みは .git または pyproject.toml を基準に判定）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード（発注連携を使う場合）
- OPENAI_API_KEY (必須/または関数引数で渡す): OpenAI の API キー（ニュース NLP / レジーム判定で使用）

任意 / デフォルト:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な API）

ここではプログラムから使う基本例を示します。すべての関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- 日次 ETL（カレンダ・株価・財務・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定可能）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡しても可
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（監査用テーブルを作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

- 研究用ファクター計算の例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, target_date=date(2026,3,20))
v = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

注意点・補足:
- OpenAI 呼び出しは内部で retry/backoff を行いますが、テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えることが想定されています。
- ニュースの時間ウィンドウや ETL の挙動は look-ahead bias を避ける設計になっています（内部で datetime.today() などを直接参照しない関数設計）。
- DuckDB の executemany に関してバージョン差異に注意（コード内で回避策あり）。

---

## よく使うモジュール（概要）

- kabusys.config: 環境変数・設定管理（.env 自動読み込み / 必須チェック / パス等）
- kabusys.data:
  - jquants_client: J-Quants API クライアント（取得 / 保存関数）
  - pipeline: ETL 実行（run_daily_etl など）
  - quality: データ品質チェック群
  - news_collector: RSS 収集ユーティリティ
  - calendar_management: 市場カレンダー管理（is_trading_day 等）
  - audit: 監査ログ用 DDL / 初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai:
  - news_nlp.score_news: 銘柄ニュースの AI スコアリング
  - regime_detector.score_regime: 市場レジーム判定
- kabusys.research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（抜粋）

（プロジェクトのソースツリーは src/kabusys 以下に配置されています。主要ファイルを抜粋）

- src/
  - kabusys/
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
      - etl.py
      - quality.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - etl.py
      - ...（その他モジュール）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...（研究用ユーティリティ）
    - ai/ (上記)
    - research/ (上記)
    - monitoring/（監視用モジュールは __all__ に含まれていますが、必要に応じて参照してください）

---

## ロギング / 実行モード

- KABUSYS_ENV: "development" / "paper_trading" / "live"（settings.env で取得。無効な値は例外）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

---

## テスト・開発者向けメモ

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。ユニットテスト等で自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI・HTTP 呼び出し関係はモックしやすいよう内部呼び出し関数を分離して実装されています（例: news_nlp._call_openai_api を patch）。
- DuckDB の挙動や executemany の制約を考慮した実装がなされています。DuckDB のバージョン差異がある場合は注意してください。

---

以上が README.md の内容です。追加で「セットアップ用の requirements.txt」「.env.example」「簡単な CLI 実行スクリプト（run_etl.py 等）」を作成する場合は、そのテンプレートも用意できます。必要なら教えてください。