# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・AIによるニュースセンチメント評価、ファクター計算、監査ログ（取引フローのトレーサビリティ）などを含みます。

主な設計思想：
- ルックアヘッドバイアスを避けるため、日時は明示的に渡す設計（内部で date.today() を多用しない）
- DuckDB をデータ層に利用し、ETL は冪等（ON CONFLICT）で安全に実行
- 外部 API には堅牢なリトライ・レート制御を実装（J-Quants / OpenAI）
- テスト容易性のため設定は .env / 環境変数から読み込み可能（自動ロード機能あり）

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード、必須変数チェック（kabusys.config）
- データ ETL（J-Quants）
  - 株価日足、財務データ、JPX カレンダーの差分取得・保存（kabusys.data.pipeline / jquants_client）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS 収集、SSRF 対策、前処理、raw_news への冪等保存（kabusys.data.news_collector）
- AI（OpenAI）関連
  - ニュース NLP（銘柄別センチメント → ai_scores に保存）: score_news（kabusys.ai.news_nlp）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）: score_regime（kabusys.ai.regime_detector）
- リサーチ / ファクター分析
  - Momentum / Value / Volatility 等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ（kabusys.data.audit）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize など）
  - 市場カレンダー管理（is_trading_day 等）

---

## 必要条件

- Python 3.10 以上（型注釈に PEP 604 の `|` を使用）
- DuckDB
- OpenAI Python SDK
- defusedxml

例（最低限の依存パッケージ）:
pip install duckdb openai defusedxml

README 内のサンプルは上記パッケージがインストール済みであることを前提としています。

---

## セットアップ手順

1. リポジトリをクローン（あるいはソースを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動読み込みされます（kabusys.config が .git / pyproject.toml を基にプロジェクトルートを探索して読み込み）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

推奨する .env の例（必要に応じて設定）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabu API（kabuステーション）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# LINE（通知等で使用する場合）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# DB パス等
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# 環境・ログレベル
KABUSYS_ENV=development         # development | paper_trading | live
LOG_LEVEL=INFO
```

必須（ライブラリ関数を使う際に ValueError が出る場合）:
- JQUANTS_REFRESH_TOKEN（ETL / jquants_client）
- OPENAI_API_KEY（score_news / score_regime を使う場合）または関数引数で API キーを渡す

---

## 使い方（主要なユースケースの例）

以下はライブラリ内部 API を直接呼ぶサンプルです。実運用向けにはラッパースクリプトや CLI を用意してください。

- DuckDB 接続を作る（デフォルトのパスは settings.duckdb_path）:
```
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます（ただし設計上は明示的に渡すこと推奨）
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

- ニュースセンチメントを算出し ai_scores に保存:
```
from datetime import date
from kabusys.ai.news_nlp import score_news

# 明示的に OpenAI API キーを渡すことも可能
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written_count}")
```

- 市場レジーム判定（market_regime テーブルに書き込み）:
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DB を初期化（監査専用 DB を別に作る場合）:
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 order_events / order_requests / executions などを使用
```

- ファクター計算（例: モメンタム）:
```
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors は dict のリスト (各要素に "code" / "mom_1m" 等を含む)
```

- データ品質チェック:
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意:
- OpenAI 呼び出しは API キーの設定が必要（env OPENAI_API_KEY か関数引数）。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN が必要（get_id_token が参照）。

---

## 実行時のヒント / 注意点

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テストや CI で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しではリトライ・フェイルセーフが実装されています。API エラー時には一部処理がスキップされることがあります（0.0 のスコアでフォールバックなど）。
- DuckDB の executemany は一部バージョンで空リストを受け付けない実装制約を考慮したコードになっています。
- ネットワークの安全性（news collector）を重視し、SSRF対策・リダイレクト検査・最大応答サイズ制限を実装しています。

---

## ディレクトリ構成

主要なモジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（銘柄別）
    - regime_detector.py             — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py              — RSS ニュース収集、前処理
    - calendar_management.py         — 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py                     — データ品質チェック
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — forward returns, IC, summary, rank
  - ai/, data/, research/ 以下にさらに細かい実装が含まれます。

（ソースは src/kabusys 以下に配置。パッケージ化して使う想定です）

---

## 開発 / テスト

- 自動ロードされる .env を利用しているため、テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して環境の注入を制御するのが便利です。
- OpenAI / J-Quants を呼ぶコードは外部呼び出しを含むため、ユニットテストでは該当関数（例: _call_openai_api, _urlopen, _request など）をモックしてください。コードはモック差し替えを想定した設計になっています（関数の docstring にその旨の記載あり）。
- DuckDB はインメモリ ":memory:" を利用できるため、テスト用の DB 初期化が容易です。

---

## ライセンス・免責

本 README はソースコードの説明に基づく概要です。実運用する場合は API トークンや資金管理、安全性（注文の二重送信防止、例外処理）など十分に検討してください。取引に関しての責任は利用者にあります。

---

必要があれば、README に CLI 利用例や具体的な .env.example ファイル、よくあるトラブルシュート（OpenAI レート制限、J-Quants 401 リフレッシュ失敗時の対処など）を追記します。どの情報を優先して追加しましょうか？