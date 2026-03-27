# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、ファクター計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（注文→約定のトレーサビリティ）などを統合的に提供します。

バージョン: 0.1.0

---

## 主な特徴（概要）

- J-Quants API から株価（OHLCV）、財務、マーケットカレンダーを差分取得し DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントによる市場レジーム判定
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ）と特徴量探索ユーティリティ
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- 設定は環境変数（.env、自動読み込み対応）で管理

---

## 機能一覧（代表）

- data.jquants_client
  - J-Quants からのデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info）
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - 認証トークン取得（get_id_token）・レート制御・リトライ処理を含む
- data.pipeline
  - 日次 ETL 実行（run_daily_etl）および個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETLResult データクラスによる実行結果報告
- data.news_collector
  - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策・サイズ制限）
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- data.calendar_management
  - 営業日判定 / 前後営業日の検索 / カレンダー更新ジョブ
- data.audit
  - 監査ログテーブルの DDL と初期化（init_audit_schema / init_audit_db）
- ai.news_nlp
  - ニュースの銘柄別センチメントスコア算出（score_news）
- ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントを合成した市場レジーム判定（score_regime）
- research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize など

---

## 必要な環境変数

以下は本プロジェクトで使用される主要な環境変数です（最低限必要なものは README のセットアップ参照）。

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます（優先度: OS 環境変数 > .env.local > .env）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の書式は通常の KEY=VALUE を想定し、export 形式やクォート、コメント等も簡易にサポートします。

---

## セットアップ手順（開発環境向け）

1. レポジトリをクローン、プロジェクトルートに移動

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なライブラリ（例）
     - duckdb
     - openai
     - defusedxml
     - (標準ライブラリ以外のパッケージは実際の pyproject/requirements を参照してください)
   - 例:
     pip install duckdb openai defusedxml

   ※ プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使ってください。

4. 環境変数の設定
   - ルートに `.env.example` を用意している場合は `.env` を作成して値を入力してください（なければ環境変数を直接設定）。
   - 重要なキー:
     - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY, KABU_API_PASSWORD

5. データディレクトリ作成（必要なら）
   - mkdir -p data

6. DuckDB 初期化（監査 DB を使う場合の例）
   - 以下の Python スニペットで監査 DB を初期化できます（Path は settings.duckdb_path を利用するのが便利）:

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection。以降の処理で利用できます。
```

---

## 使い方（簡単な例）

以下は主要な操作の最小例です。実運用前に環境変数や DB スキーマなどを整備してください。

- 日次 ETL を実行（DuckDB に接続して run_daily_etl を呼ぶ）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # 取得件数や品質チェック結果を確認
```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が設定されていれば api_key は None でよい
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- マーケットレジーム判定（regime）をスコアして market_regime テーブルへ書き込み:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を利用
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマを初期化（既述の init_audit_db と同等）:

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/audit.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

---

## 注意点・設計方針（要旨）

- Look-ahead バイアス防止のため、内部関数は datetime.today() / date.today() を直接参照しない設計（多くの関数は target_date を引数に取ります）。
- API 呼び出しは堅牢なリトライ・バックオフ・レート制御を実装（J-Quants / OpenAI）。
- ETL と DB 保存は冪等（ON CONFLICT ...）により重複インサートを防ぎ、監査ログも冪等性を考慮。
- ニュース収集は SSRF / XML 攻撃 / Gzip bomb / 大容量レスポンス対策を実施。
- テスト容易性のため、外部 API 呼び出し箇所は差し替え（モック）しやすい設計。

---

## ディレクトリ構成（概要）

プロジェクトの主要なファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py                    — パッケージ初期化（__version__ 等）
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save 系）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 他）
    - etl.py                       — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py            — RSS ニュース収集・前処理
    - quality.py                   — データ品質チェック
    - calendar_management.py       — マーケットカレンダー管理
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等の計算
    - feature_exploration.py       — 将来リターン計算・IC・統計サマリー
  - (その他)
    - strategy/                     — 戦略ロジック（本リストでは詳細未掲示）
    - execution/                    — 約定・ブローカ連携（詳細未掲示）
    - monitoring/                   — 監視・通知機能（詳細未掲示）

注: strategy / execution / monitoring は __init__ の __all__ に含まれていますが、本 README に含めたコード断片では詳細実装が省略されています。実際のリポジトリではそれらのパッケージも存在する想定です。

---

## 貢献・開発メモ

- LLM 呼び出し部（news_nlp, regime_detector）はテスト時に差し替えられるよう設計されています（ユニットテストでは _call_openai_api をモックしてください）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています（互換性に注意）。
- 運用時は KABUSYS_ENV を適切に設定し（paper_trading / live）、ログレベルや通知設定を整えてください。

---

必要に応じて、この README をベースにサンプルスクリプト、運用フロー、CI/デプロイ手順、依存関係一覧（pyproject.toml / requirements.txt）などを追加できます。必要な追加情報があれば教えてください。