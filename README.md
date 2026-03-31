# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）・品質チェック・ニュース NLP・市場レジーム判定・研究用ファクター計算・監査ログ初期化などを行うモジュール群を提供します。

---

## 主要な特徴（機能一覧）

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得（ページネーション対応）
  - レートリミット・リトライ・トークン自動リフレッシュを備えた堅牢な HTTP クライアント
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（market calendar → prices → financials → 品質チェック）
  - 差分フェッチ / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を表す ETLResult 型
- ニュース収集・NLP
  - RSS 収集（トラッキングパラメータ除去、SSRF 対策、gzip ハンドリング）
  - OpenAI を用いたニュースの銘柄別センチメントスコアリング（gpt-4o-mini、JSON Mode）
  - LLM 呼び出しの堅牢化（リトライ、パース検証、スコアクリップ）
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次でレジーム判定（bull / neutral / bear）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z-score 正規化
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定までトレーサビリティを確保する監査テーブル生成・初期化ユーティリティ（DuckDB）
  - UUID ベースの冪等キー、ステータス遷移管理、UTC タイムスタンプ運用
- 汎用統計ユーティリティ（zscore_normalize など）

---

## 必要条件（推奨環境）

- Python 3.10+
- 必要なライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

インストール例:
```
pip install duckdb openai defusedxml
```

※プロジェクトの実行に応じて追加の依存が発生する場合があります（ロギング、sqlite の利用等）。

---

## 環境変数 / 設定

このパッケージは .env ファイル（プロジェクトルート）または環境変数を読み込みます（自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（注文連携等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（監視等）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルト値あり:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live") — デフォルト "development"
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" — デフォルト "INFO"
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime で参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

注意: 必須設定が不足していると Settings プロパティで ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存をインストール
   ```
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定（.env を作成）
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動的に読み込まれます。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB 用ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（プログラマティックに）

以下は代表的な利用例です。各関数は DuckDB 接続を受け取る設計になっています。

- DuckDB 接続を開く:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの銘柄別センチメントを生成（score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査DBを別ファイルで管理する例）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# init_audit_db はスキーマを作成して接続を返します
```

- ニュース収集（個別 RSS フェッチ）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

items = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for it in items:
    print(it["id"], it["title"], it["datetime"])
```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI API の課金対象です。api_key の管理に注意してください。
- ETL・news_collector 等はネットワークを使用します。実行環境のネットワーク設定やファイアウォールに留意してください。
- 自動ロードされる .env の挙動をテストで抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してから import してください。

---

## 主要モジュール（ディレクトリ構成）

簡略化した主要ファイルと役割:

- src/kabusys/
  - __init__.py — パッケージ公開（version 等）
  - config.py — 環境変数 / 設定の読み込み（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save 系）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得と前処理
    - calendar_management.py — マーケットカレンダーの判定 / 更新ロジック
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計（zscore_normalize）
    - audit.py — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリーなど
  - ai/* と research/* はモデル評価やバックテスト用の研究ワークフローを支援

（上記はリポジトリの主要モジュールを抜粋したものです。実際のディレクトリにはさらに補助モジュールが含まれます。）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス対策:
  - 多くの関数は date 引数で対象日を明示する設計です。内部で date.today() 等を無差別に使用しないため、バックテスト時は必ず適切な過去日を渡してください。
- 環境分離:
  - KABUSYS_ENV を "development" / "paper_trading" / "live" で切り替えて挙動や安全制約（実際の発注など）を区別してください。
- OpenAI / J-Quants の API キーは安全に管理し、不要時は取り外してください。
- ETL の品質チェック（quality.run_all_checks）は ETL 後に実行して問題を早期に検出してください。重大度の高い問題はアラートを上げる運用を推奨します。
- ニュース収集時は外部 URL の扱いに注意。news_collector には SSRF 対策や受信サイズ制限が組み込まれていますが、追加のポリシーが必要な場合があります。

---

## テスト / デバッグのヒント

- 環境変数の自動ロードを無効にしてテスト用に明示的に環境を切り替え:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しや HTTP レイヤーは各モジュールで _call_openai_api や _urlopen をモックしやすく分離されています。ユニットテスト時はこれらを patch して外部依存を切り離してください。
- DuckDB はインメモリモード（":memory:"）をサポートしているため、テスト用に一時 DB を用いると高速に検証できます。

---

## ライセンス / 貢献

（リポジトリに LICENSE 等がある場合はそちらを参照してください。貢献方法やコードスタイル、コミットルールなどはプロジェクトの CONTRIBUTING.md を参照してください。）

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API ドキュメントや実運用スクリプト（例: cron / Airflow 用のラッパー）は別途用意してください。必要に応じて README を拡張しますので、追加したい点（例: サンプル .env.example、Dockerfile、システム図など）を教えてください。