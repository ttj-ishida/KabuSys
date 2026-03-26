# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュースNLP / LLM を用いたセンチメント評価、研究用ファクター計算、監査ログ等の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤向けのモジュール群です。主な目的は次の通りです。

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL（差分更新・バックフィル対応）
- RSS ベースのニュース収集と OpenAI（LLM）を用いた銘柄別/マクロのセンチメント算出
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- 市場レジーム判定（ETF + マクロニュースの合成スコア）
- 監査ログ（signal → order → executions）用のスキーマ生成ユーティリティ
- データ品質チェック、マーケットカレンダー管理、ニュース収集の堅牢実装

設計上の特徴：
- DuckDB をデータ層に採用（軽量かつ高速な列指向 DB）
- Look-ahead バイアス対策（日時参照を明示的受け渡し、ETL の差分/バックフィル等）
- 外部 API 呼び出しにリトライ／バックオフ、フェイルセーフの実装
- 冪等操作（DB への保存は ON CONFLICT 等で上書き）と監査ログの追跡可能性

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save の実装、トークン自動リフレッシュ、レートリミット）
  - マーケットカレンダー管理（is_trading_day 等）
  - ニュース収集（RSS 取り込み、SSRF / Gzip / サイズ制限対応）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）：銘柄別 ai_scores 生成（OpenAI）
  - 市場レジーム判定（score_regime）：ETF 200日MA乖離 + マクロニュース LLM を合成
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（.env 自動読み込み、必須変数チェック、設定オブジェクト settings）

---

## 動作環境 / 前提

- Python 3.10 以上（型アノテーションに新しい union 表記などを使用）
- 必要ライブラリ（主な例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリのみで実装されている箇所が多いですが、ネットワーク処理や JSON 等を使います

（実際の packaging / requirements はプロジェクト側で管理してください）

---

## セットアップ手順（概要）

1. Python と依存ライブラリをインストール
   - 例（仮想環境推奨）:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb openai defusedxml

   - 開発インストール（パッケージとして提供されている場合）:
     - pip install -e .

2. 環境変数の準備
   - プロジェクトルートの `.env` / `.env.local` に必要な値を設定できます。自動ロードは config モジュールが行います（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使う）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャネル ID
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携がある場合）
   - OpenAI を使う場合:
     - OPENAI_API_KEY 環境変数（score_news / score_regime で None を渡した場合に参照）
     - または score_news(..., api_key="...") のように明示的に渡す

   - 任意の設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)

3. データベース準備
   - デフォルトでは DuckDB ファイルは data/kabusys.duckdb に保存されます（settings.duckdb_path）。
   - 監査ログ専用 DB を初期化する場合は data/audit.duckdb 等を指定して init_audit_db を呼び出します（親ディレクトリ自動作成）。

---

## 使い方（主要なエントリポイント・コード例）

以下は最小限の使用例（Python スクリプト／REPL）です。

- DuckDB 接続と ETL 実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を用いたニューススコア（銘柄別 ai_scores 生成）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written {n_written} codes")
```

- 市場レジーム判定（ETF + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境に設定するか api_key を渡す
```

- 監査ログスキーマの初期化（別DBに監査専用を作る）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/monitoring_audit.duckdb")
# 以降 conn_audit を使って監査ログを書き込む
```

- マーケットカレンダーの確認ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- score_news / score_regime は OpenAI API を使うため、API キーと利用料が必要です。API エラー時はフェイルセーフ（スコア 0 等）で継続する設計です。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token を通じて取得されます）。

---

## 設定（環境変数・.env）

config.Settings からアプリ設定を参照できます。主なプロパティと対応する環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB の保存先パス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順は OS 環境変数 > .env.local > .env です（.env.local が .env を上書き）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の書式は一般的な KEY=VALUE を想定しておりコメント行やクォート、export プレフィックスに対応します。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール構成（提供されたファイル群に基づく）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン / run_daily_etl 等
    - etl.py                         — ETLResult エクスポート
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore）
    - audit.py                       — 監査ログスキーマの初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー

---

## 開発上の注意 / 実運用での留意点

- OpenAI / J-Quants の API 呼び出しは利用料・レート制限の対象です。ローカルでのテスト時はキーの取り扱いに注意してください。
- ETL の差分ロジックやニュースウィンドウは「ルックアヘッドバイアス」を避けるため設計されています。ターゲット日を明示して処理を行ってください。
- DuckDB の executemany に空リストを与えるとエラーになるバージョンがあるため、関数内で空チェックを行う実装になっています。
- 監査ログスキーマは削除を前提としない設計です。運用でのデータ保持方針を検討してください。

---

## サポート / 貢献

- バグ報告や改善提案、テストケースは Issue または Pull Request を送ってください。
- 外部 API の呼び出し部分（ネットワーク）についてはモックしやすい設計を意識しています。ユニットテストでは該当関数を patch して挙動を検証してください。

---

この README はコードベース内の実装（コメント・docstring）を要約して作成しています。詳細な API 仕様や DB スキーマは各モジュールの docstring / 関数コメントを参照してください。