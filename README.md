# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント）、研究用ファクター計算、監査ログ（約定トレーサビリティ）、スケジュール実行用ユーティリティなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株のデータ基盤と研究/実行レイヤーを支援するモジュール群です。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集と記事前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA と LLM 評価の合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
- データ品質チェックと監査ログ（監査テーブル初期化・管理）
- 設定は環境変数 / .env ファイル経由で管理（自動ロード機構あり）

設計上の重点:

- ルックアヘッドバイアス防止（内部での日付取得を明示的に渡す設計）
- 冪等性（DB 保存は ON CONFLICT 等で上書き）
- フェイルセーフ（外部 API 失敗時は部分的にフォールバック）
- DuckDB を主要なローカル DB として利用

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS の正規化、SSRF 対策、raw_news 保存）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF MA とマクロセンチメントの合成）
- research/
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数 / .env 自動読み込み、設定アクセス（settings オブジェクト）
- その他
  - audit（監査テーブル DDL と初期化）
  - news_collector（RSS 取得／前処理）

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（typing の | などを使用）
- 主要な Python パッケージ:
  - duckdb
  - openai
  - defusedxml

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発モードでインストールする場合（プロジェクトルートで）
pip install -e .
```

（プロジェクトに requirements.txt があればそれに従ってください）

---

## 環境変数 / 設定

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` ファイルから設定を自動読み込みします（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必要に応じて）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）

任意設定（デフォルトあり）:

- KABUSYS_ENV           : `development`, `paper_trading`, `live`（デフォルト development）
- LOG_LEVEL             : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`（デフォルト INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- PID_FILE_PATH         : 実行 PID ファイルパス（デフォルト `data/execution.pid`）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値

注意: settings オブジェクトを通じて設定値へアクセスできます。

例:

```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローンする（省略）
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（参考: `.env.example` がある想定）
   - 必須変数（JQUANTS_REFRESH_TOKEN など）を設定する
5. DuckDB ファイルやデータディレクトリを準備（`settings.duckdb_path` の親ディレクトリを作成）
6. 監査 DB を初期化する（任意）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な API 例）

以下は代表的な操作の例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...)）を受け取ります。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を計算して ai_scores に保存

```python
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"{count} 銘柄書き込み")
```

- 市場レジーム判定（1321 の MA200 とマクロニュース評価の合成）

```python
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- ファクター計算（研究用）

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

- 監査テーブルの初期化（既存 DB に対して）

```python
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 設定値の参照

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須（未設定時は ValueError）
print(settings.duckdb_path)
```

---

## よくある運用上の注意

- OpenAI 呼び出しはコストとレイテンシがかかります。API キーとレート制御を適切に設定してください。
- J-Quants API にはレート制限があるため jquants_client はスロットリングとリトライを内包しています。ID トークンの自動リフレッシュ機構があります。
- ETL / AI スコアリングは「target_date」を明示的に渡す設計のため、バックテストでのルックアヘッドバイアスを避けられます。日付は内部で自動取得されない点に留意してください。
- DuckDB に対する executemany の空リストは一部バージョンで問題になるため、実装は空チェックを行っています。DuckDB のバージョン互換性には注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数 / .env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py                # 銘柄別ニューススコア
    - regime_detector.py         # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch/save）
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     # 市場カレンダー管理
    - news_collector.py          # RSS 収集・前処理
    - quality.py                 # データ品質チェック
    - audit.py                   # 監査ログ DDL / 初期化
    - stats.py                   # zscore_normalize 等
    - etl.py                     # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         # モメンタム / バリュー / ボラティリティ
    - feature_exploration.py     # 将来リターン / IC / 統計サマリー
  - ai/                          # AI 関連（上記）
  - research/                    # 研究用モジュール（上記）

---

## 開発 / 貢献

- コードは単体テスト可能なように設計されており、外部 API 呼び出しや時間依存部分はモックしやすく作られています（内部で _call_openai_api や _urlopen を差し替え可能）。
- プルリクエストの際は下記を意識してください:
  - ルックアヘッドバイアスを導入しない（target_date を引数として扱う）
  - DuckDB とのトランザクション整合性を保つ（BEGIN/COMMIT/ROLLBACK）
  - 外部接続周りの障害に対するフェイルセーフを残す

---

## 参考 / 備考

- settings._require() は必須環境変数がない場合に ValueError を投げます。`.env.example` を参照して `.env` を作成してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を起点に行われます。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- README に記載の API 呼び出し例はライブラリの最小利用例です。実運用ではログ設定、例外監視、再試行ポリシーを追加してください。

---

不明点や README の追記希望（例: 実行用 CLI や systemd / supervisor 用の設定例、より詳しい .env.example のテンプレート等）があれば教えてください。必要に応じてサンプル .env.example や運用手順を追加します。