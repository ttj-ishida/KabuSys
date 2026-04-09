# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
このリポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）など、トレーディングシステムのコア機能をモジュール単位で提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価（日次OHLCV）、財務データ、JPX カレンダー取得（pagination / rate limit / token refresh 対応）
  - 差分更新・バックフィル対応の日次 ETL パイプライン（run_daily_etl）
  - データ保存（DuckDB）と冪等保存（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース処理 / NLP
  - RSS 取得・前処理・raw_news への保存（SSRF 対策、XML 安全パース）
  - OpenAI を使った銘柄単位のニュースセンチメントスコア生成（score_news）
  - マクロニュースと ETF (1321) の MA200乖離を合成した市場レジーム判定（score_regime）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - すべての操作を追跡可能なトレーサビリティ設計
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、Z スコア正規化など

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上を推奨（型注釈に union 型等を使用）
- DuckDB（Python パッケージ）、openai、defusedxml 等の依存をインストール

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo-directory>
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

2. 依存パッケージをインストール（例）
```bash
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用に以下も入れておくと便利
pip install pytest
```

※ pyproject.toml / requirements.txt がある場合はそちらに従ってください。パッケージ配布があれば `pip install -e .` で編集可能インストールが可能です。

3. 環境変数を設定
プロジェクトは .env / .env.local を自動ロードします（ルートに .git または pyproject.toml を置くことで自動検出）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須のもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合は必須）
- KABU_API_PASSWORD: kabuステーション API を利用する場合に必要

任意・デフォルト値あり
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）

.env 例（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なエントリポイント・例）

まず DuckDB 接続を作成してから各ユーティリティを呼び出します（in-memory やファイル DB どちらも可）。

- 日次 ETL を実行する（データ取得 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ユーティリティ（例: モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト（mom_1m, mom_3m, mom_6m, ma200_dev 等）
```

---

## 開発上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス回避:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照しません。target_date を引数で明示する設計です。
  - データ取得・集計は target_date 未満や <=/>= の条件を慎重に扱っています。
- 冪等性:
  - DB への保存は可能な限り ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を用いて冪等化しています。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）での一部失敗は例外を投げずにフォールバック（0.0 やスキップ）して全体処理を続行する設計箇所があります（ログ出力あり）。
- テスト容易性:
  - OpenAI 呼び出しや URL open などは内部関数をモック可能に実装してあり、unit テストで差し替えられるようになっています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と概要です。

- kabusys/
  - __init__.py (パッケージ定義、version)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメントスコア生成)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ユーティリティ)
    - pipeline.py (ETL パイプライン: run_daily_etl, run_prices_etl 他)
    - etl.py (ETL の公開インターフェース / ETLResult re-export)
    - news_collector.py (RSS 取得・前処理・保存)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - calendar_management.py (市場カレンダー処理・営業日判定)
    - audit.py (監査ログ DDL / 初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム / ボラティリティ / バリュー計算)
    - feature_exploration.py (forward returns / IC / factor summary / rank)
  - ai/ (ニュース / レジーム検出)
  - research/ (ファクター計算・解析)

（上記は抜粋です。実際のリポジトリにはさらに細かいモジュールやユーティリティが含まれます。）

---

## よくあるトラブルと対処

- .env が読み込まれない:
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に探します。テスト等でこれを停止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や J-Quants の認証エラー:
  - 環境変数に正しいキー/トークンが設定されているか確認してください。jquants の場合は JQUANTS_REFRESH_TOKEN（このライブラリは自動で id_token を取得します）。
- DuckDB のスキーマ未作成:
  - `init_audit_db` などの初期化関数で必要テーブルを作成するユーティリティを提供しています。ETL 実行前にスキーマが必要な場合は該当スキーマ初期化関数を呼んでください。

---

## ライセンス・貢献

- （ここにプロジェクトのライセンスやコントリビュート手順を記載してください）

---

必要であれば、README に例となる .env.example、requirements.txt、CI（GitHub Actions）やスケジューリング（cron / systemd / Airflow）についての設定例も追記できます。どの情報を優先して追加しましょうか？