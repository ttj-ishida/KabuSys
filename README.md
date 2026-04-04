# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLP処理（OpenAI）、研究用ファクター計算、監査ログの初期化などを含みます。

---

## 概要

KabuSys は以下の機能を組み合わせて、取引戦略のデータ基盤および一部の分析／意思決定支援を提供します。

- J-Quants API からの日足・財務・カレンダー取得と DuckDB への保存（ETL）
- ニュース収集（RSS）と LLM を用いたニュースセンチメントのスコアリング
- ETF ベースの市場レジーム判定（MA と マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査（audit）スキーマの初期化／管理（発注・約定等のトレーサビリティ）

パッケージは `src/kabusys` 配下に実装されています。主要モジュールはデータ（data）、AI（ai）、リサーチ（research）、設定（config）などです。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策・正規化）
  - データ品質チェック（missing/duplicate/spike/future_date）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news: gpt-4o-mini を利用した銘柄ごとのスコア）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local の優先順）
  - 環境変数ラッパ（settings オブジェクト）

---

## 必要要件（目安）

- Python 3.10+
- 必要ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- OS: Linux / macOS / Windows（DuckDB 対応環境）

実行に必要な外部サービス:
- J-Quants API（JQUANTS_REFRESH_TOKEN）
- OpenAI API（OPENAI_API_KEY） — ai モジュールを使う場合
- kabuステーション API パスワード（KABU_API_PASSWORD） — 発注統合等で使用

---

## インストール（開発環境）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（必要に応じて requirements.txt を用意してください）
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨します。）

---

## 設定 (.env)

config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（一部）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL 実行時）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注統合で必要）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings は必須キーが未設定の場合 ValueError を投げます（例: JQUANTS_REFRESH_TOKEN は settings.jquants_refresh_token プロパティで _require が呼ばれます）。

---

## セットアップ手順（簡易）

1. .env を作成して必要なトークンを設定する。
2. 仮想環境内で依存パッケージをインストールする。
3. データベース用ディレクトリを作成（例: data/）。
4. DuckDB 接続を作って ETL / スキーマ初期化 を実行。

例: 監査用 DB の初期化
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db
# settings.duckdb_path は既定の path を返す (Path オブジェクト)
audit_conn = init_audit_db("data/audit.duckdb")
```

ETL 用の DuckDB 接続
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

---

## 使い方（主要な例）

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコアの作成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI キーは環境変数 OPENAI_API_KEY に設定するか api_key 引数で渡す
written_count = score_news(conn, target_date=date(2026,3,20))
print("scored:", written_count)
```

- 市場レジーム判定（1321 の MA200 とマクロセンチメント合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

- データ品質チェック（全チェック）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 注意点・設計方針（運用上のポイント）

- ルックアヘッドバイアス回避:
  - ai/regime_detector や news_nlp 等は内部で `date.today()` を直接参照しないよう設計され、関数呼び出し時に `target_date` を渡す形式です。バックテスト等で「当時点で利用可能なデータのみ」を再現しやすくなっています。
- .env 自動読み込み:
  - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます。テスト等でこれを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはリトライとフェイルセーフを備えています。API 失敗時にはゼロやスキップで継続する設計（例: マクロスコア失敗時は 0.0 を使用）。
- J-Quants API はレート制御とトークン自動リフレッシュ、ページネーション対応、保存時の冪等性（ON CONFLICT）を実装しています。
- DuckDB に対する executemany の制約（空リスト不可）や SQL の互換性に配慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

（パッケージベース: src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数管理、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント / score_news
  - regime_detector.py  — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理
  - news_collector.py   — RSS 取得・正規化・保存
  - quality.py          — データ品質チェック
  - stats.py            — zscore_normalize 等
  - audit.py            — 監査ログ（DDL・初期化）
- research/
  - __init__.py
  - factor_research.py  — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（上記に加え、モジュール内で多数のヘルパー関数・定数が定義されています）

---

## 開発・貢献

- テスト: 各モジュールは外部 API 呼び出しを抽象化しており、ユニットテスト時には HTTP / OpenAI 呼び出しをモックしやすく設計されています（内部呼び出し関数を patch して差し替え可能）。
- LLM 呼び出しは JSON Mode を利用し、レスポンスの厳密なパースとバリデーションを行っています。

---

必要であれば、README に以下を追加できます：
- 実行例のスクリプト（cron / systemd / Airflow 用）
- 依存関係の完全な requirements.txt
- スキーマ初期化（data.schema.init_schema 相当の手順）
- CI / テストの実行方法

どの追加情報が必要か教えてください。