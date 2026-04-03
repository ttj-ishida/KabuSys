# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、そして実行・監視のためのユーティリティ群を提供します。

主な設計方針
- ルックアヘッドバイアス防止（バックテストでの誤った未来参照を避ける）
- DuckDB を中心としたローカルデータ保存と冪等（idempotent）処理
- 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- セキュリティ考慮（RSS の SSRF 防止、XML パースの安全化等）

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` 自動読み込み（無効化可）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）

- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション対応）
  - 差分取得とバックフィル機能
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集・NLP
  - RSS からニュース収集（URL 正規化、トラッキング削除、SSRF 対策）
  - OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai_scores へ保存）
  - マクロニュースと ETF MA200 乖離を合成した市場レジーム判定

- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility など）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化

- 監査（Audit）テーブル
  - シグナル → 発注要求 → 約定までを UUID 階層でトレース可能にするスキーマと初期化関数

- その他
  - LINE 通知用の設定（トークンを環境変数で管理）
  - 実行監視設定（PID ファイル、キルフラグ、CPU/Memory/Disk 閾値）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントに `|` 演算子等を利用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API など）

必要なパッケージはプロジェクトに応じて requirements を用意してください。最低限のインストール例:

pip install duckdb openai defusedxml

（実運用ではバージョン固定の requirements.txt や Poetry を使うことを推奨します）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) ：J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) ：kabuステーション API パスワード
- OPENAI_API_KEY ：OpenAI API キー（news_nlp / regime_detector で利用）
- KABUSYS_ENV ：環境 ("development" / "paper_trading" / "live"), デフォルト "development"
- LOG_LEVEL ："DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- DUCKDB_PATH ：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH ：監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト時に便利）

.env / .env.local の自動読み込みは、プロジェクトルート（.git や pyproject.toml を基準）を探して行われます。

---

## セットアップ手順（開発環境の例）

1. リポジトリをチェックアウト

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定

5. DuckDB 等のディレクトリを作成（必要なら）
   - mkdir -p data

6. （任意）監査 DB を初期化
   - 下記「使い方」を参照

---

## 使い方（主要 API の例）

以降の例では Python スクリプト / REPL からの呼び出しを示します。

- 共通準備（DuckDB 接続・設定読み込み）:

from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:

from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースのセンチメントスコアを算出（OpenAI 必要）:

from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を使う

- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの合成）:

from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算・研究系ユーティリティ:

from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))

# 将来リターン例
fwd = calc_forward_returns(conn, target_date=date(2026, 3, 20), horizons=[1,5,21])

# IC 等の解析は関数を組み合わせて使用

- 監査（Audit）スキーマの初期化:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# またはインメモリ:
# audit_conn = init_audit_db(":memory:")

- J-Quants トークン取得（低レベル）:

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用

---

## 実装上の注意点 / 補足

- Look-ahead バイアス対策
  - 多くの関数は date や target_date を明示的に受け取り、内部で date.today() 等に依存しないよう設計されています。

- 冪等性
  - ETL の保存処理は ON CONFLICT DO UPDATE を用いて重複挿入に耐性があります。

- 外部 API とエラー処理
  - J-Quants クライアントや OpenAI 呼び出しはリトライ・バックオフやレート制限（J-Quants: 120 req/min）制御を実装しています。
  - LLM 呼び出し失敗時はフェイルセーフとしてゼロやスキップを返す設計の箇所が多くあります（サービスの可用性を考慮）。

- セキュリティ
  - RSS フィード取得は SSRF 対策、最大応答サイズ制限、defusedxml を用いた安全な XML パースを行っています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py            — ニュースの NLU / OpenAI 補助関数（ai_scores 書込）
  - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - news_collector.py      — RSS 収集 / raw_news 保存
  - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py               — 汎用統計（zscore_normalize）
  - audit.py               — 監査ログ（監査テーブル定義 + 初期化）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- research/...             — 上記モジュール群

ドキュメント / 設計仕様は各モジュールの docstring 内に要点が記載されています。

---

## 開発・運用上の推奨

- 本番環境では KABUSYS_ENV を "live" に設定し、発注ロジック・実行制御を厳密にテストすること。
- OpenAI を使う機能は API コストとレイテンシに注意。batch サイズや retry 戦略は実運用に合わせて調整してください。
- ETL はスケジュール（夜間バッチ）での定期実行を想定しています。run_daily_etl を cron / Airflow 等から呼ぶ運用が簡便です。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動ロードを止められます。OpenAI 呼び出しはモック化して単体テストを行ってください。

---

README の補足やサンプルスクリプト、CI 用のテスト実装などが必要でしたら、用途に合わせたサンプルを追加で作成します。どの部分を重点的に見たいか教えてください。