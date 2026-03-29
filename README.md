# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API からのデータ取得（ETL）、DuckDB ベースのデータ管理、ニュース収集・NLP によるセンチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得から特徴量計算、AI を用いたニュースセンチメント判定、マーケットレジーム評価、そして発注前後の監査ログ管理までを想定した内部ライブラリ群です。  
設計における主な方針は以下の通りです。

- Look-ahead バイアス防止（time.now を直接使わない / DB クエリに排他条件を付与）
- DuckDB を用いたローカルデータプラットフォーム
- J-Quants API の差分取得（レート制御・リトライ・トークン自動更新）
- OpenAI（gpt-4o-mini）を用いたニュース解析（JSON Mode）とフェイルセーフ処理
- 冪等性（DB 保存時は ON CONFLICT で上書き）と監査ログ（完全なトレーサビリティ）

---

## 主な機能一覧

- データ ETL
  - J-Quants から株価（日足）・財務・マーケットカレンダーを差分取得し DuckDB に保存（kabusys.data.pipeline）
  - 差分・バックフィル・品質チェックを組み合わせた日次 ETL（run_daily_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後営業日の算出 / カレンダー自動更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの収集、前処理、raw_news への冪等保存（SSRF / XML 攻撃対策あり）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄別ニュースセンチメント算出（JSON 出力検証、バッチ処理、リトライ）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）＋マクロニュース LLM センチメント（30%）で日次レジーム判定
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC・統計サマリ
- 監査ログ（kabusys.data.audit）
  - signal → order_request → executions までの監査テーブル定義・初期化ユーティリティ
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ、ID トークン自動更新、DuckDB への保存ユーティリティ

---

## 動作環境 / 依存

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）を行うため適切な環境変数が必要

必要パッケージはプロジェクトの setup/pyproject を参照してください（本リポジトリ断片では省略）。

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主に必要な変数は以下です。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI 関連処理で必須）
- KABUSYS_ENV: 実行環境 ('development' | 'paper_trading' | 'live')
- LOG_LEVEL: ログレベル ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')

.env の書式は shell 形式（KEY=VALUE、export KEY=... 等）に対応し、クォートやコメント処理も行います。

---

## セットアップ手順（例）

1. Python と仮想環境の準備
   - Python 3.10 以上を用意し、仮想環境を作成・アクティブ化してください。
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存のインストール
   - 必要なライブラリをインストールしてください（requirements.txt / pyproject を参照）。
     - 例:
       pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成して必要なキーを設定します。
     例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ作成等
   - DuckDB 保存先の親ディレクトリを作成しておきます（init 関数で自動作成する場合もあります）。
     - 例: mkdir -p data

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプトから主要機能を呼ぶ最小例です。

- DuckDB 接続を作り日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続（存在しない場合は作成）
conn = duckdb.connect("data/kabusys.duckdb")

# 今日の日次ETLを実行（settings.jquants_refresh_token が .env / 環境変数で設定されている前提）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを生成する:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"スコアを書き込んだ銘柄数: {n_written}")
```

- 市場レジームスコアを計算して保存する:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込み等が可能
```

- J-Quants トークンを直接取得したい場合:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
print(token)
```

---

## 開発時のヒント / 注意点

- LLM 呼び出しは失敗時にフォールバックする設計です（スコアは 0 にフォールバックするなど）。ただし API キー未設定だと例外を投げますのでテスト時はモック化を推奨します。
- news_nlp と regime_detector はテスト容易性のため内部の OpenAI 呼び出し関数を差し替え可能です（unittest.mock.patch で _call_openai_api をモック）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時や CI で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany は空リストを受け付けないバージョンの互換性を考慮した実装があります（空パラメータを渡さないように注意）。
- OpenAI の JSON Mode を期待した厳密パースを行っているため、モデルの出力形式・安定性に依存します。レスポンスの検証・パースに失敗した場合は該当銘柄・チャンクをスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理、自動 .env 読み込み
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント (score_news)
  - regime_detector.py — 市場レジーム判定 (score_regime)
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理
  - etl.py — ETL 辞書再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ定義 / 初期化
  - jquants_client.py — J-Quants API クライアント & DuckDB 保存関数
  - news_collector.py — RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ 等

（上記は本コードベースで定義されている主要モジュールの一覧です）

---

## 貢献 / テスト

- 単体テストは各モジュールの外部 API 呼び出しをモックして行うことを推奨します（特に OpenAI / urllib / J-Quants）。
- config.py の自動 .env 読み込みはテスト時に副作用を及ぼすことがあるため、KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて無効化してください。
- DuckDB を利用するテストでは ":memory:" を使うことでインメモリ DB による高速なテストが可能です（init_audit_db などは ":memory:" をサポートします）。

---

もし README に追加したい具体的な例（CI 設定、Dockerfile、pyproject.toml、.env.example のテンプレートなど）があれば、提供いただければそれに合わせて拡張版 README を作成します。