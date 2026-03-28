# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取り込み）、ニュースの NLP スコアリング、リサーチ用ファクター計算、監査ログ（オーディット）など、バックテスト／運用に必要な基盤機能群を提供します。

---

## 概要

KabuSys は以下を主たる目的とするモジュール群を含む小規模なプロジェクトです。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS ニュース収集と OpenAI を用いたニュースセンチメントスコアリング
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を想定したローカル DB への保存機能

設計方針として「Look-ahead バイアス回避」「冪等性」「外部 API の堅牢なリトライ／レート制御」「テストしやすい分離設計」を重視しています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（レートリミット制御・トークン自動リフレッシュ・ページネーション対応）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース関連（NLP）
  - RSS 取得・前処理（SSRF 対策・トラッキングパラメータ除去・サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200乖離で日次市場レジーム判定（score_regime）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum 等）
  - 将来リターン計算（calc_forward_returns）
  - IC（Information Coefficient）・統計サマリー・Zスコア正規化
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合検出（run_all_checks）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを初期化するユーティリティ
  - 監査 DB の初期化関数（init_audit_db / init_audit_schema）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部表記は 3.9+ 想定）
- DuckDB を利用するためライブラリ duckdb が必要
- OpenAI API を利用する場合は openai パッケージ
- RSS パースに defusedxml

1. リポジトリをチェックアウト
   - git clone ...（適宜）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
   - 開発インストール例: pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（少なくとも運用する機能に応じて設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API 用パスワード（注文等を実装する場合）
     - SLACK_BOT_TOKEN — Slack 通知に使用するトークン
     - SLACK_CHANNEL_ID — Slack チャンネルID
     - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）の場合必要
   - データベースパス（任意、デフォルト値あり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用途等、デフォルト: data/monitoring.db）

5. プロジェクトルート検出について
   - config._find_project_root() は .git または pyproject.toml を起点にプロジェクトルートを探索します。パッケージ配布後も挙動が安定する設計です。

---

## 使い方（代表的な例）

以下は最小限の使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を用意して ETL を実行する（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path に合わせても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）を実行する:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written codes:", n_written)
```

- 市場レジーム判定を実行する:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等にアクセスできます
```

- 研究用ファクター計算の例:

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore_normalize 等を使って正規化することも可能
```

---

## 環境変数・設定の挙動

- .env / .env.local がプロジェクトルートにあれば自動で読み込まれます（OS 環境変数が優先、.env.local は .env を上書き）。
- 自動ロードを停止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の設定を参照する箇所では未設定時に ValueError が送出され、README に記載の key を .env に追加するよう案内されます。

---

## ディレクトリ構成（主なファイル）

（パッケージのルートは src/kabusys として記載）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの収集ウィンドウ計算・OpenAI 呼び出し・スコア保存ロジック
    - regime_detector.py   — ETF の MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS フィード取得・前処理・raw_news 保存
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py          — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログテーブルの DDL／初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Volatility / Value のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - research パッケージは data.stats を再利用します

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアス防止: 多くの関数は date 引数を外部から明示的に受け取り、内部で date.today() 等を直接参照しない設計です。バックテストや再現性のため、常に明示的な日付を渡すことを推奨します。
- OpenAI 呼び出し: レスポンスの堅牢性を高めるため JSON mode を利用し、リトライ・パース失敗時はフェイルセーフで 0.0 に戻す等の処理があります。API 利用料とレートに注意してください。
- J-Quants: API のレート制限に合わせた固定間隔スロットリングとリトライロジックを入れています。ID トークンは自動リフレッシュされ、モジュール内でキャッシュされます。
- DuckDB の executemany に空リストを与えると失敗するバージョンがあるため、コード内で必ず空チェックを行っています。DuckDB のバージョン差に注意してください。
- RSS 取得は SSRF 対策（リダイレクト検査・プライベートホスト拒否）・サイズ制限を施しています。外部フィードの信頼性に依存する点に注意してください。

---

## 貢献 / テスト

- 機能ごとに分離されており、ユニットテストで OpenAI / HTTP / DuckDB をモックしやすく設計されています。
- テストを書いてプルリクエストを送る際は、外部 API キーを含めないこと（.env.example を用意してキーを除去したテンプレートを置く等）を徹底してください。

---

この README はコードベースの公開インターフェースと主要な設計意図をまとめたものです。さらに詳細な API使い方や運用手順は各モジュールの docstring を参照してください。質問や追記したい項目があれば教えてください。