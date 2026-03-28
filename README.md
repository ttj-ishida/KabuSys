# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ETL パイプライン、ニュース NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供するモジュール群です。バックテストや本番運用のデータ基盤・戦略実装の基礎を目的としています。

主な設計方針:
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を中心としたローカル DB 管理（ETL は冪等性を考慮）
- 外部 API 呼び出しに対してリトライ・レート制御・フェイルセーフ実装
- OpenAI（gpt-4o-mini）を用いた JSON Mode 入出力による堅牢な NLP 呼出し

---

## 機能一覧

- data（データ層）
  - J-Quants クライアント（株価・財務・上場情報・マーケットカレンダー取得）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - market calendar 管理（営業日判定・翌営業日/前営業日取得など）
  - news collector（RSS 取得、SSRF 対策、前処理、raw_news 保存）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal / order_request / executions テーブル、初期化ユーティリティ）
  - 汎用統計ユーティリティ（Z スコア正規化 等）
- ai（NLP / LLM）
  - news_nlp: ニュース記事を銘柄毎に集約して OpenAI に投げ、ai_scores に書き込む（score_news）
  - regime_detector: ETF(1321)の MA とマクロニュース LLM センチメントを合成して市場レジーム判定（score_regime）
- research（リサーチ）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン・IC・統計サマリー等の解析ユーティリティ

安全性・運用面の特徴:
- API レート制限の考慮（J-Quants: 固定間隔スロットリング）
- OpenAI 呼び出しに対するリトライ（5xx/429 等）とレスポンスバリデーション
- ETL/保存処理は冪等設計（ON CONFLICT 等）
- ニュース収集時の SSRF 対策、XML 安全パーサー利用（defusedxml）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに | 演算子を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてパッケージをインストール（開発用）
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[all]"     # requirements が用意されていれば -r で代替
   ```
   ※ このコードベースには requirements.txt が含まれていない想定です。少なくとも次のパッケージは必要になります:
   - duckdb
   - openai
   - defusedxml

   追加（環境に応じて）:
   - slack-sdk（Slack 通知を使う場合）
   - requests 等（外部モジュールを追加したい場合）

2. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD: kabu API（発注など）用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
   推奨／任意:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB データパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

3. データベース初期化（監査ログ等）
   サンプル:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings

   # DuckDB メイン DB に接続する例
   conn = duckdb.connect(str(settings.duckdb_path))
   # 監査用 DB (別ファイル) を初期化する例
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本例）

以下は各機能の呼び出し例です。実運用ではエラーハンドリングやログ、スケジューリング（cron / Airflow 等）を適切に行ってください。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム（bull/neutral/bear）を判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログスキーマを初期化（既存の DuckDB 接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- J-Quants から株価を直接取得する（テストや補助用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from kabusys.config import settings
# tokens は settings.jquants_refresh_token で取得される
rows = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

注意点:
- OpenAI 呼び出しは JSON Mode 出力を想定しており、厳密な JSON を返すことをプロンプトで要求しています。レスポンスのパースに失敗した場合はフェイルセーフでスコア 0.0 を扱う実装箇所があります。
- J-Quants API はリクエストレートを制限しています（モジュール内で固定間隔スロットリングを行います）。

---

## 主要な設定項目（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（score_news / score_regime 実行時。関数引数で注入可能）

任意（デフォルトがあるもの）:
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env の読み込み順:
1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き）
3. .env

パーサはシェル風の export KEY=val に対応し、クォートやインラインコメント処理も行います。

---

## ディレクトリ構成（概要）

プロジェクトは src/kabusys 以下に実装がまとまっています。主要ファイルと簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM センチメント解析（score_news）
    - regime_detector.py      — マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL API の再エクスポート（ETLResult）
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - news_collector.py       — RSS 収集・前処理・raw_news 保存
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 等
    - feature_exploration.py  — 将来リターン/IC/統計サマリー
  - ai/、data/、research/ はそれぞれ public API を __all__ で整理

（上記は抜粋です。詳細はソースを参照してください。）

ツリーの簡易表示例:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ calendar_management.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリは外部 API（J-Quants / OpenAI）を扱うため、運用時は API キーの権限管理・ログ監査・レート制御に留意してください。
- ETL は差分更新・バックフィルを内部で処理しますが、スケジュール実行（cron / CI / Airflow）と品質チェックのアラート機構を組み合わせることを推奨します。
- OpenAI 呼び出しはコストが発生するため、バッチサイズや最大記事文字数（_MAX_CHARS_PER_STOCK 等）を適切に設定して運用してください。
- DuckDB ファイルは定期バックアップを推奨します（データ破損や誤操作に備えて）。

---

## 貢献・ライセンス

この README はコードベースから抽出した情報を元に手短にまとめたものです。細かな挙動や追加のユーティリティについてはソースコード内の docstring を参照してください。ライセンスやコントリビュート規約はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、README にサンプル .env.example 内容、より詳細な CLI / サービス起動手順、CI 設定例、ユニットテストの書き方例などを追記します。どの情報を充実させたいか教えてください。