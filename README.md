# KabuSys

日本株の自動売買・データ基盤ライブラリ群（モジュール群）。  
データ取得（J-Quants）、ETL、品質チェック、ニュース/NLP による銘柄センチメント算出、レジーム判定、リサーチ用ファクター計算、監査ログなどを含むバックエンドコンポーネント群です。

主な目的:
- J-Quants からのデータ差分 ETL と品質チェック
- ニュース収集・NLP による銘柄ごとの AI スコア生成
- 市場レジーム判定（移動平均乖離 + マクロセンチメント）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注〜約定をトレースする監査ログスキーマ

注: これはライブラリ/フレームワークレイヤーであり、実際の運用では外部プロセス（ジョブスケジューラ、発注ブローカーラッパー等）と組み合わせて使用します。

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須値チェック、環境（development / paper_trading / live）やログレベル判定

- データプラットフォーム（kabusys.data）
  - J-Quants クライアント（認証、取得、保存、レート制御、リトライ）: fetch/save 関数群
  - ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS パーシング、SSRF 対策、前処理）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（audit）: 発注・約定トレーサビリティ用スキーマ初期化、専用 DB 初期化ユーティリティ

- AI モジュール（kabusys.ai）
  - ニュース NLP（銘柄ごとのセンチメント算出）: score_news
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント）: score_regime

- 研究モジュール（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化ユーティリティ

---

## 必要条件

- Python 3.10+
  - typing の `X | Y` 構文を利用しているため 3.10 以上を想定
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリを多用、追加はプロジェクト側で管理してください）

インストールはプロジェクトの pyproject.toml / requirements.txt に基づいて行ってください。開発環境で手早く試すには例:

```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
pip install -e .
```

（実際のメタデータはプロジェクト配布に依存します）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境を作成し依存をインストール（上記参照）
3. .env をプロジェクトルートに作成して環境変数を設定（下記参照）
4. DuckDB ファイルや監査用 DB の初期化（必要に応じて）

重要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（発注等で使用）
- OPENAI_API_KEY — OpenAI を使う処理（news_nlp, regime_detector）で必要
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- KABUSYS_ENV — execution 環境: development / paper_trading / live
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM 閾値など

例 .env（プロジェクトルート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードを無効化する場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（抜粋）

以下はライブラリ利用の簡単な例です。実際はアプリケーション側でジョブ化（cron / scheduler）して使います。

- DuckDB 接続の作成と ETL の実行:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH から決まる
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアの取得（OpenAI API 必須）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

- 市場レジームスコア算出:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用 DuckDB を新規作成）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親フォルダがなければ自動作成
# これで監査テーブルが作られる
```

- 市場カレンダー関連:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- AI モジュールは OpenAI API を呼び出すためネットワーク・料金が発生します。テスト時は該当関数をモックしてください（モジュール内でパッチ可能な内部関数が用意されています）。
- run_daily_etl 等は内部で calendar ETL → prices ETL → financials ETL → 品質チェックを順に実行します。外部 API 呼び出しは try/except で個別にハンドリングしますが、環境変数（JQUANTS_REFRESH_TOKEN など）は必須です。

---

## ディレクトリ構成（主要部分）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py          — パッケージ情報
  - config.py            — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースNLP (score_news)
    - regime_detector.py — 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save）
    - pipeline.py         — ETL パイプラインと run_daily_etl
    - etl.py              — ETL インターフェース再エクスポート
    - stats.py            — zscore_normalize 等統計ユーティリティ
    - quality.py          — データ品質チェック
    - market_calendar.py? — カレンダー管理（calendar_management.py）
    - calendar_management.py — 市場カレンダー管理、calendar_update_job 他
    - news_collector.py   — RSS 収集・前処理・保存ロジック
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (参考: README には未含まれるがパッケージ公開時に存在可能)
  - execution/ (参考: 実行 / 発注関連モジュールが想定される)

上記は実装ファイルから抽出した主要モジュールを示しています。

---

## テスト・開発時のヒント

- 自動 env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出しや外部 API 呼び出しはユニットテストではモックしてください。モジュール内の _call_openai_api などを patch する設計になっています。
- DuckDB による executemany の空リストバインドなど、バージョン差異に注意してください（コード内に互換性処理あり）。

---

## 補足

この README はコードベースの実装を元にした概要・利用ガイドです。実際の運用時には以下を確認してください:

- pyproject.toml / requirements.txt の依存関係と Python バージョン
- 実行環境（ジョブスケジューラ、コンテナ、セキュリティポリシー）
- API キーの安全な保管・ローテーション、ログの取り扱い（個人情報や秘密情報の出力に注意）

ご要望があれば、インストール用の具体的な requirements.txt、サンプル .env.example、または各モジュールの API リファレンス（関数/引数一覧）を出力します。