# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants や RSS、OpenAI など外部データを取り込み、ETL、品質チェック、ファクター計算、ニュース NLP、マーケットレジーム判定、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ／戦略層を支える共通ライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL。
- raw_news（RSS）収集・前処理と OpenAI を用いたニュースセンチメントスコアリング（銘柄単位）。
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの合成）。
- ファクター作成（モメンタム / バリュー / ボラティリティ 等）とリサーチ用ユーティリティ（IC, forward returns 等）。
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）機能。
- 環境変数ベースの設定管理（.env 自動読み込み機能あり）。

設計方針として、バックテスト時のルックアヘッドバイアス回避、冪等性、外部 API の堅牢なリトライ/フェイルセーフ、DuckDB を利用した軽量永続化を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック、環境モード判定（development / paper_trading / live）

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API のページネーション対応フェッチ、レートリミッティング、トークン自動更新
  - raw_prices / raw_financials / market_calendar への冪等保存
  - 日次 ETL run_daily_etl：カレンダー → 株価 → 財務 → 品質チェックの一括実行

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）
  - 重複チェック、将来日付 / 非営業日データ検出

- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 収集（SSRF 対策・gzip 制限・URL 正規化・トラッキング除去）
  - OpenAI を用いた銘柄ごとのニュースセンチメント（JSON Mode, バッチ・リトライ実装）
  - score_news(conn, target_date, api_key=None) で ai_scores テーブルへ書き込み

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュース LLM 観点を重み合成して daily regime を判定
  - score_regime(conn, target_date, api_key=None)

- 研究用ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティのファクター計算
  - forward returns, IC（スピアマン）計算、Z スコア正規化等

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化 helper（冪等）
  - init_audit_db(db_path) により監査用 DuckDB を初期化

---

## セットアップ手順

以下は開発環境での例です。実運用では依存管理（Poetry / pipx / Docker 等）やシークレット管理を適宜導入してください。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml

   （パッケージバージョンはプロジェクトの requirements / pyproject に従ってください。ローカル開発用に `pip install -e .` を用いて editable インストールすることも可能です）

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（kabusys.config が .git または pyproject.toml を見てルートを特定します）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に利用）
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用
   - データベースパス（任意、デフォルト値）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
   - 自動 .env ロードを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB 初期スキーマ作成
   - ETL や audit 初期化関数を実行してテーブルを作成してください（プロジェクトに schema 初期化ユーティリティがある場合はそれを利用）。

注意: 実際の J-Quants / OpenAI API 呼び出しはネットワーク接続と適切な料金プラン（API 使用料）が必要です。

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの利用例です。

1) 環境変数の確認 / 設定済みであることを前提に DuckDB 接続を作成して ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続（自動でファイル作成）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか引数で渡す）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"{written} 銘柄のスコアを書き込みました")
```

3) マーケットレジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（独立した監査用DBを作成）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.db")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) リサーチ用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# リストとして (date, code, mom_1m, mom_3m, mom_6m, ma200_dev) を取得
```

テストや CI では多くの内部関数が引数で api_key を受け取ったり、OpenAI 呼び出し部分をモックしやすい設計になっています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API を使う場合
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境モード（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

設定は .env または .env.local に記述可能。プロジェクトルートの .env が自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

.env のフォーマットはコメント行や export プレフィックスに対応し、クォートやインラインコメントの取り扱いに配慮したパーサを使用します。

---

## ディレクトリ構成（抜粋）

主要モジュールと階層の概観です（実ファイルを含む src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境設定・.env ローダ
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news）
    - regime_detector.py          — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch / save）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETL の公開型再エクスポート
    - news_collector.py           — RSS 収集 / 前処理
    - calendar_management.py      — マーケットカレンダー管理（営業日判定等）
    - quality.py                  — データ品質チェック
    - stats.py                    — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py          — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py      — forward returns / IC / summary / rank
  - research/*（その他の研究用モジュール）

各ファイルの docstring に詳細な設計方針と実装の注意点が記載されています。関数は概ね DuckDB 接続を引数で受け取り、外部副作用（発注等）は行わないものと、ETL/保存系で DB に書き込むものがあります。

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス回避
  - 多くの関数は内部で date.today() を参照しない設計（target_date を明示的に渡す）です。バックテストでは必ず target_date を固定して呼び出してください。

- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて冪等に保存します。ETL は差分取得＋バックフィル設計です。

- API キーの取り扱い
  - OPENAI_API_KEY や J-Quants のトークンは環境変数で管理してください。CI 等での安全な取り扱いを推奨します。

- テスト
  - OpenAI 呼び出し箇所はモック可能（モジュール内の _call_openai_api をパッチする等）で、外部アクセスポイントを分離した設計になっています。

---

## 貢献・拡張

- 新しい RSS ソース追加は data.news_collector.DEFAULT_RSS_SOURCES を拡張
- 新しいファクター追加は research/ のモジュールに実装し、zscore_normalize 等ユーティリティを活用
- kabu API やブローカー連携は execution 層（本リポジトリに存在する場合）で安全に抽象化して実装してください

---

問題や改善提案、API 仕様の議論等があれば issue を立ててください。README に記載のない運用・設計上の意図は各モジュールの docstring に詳述しています。