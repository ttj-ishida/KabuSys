# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つ内部ユーティリティ群です。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL）
- DuckDB を用いたデータ保存と品質チェック
- RSS ニュース収集と OpenAI を使った銘柄別センチメントスコアリング
- マクロニュースとETF（1321）のMA乖離を組み合わせた市場レジーム判定
- 戦略→シグナル→発注→約定に至る監査ログ（トレーサビリティ）の初期化ユーティリティ
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ

設計方針として「ルックアヘッドバイアスの排除」「API 呼び出しの冪等性」「フェイルセーフ（API失敗時は安全なデフォルトで継続）」を重視しています。

---

## 機能一覧

- 環境変数/設定管理（自動 .env ロード、保護キー）
- J-Quants API クライアント（認証、ページネーション、リトライ、レート制御）
- ETL パイプライン（prices / financials / calendar の差分取得と保存）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS、SSRF 対策、テキスト前処理）
- ニュース NLP（OpenAI を用いた銘柄別センチメント、JSON Mode 利用、リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 研究用ファクター計算（momentum / value / volatility 等）、Z-score 正規化
- 監査ログスキーマ初期化（DuckDB 用、冪等、UTC タイムスタンプ）

---

## 前提 / 要件

- Python 3.10+
- 主要依存ライブラリ（例、パッケージの実際の requirements が無い場合は以下を想定）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 実際の requirements.txt / pyproject.toml に依存するため、環境構築時は該当ファイルを参照してください。

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （パッケージ化されている場合）pip install -e .

4. 環境変数設定
   - プロジェクトルートの `.env` または `.env.local` に必要なキーを設定してください。
   - 自動 .env 読み込みはデフォルトで有効です（ルートは .git または pyproject.toml から検出）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な主要環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（本システムの別機能向け）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネルID
- OPENAI_API_KEY: OpenAI API 呼び出しで未指定時に参照されるキー

データベースパス（任意、デフォルト値）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 SQLite, デフォルト: data/monitoring.db)

システムモード
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

---

## 使い方（主なユーティリティ例）

以下は Python REPL もしくはスクリプト内での呼び出し例です。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを生成する（OpenAI API キーは環境変数または引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None だと env の OPENAI_API_KEY を使う
print("書き込み銘柄数:", n_written)
```

3) 市場レジームをスコアリングする
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_kabusys.duckdb")
# conn を用いて order_requests / signal_events / executions テーブルが作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

注意:
- 多くの関数は DuckDB 接続と target_date を受け取り、内部でルックアヘッドを避ける実装になっています（date.today() 等を直接参照しない）。
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク/料金発生源になるため、テスト時はモックを推奨します（モジュール内で _call_openai_api のモックが可能）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — マクロ+MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py      — RSS 収集（SSRF 対策・前処理）
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/
    - ... (上記)
  - research/
    - ... (上記)

README等の他ファイルや tests はリポジトリに含まれている想定です。

---

## 環境変数の自動ロード

- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は .env の上書き（override=True）
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ロギング / モード

- 環境変数 `KABUSYS_ENV` によりモードを切替（development / paper_trading / live）
- `LOG_LEVEL` でログレベルを指定（デフォルト INFO）

---

## テストとモック

- OpenAI 呼び出しなど外部APIの箇所はモジュール内で呼び出しを集約しており、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch して差し替え可能です。
- J-Quants クライアントの HTTP 呼び出しも _request を通しているため、テストでは urllib 周りをモックできます。

---

## 貢献 / 注意事項

- 外部 API キーや実口座情報の管理には十分注意してください（.env を含めて VCS にコミットしないでください）。
- DuckDB のスキーマや SQL は本番運用・互換性を考慮した実装がなされていますが、マイグレーションやスキーマ変更時はバックアップを取ってください。
- 本リポジトリのコードは参考実装として提供しています。実際の自動売買に用いる場合は十分な監査・テストを行ってください。

---

必要に応じて README にサンプル .env.example、より詳細な API 使用例、CLI スクリプトの追加を行えます。ご希望があれば補足します。