# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ収集（J-Quants、RSS）→ 品質チェック → 特徴量算出 → ニュースNLP / レジーム判定 → 監査ログの管理、という一連の処理を提供します。  
（パッケージ名: `kabusys`, バージョン: 0.1.0）

---

## 主要な目的・概要

- J-Quants API から株価・財務・上場情報・マーケットカレンダーを取得して DuckDB に蓄積する ETL パイプラインを提供します。
- RSS ニュース収集・前処理・銘柄紐付けを行い、OpenAI を用いてニュースセンチメント（銘柄毎・マクロ）を評価します。
- ETF（1321）の長期移動平均乖離とマクロニュースの LLM スコアを組み合わせて市場レジーム（bull/neutral/bear）を判定します。
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）や統計ユーティリティを提供します。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル定義と初期化ユーティリティを備えています。
- データ品質チェック（欠損・重複・スパイク・日付不整合）を実行する機能があります。

---

## 機能一覧（概要）

- データ取得 / ETL
  - J-Quants クライアント（認証、ページネーション、レートリミット、リトライ）
  - ETL パイプライン（価格 / 財務 / カレンダーの差分取得、バックフィル）
  - market_calendar の夜間更新ジョブ
- ニュース関連
  - RSS フィード取得・前処理（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - news → 銘柄マッピング / ai スコアリング（OpenAI）
  - マクロニュースを使った市場レジーム判定（OpenAI）
- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- データ品質（Quality）
  - 欠損検出、主キー重複、スパイク検出、日付不整合チェック
  - 全部チェックをまとめて実行する `run_all_checks`
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義
  - スキーマ初期化ユーティリティ（`init_audit_schema` / `init_audit_db`）
- 設定管理
  - `.env` / `.env.local` 自動ロード（プロジェクトルート検出）と `Settings` クラス

---

## 必要条件（想定）

- Python 3.10+（型ヒントで `|` を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等も利用

（実プロジェクトでは requirements.txt / pyproject.toml に依存を明記してください）

---

## セットアップ手順

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクト配布に合わせて `pip install -e .` や extras を利用してください）

3. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（少なくとも以下を設定してください）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - OPENAI_API_KEY: OpenAI を直接呼ぶ関数で環境を使う場合は必須（関数に api_key を渡すことも可能）
   - 省略時は以下の値がデフォルトになります（任意）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - README 等の `.env.example` を参考にしてください（リポジトリにあれば）

---

## 基本的な使い方（例）

下記は Python スクリプトやインタラクティブに実行する一例です（DuckDB 接続を使うことが前提）。

- ETL（日次パイプライン）を実行する例:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルトの DB ファイルパスは settings.duckdb_path
conn = duckdb.connect("data/kabusys.duckdb")

# target_date を指定（None で今日）
result = run_daily_etl(conn, target_date=date(2026,3,20))

print(result.to_dict())
```

- ニューススコア（銘柄ごと）を生成する例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20))  # OpenAI API キーは OPENAI_API_KEY または api_key 引数で与える
print(f"scored stocks: {count}")
```

- 市場レジーム判定の例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数または api_key 引数
```

- 監査用 DuckDB を初期化する例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# これで signal_events / order_requests / executions テーブルが初期化されます
```

- カレンダー関数の利用例:

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
- OpenAI 呼び出しを行う関数（news scoring, regime scoring 等）は API キーを引数で受け取れます。テスト時はこの引数や内部の `_call_openai_api` をモックしてください。
- ETL・スキーマ操作は DuckDB 接続を直接受け取ります。トランザクション扱いに注意して呼び出してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（関数に渡すことも可能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring 用)（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュールと役割の一覧です（`src/kabusys` 配下）。

- __init__.py
  - パッケージのエクスポートと __version__ = "0.1.0"

- config.py
  - 環境変数・設定管理（Settings クラス）
  - .env / .env.local の自動読み込みロジック

- ai/
  - news_nlp.py
    - RSS ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出、ai_scores に書き込む
  - regime_detector.py
    - ETF(1321)のMA乖離とマクロニュースLLMスコアを合成して market_regime に書き込む

- data/
  - jquants_client.py
    - J-Quants API クライアント（認証、fetch/save、レート制御、リトライ）
  - pipeline.py
    - ETL 実行（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
    - ETLResult データクラス
  - calendar_management.py
    - JPX カレンダーの管理、営業日判定、calendar_update_job
  - news_collector.py
    - RSS 取得・前処理・raw_news 保存（SSRF 対策等を含む）
  - quality.py
    - データ品質チェック（欠損、重複、スパイク、将来日付/非営業日）
  - stats.py
    - zscore_normalize などの統計ユーティリティ
  - audit.py
    - 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - etl.py
    - ETLResult の公開エイリアス（pipeline.ETLResult の再エクスポート）

- research/
  - factor_research.py
    - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration.py
    - calc_forward_returns, calc_ic, factor_summary, rank（研究用ユーティリティ）
  - __init__.py
    - 研究 API のエクスポート

- その他
  - monitoring, strategy, execution モジュールはパッケージエクスポートに含まれます（将来的に実装・拡張想定）

---

## 開発 / テストに関する注意

- 外部 API を叩く部分（OpenAI / J-Quants / RSS のネットワーク呼び出し）はユニットテスト中にモックしてください。各モジュールは内部で `_call_openai_api` や `_urlopen` など置き換え可能な関数を用意しており、テストで差し替えられるよう設計されています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の所在）を基に行います。テスト実行時に環境依存を避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対しては接続オブジェクトを明示的に作成して渡す設計です。テストでは `:memory:` を使用すると簡単にインメモリ DB が使えます。

---

## ライセンス・貢献

（ここにはライセンス情報、貢献ガイドライン、連絡先などを追記してください）

---

この README はコードベースの主要設計・使い方を要約したものです。詳細は各モジュールの docstring / ソースコードをご参照ください。