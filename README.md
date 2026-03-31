# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得／保存）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログスキーマ、マーケットカレンダー管理、そして市場レジーム判定などを含みます。

> 注: この README はソースコード（src/kabusys 配下）を元に作成しています。

---

## 主な概要

KabuSys は以下の機能群を提供します（ライブラリとしてインポートして利用）:

- データ ETL（J-Quants API からの株価・財務・カレンダー取得、DuckDB 保存）
- ニュース収集（RSS）と NLP による銘柄センチメントスコア生成（OpenAI 使用）
- 市場レジーム判定（ETF の MA 乖離 + マクロニュースセンチメント）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）用の DuckDB スキーマ初期化
- JPX カレンダー管理（営業日判定、next/prev trading day 等）

モジュール主要一覧:
- kabusys.config: 環境変数・設定管理（.env 自動読み込みあり）
- kabusys.data: ETL、J-Quants クライアント、ニュース収集、品質チェック、監査スキーマ等
- kabusys.ai: news_nlp（記事センチメント）、regime_detector（市場レジーム判定）
- kabusys.research: ファクター計算・特徴探索ユーティリティ

---

## 機能一覧（抜粋）

- 自動差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ニュース RSS 収集（SSRF 対策・トラッキングパラメータ除去・前処理）
- OpenAI を用いたニュースセンチメント（gpt-4o-mini / JSON mode）バッチ処理
- 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロセンチメントの加重合成）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 研究用ファクター群（モメンタム / バリュー / ボラティリティ 等）
- 監査ログスキーマの初期化・専用 DB 作成ユーティリティ

---

## 動作要件

- Python 3.10 以上（型注記に `X | None` を使用しているため）
- 推奨パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging, datetime など）

requirements.txt が無い場合は以下をインストールしてください（例）:
pip install duckdb openai defusedxml

（プロジェクト配布に requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -e .            （パッケージ化されている場合）
   - または: pip install duckdb openai defusedxml
4. 環境変数を設定（.env をプロジェクトルートに作成）
   - プロジェクトは起動時に自動で .env/.env.local を読み込みます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です（.env に設定）。必須なものは README 上で明記します。

必須（アプリ実行に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY: news_nlp / regime_detector で使用。関数呼び出し時に api_key 引数を渡してオーバーライド可能。

DB パス等（デフォルト値あり）:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)

監視しきい値（デフォルト値あり）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（%）

システム設定:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env の読み込みについて:
- プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、.env を読み込み（既存 OS 環境変数は上書きしない）。
- その後 .env.local を読み込み（上書き許可。ただし OS 環境変数は保護される）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（簡単なコード例）

以下は Python から主要機能を呼ぶ例です。DuckDB 接続は `duckdb.connect()` を使用します。

1) 日次 ETL を実行する（market calendar / prices / financials / quality checks）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジームスコア（1321 の MA200 乖離 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って以降の監査ログテーブルにアクセスできます
```

5) 研究用ユーティリティの利用例（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化を掛ける場合
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意点:
- OpenAI を利用する関数は API 呼び出しに失敗した場合、フェイルセーフ（多くはスコア 0.0 やスキップ）を採る設計です。API キーは環境変数 OPENAI_API_KEY を推奨しますが、関数へ直接渡すことも可能です。
- J-Quants への認証は refresh token を使用して ID トークンを取得します。settings.jquants_refresh_token を必ず設定してください。

---

## 主要 API（抜粋）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic

各関数は docstring に詳細な挙動（引数・戻り値・エラーハンドリング）を記載しています。実装のコメント（設計方針）も豊富に書かれているので参照してください。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py
    - .env の自動読み込みロジック、settings オブジェクト（各種設定プロパティ）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメントのスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定ロジック（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - news_collector.py  — RSS 収集・前処理・DB 保存
    - quality.py         — データ品質チェック
    - calendar_management.py — マーケットカレンダーの判定・更新ロジック
    - stats.py           — 汎用統計ユーティリティ（zscore_normalize など）
    - audit.py           — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 運用上の注意

- Look-ahead バイアス対策が各モジュールに組み込まれています（target_date 未満のみ参照する等）。バックテストや再現性ある解析を行う際はこの設計を尊重してください。
- OpenAI / J-Quants の API 呼び出しにはレート制御・リトライが実装されていますが、実運用では API 使用量とコストに注意してください。
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を探索) に依存します。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御してください。
- DuckDB の executemany に関する制約（空リスト不可 等）を考慮した実装になっています。バージョン差異で挙動が異なる場合は duckdb バージョンを揃えてください。

---

## 参考（トラブルシュート）

- OpenAI のレスポンスパースに失敗した場合、ニュース・レジームモジュールはスコアを 0.0 にフォールバックしたり当該チャンクをスキップします。ログを確認して再実行してください。
- J-Quants で 401 が返った場合、トークンを自動リフレッシュして再試行します。refresh token が無効な場合は設定を見直してください。
- RSS 取得で SSRF 対策・レスポンスサイズチェック・gzip 解凍などの検査を行い、不正なフィードはスキップします。ログに出力される理由を確認してください。

---

README は以上です。必要であれば、使用例を増やしたりセットアップの自動化（スクリプト・docker-compose 等）や CI 設定例、requirements/pyproject のテンプレートを追加できます。どの部分を詳しく書き足しましょうか？