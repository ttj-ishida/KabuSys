# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（部分実装）

このリポジトリは日本株のデータ収集・ETL・品質管理・ファクター計算・AI ニュースセンチメント・監査ログなど、アルゴリズム取引プラットフォームのバックエンド機能群を提供します。主要な処理は DuckDB をデータ層に使い、J‑Quants API／RSS／OpenAI（LLM）を外部データソースとして利用します。

---

## 主要機能（抜粋）

- ETL パイプライン
  - J‑Quants からの株価（OHLCV）・財務データ・マーケットカレンダーの差分取得と保存（冪等）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- データ層ユーティリティ
  - DuckDB 用の保存/初期化ユーティリティ（監査ログ初期化など）
  - マーケットカレンダー管理（営業日の判定、next/prev 等）
- ニュース収集 & NLP
  - RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI を用いたニュースごとの銘柄センチメント集約（ai_scores テーブルへ保存）
  - マクロニュース + MA200 を用いた市場レジーム判定（bull/neutral/bear）
- リサーチ（ファクター計算）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（オーダー/シグナル/約定のトレーサビリティ）
  - 信頼性の高い監査テーブル群のスキーマ作成・初期化
- 設定管理
  - .env / 環境変数読み込み（自動ロード機能、上書き・保護ロジック）

---

## 必要環境 / 依存

最低限必要な Python パッケージ（代表例）：
- duckdb
- openai
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt を参照してください。なければ上記を個別にインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを editable インストールできる場合
pip install -e .
```

---

## 環境変数 / 設定

kabusys は環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動読み込みはデフォルト ON です（プロジェクトルートは `.git` または `pyproject.toml` を探索して決定）。

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL で use）
- KABU_API_PASSWORD (必須)
  - kabuステーション（発注 API）用のパスワード
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI API を使う関数（score_news / score_regime 等）で使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)
  - LINE 通知を使う場合
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視用途など（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE (任意)
  - paper trading の fill モード: instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH (任意)
  - Paper trading 用 SQLite DB パス（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等
  - 実行監視関連設定
- KABUSYS_ENV (任意)
  - environment: development | paper_trading | live
- LOG_LEVEL (任意)
  - DEBUG|INFO|WARNING|ERROR|CRITICAL

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .          # pyproject があれば
   # または個別インストール
   pip install duckdb openai defusedxml
   ```

3. 環境変数の用意
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - OpenAI キーや J‑Quants リフレッシュトークンは必須（AI/ETL 機能を使う場合）。

4. データディレクトリ作成
   ```bash
   mkdir -p data
   ```

5. DuckDB 等の初期化（監査 DB を使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は各主要 API の簡単な使用例です。実行は Python プロセスやスクリプトから行います。

- 日次 ETL を実行（prices / financials / calendar を差分更新）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア生成（OpenAI API キー必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数で設定するか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ関数の利用例（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- OpenAI 呼び出しを行う関数（score_news, score_regime 等）は api_key 引数でキーを直接渡すことができます。渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- 各関数はルックアヘッドバイアスを避けるように設計されています（target_date を明示的に渡すことを推奨）。

---

## ディレクトリ構成（主要ファイル）

（提供されたコードベースに基づく抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数処理・Settings クラス（自動 .env 読込ロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースをまとめて OpenAI に送り、ai_scores に書き込むロジック
    - regime_detector.py
      - MA200 とマクロニュースの LLM 結果を合成して market_regime を算出
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py
      - 日次 ETL の主要処理（run_daily_etl 等）
    - etl.py
      - ETLResult を再エクスポート
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合など）
    - news_collector.py
      - RSS 取得・前処理・保存ロジック（SSRF 対策等）
    - calendar_management.py
      - market_calendar を参照した営業日ロジック、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム、バリュー、ボラティリティ等の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等

（上記は一部抜粋です。各モジュール内に詳細実装と設計方針のドキュメント文字列が含まれています。）

---

## 開発 / テストに関するヒント

- settings モジュールは自動で .env を読み込みます。ユニットテストで自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J‑Quants 呼び出し部分は外部 API と通信するため、ユニットテストではモック（patch）することを推奨します。モジュール内の `_call_openai_api` / _urlopen / _request などを差し替えられるよう設計されています。
- DuckDB を使った関数はインメモリ DB（":memory:"）でも動作するものが多く、テストが容易です。

---

## 貢献 / 連絡

README に記載のない改善提案やバグレポートは issue を作成してください。コードコメントや docstring にも設計意図を残していますので、機能拡張時はそちらも参照してください。

---

以上。開発者向けに主要機能と使い方をまとめました。追加で「セットアップの自動化」「CI 設定」「サンプル DB 初期化スクリプト」などの追記が必要であればお知らせください。