# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
ETL（J-Quants）→データ品質チェック→特徴量／リサーチ→AI（ニュースNLP / レジーム判定）→監査ログ／発注トレースといった一連の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株を対象にした内部データプラットフォームとリサーチ・自動売買のためのモジュール群です。主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- ニュース記事の収集・NLP（OpenAI を用いたセンチメント）による銘柄スコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量探索ツール（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用の DuckDB スキーマ初期化ユーティリティ

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 取得・保存（日足・財務・カレンダー等）、レートリミット・リトライ・トークン自動リフレッシュ
  - pipeline: 日次 ETL 実行（差分取得、保存、品質チェック）。ETLResult を返す。
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集（SSRF 対策・サイズ制限・トラッキング除去）と raw_news への保存処理想定
  - audit: 監査ログテーブル定義／初期化（signal_events / order_requests / executions）
  - calendar_management: 市場カレンダーの補助関数（営業日判定、next/prev_trading_day 等）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp: ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores へ保存
  - regime_detector: ETF（1321）200日MA乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込み
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算（prices_daily / raw_financials ベース）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- config: 環境変数の自動読み込みロジック（.env / .env.local、環境変数優先）、Settings オブジェクト

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```
pip install duckdb openai defusedxml
```
（プロジェクトに requirements.txt があればそちらを使用してください。）

---

## セットアップ手順

1. リポジトリをクローン／取得する。
2. 仮想環境を作成し、依存パッケージをインストールする。
3. 環境変数を設定する（.env ファイルをプロジェクトルートに配置すると自動で読み込まれます。読み込み順は OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。
4. DuckDB ファイルの保存先ディレクトリ（デフォルト: data/）を作成する（init_audit_db が自動で作る場合もあります）。

---

## 環境変数（主要）

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- SLACK_BOT_TOKEN: Slack 通知に使用する場合
- SLACK_CHANNEL_ID: Slack 通知先チャンネル
- KABU_API_PASSWORD: kabuステーション API を使う場合

OpenAI 関連:
- OPENAI_API_KEY: news_nlp / regime_detector 実行時に使用（関数の api_key 引数で上書き可能）

その他:
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

注意: config.Settings は必須環境変数が未設定の場合 ValueError を投げます。

簡単な .env の例（.env.example 相当）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内から呼び出す例です。各関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- DuckDB 接続の作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコア（ai_scores への書き込み）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数にセットしていない場合は api_key を渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("wrote", n_written, "codes")
```

- 市場レジーム判定（market_regime への書き込み）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログデータベース初期化（監査用 DuckDB を作成）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# あるいは :memory: を使ってテスト
# audit_conn = init_audit_db(":memory:")
```

- 研究用ファクター計算例:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
```

注意点:
- OpenAI 呼び出しは外部 API なので、APIキーとレートに注意してください。
- ETL / 保存系は DuckDB テーブル構造を前提としています。事前にスキーマを用意するか、ETL 実行時のスキーマ初期化ロジックを組み合わせてください。
- 多くの機能は「Look-ahead バイアス」を防ぐ設計（target_date 未満のデータのみ参照）になっています。バックテストや再現時は取得日付の扱いに留意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・Settings 定義
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント評価、ai_scores への書込
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult 再エクスポート
    - quality.py         — データ品質チェック
    - news_collector.py  — RSS 収集ユーティリティ
    - calendar_management.py — 営業日ロジック、calendar_update_job
    - audit.py           — 監査ログスキーマ初期化 / init_audit_db
    - stats.py           — 統計ユーティリティ（z-score）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*          — ファクター / 特徴量探索関連

---

## 開発・テストのヒント

- 環境変数の自動読み込みは config._find_project_root() でプロジェクトルート（.git / pyproject.toml）を探し .env / .env.local を読み込みます。ユニットテストで副作用を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは各モジュール内で _call_openai_api を定義しており、ユニットテストではこの関数を patch/mocking して応答を差し替えられるようになっています。
- jquants_client の HTTP 呼び出しは内部でリトライとレートリミットを行います。テスト時はネットワーク呼び出しをモックしてください。
- DuckDB のバージョン差異により executemany 空リストの扱いが異なるため、コード側で空リストチェックが行われています。テストで空の書込みパスを検証する場合は注意してください。

---

## ライセンス / 貢献

（ここには実際のプロジェクトのライセンスや貢献ガイドを記載してください。）

---

以上が README.md の要旨です。必要であれば、README に示すサンプル .env.example や、スキーマ初期化スクリプト、requirements.txt の推奨内容などを追記できます。どの部分をより詳しくしたいか教えてください。