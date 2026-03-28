# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットカレンダー管理、データ品質チェック、ファクター計算、監査ログ（約定トレーサビリティ）などを一貫して提供します。

主な目的は、バックテスト・リサーチ環境および実運用のデータ基盤・分析基盤を安定して構築することです。

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - settings オブジェクトで各種設定（J-Quants / kabuステーション / Slack / DB パス 等）を取得

- データ取得（J-Quants クライアント）
  - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、上場銘柄情報、JPX マーケットカレンダーの取得
  - レートリミット対応・リトライ・トークン自動リフレッシュを実装
  - DuckDB へ冪等保存（ON CONFLICT で更新）

- ETL パイプライン
  - 差分取得・バックフィル・カレンダー先読み・品質チェックを含む日次 ETL run_daily_etl を提供
  - ETL の結果を ETLResult クラスで受け取れる

- ニュース収集・前処理
  - RSS フィードの取得（SSRF 対策、gzip/サイズ上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存（score_news）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM 評価の合成 → score_regime）

- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日付 / 非営業日データ）を検出
  - QualityIssue のリストで問題を返す

- マーケットカレンダー管理
  - market_calendar の取得・バッチ更新 job（calendar_update_job）
  - 営業日判定 / 前後営業日取得 / 期間内営業日取得 等のユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマ定義と初期化（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ確保（UUID ベースの階層）

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman ρ）、統計サマリー、zscore 正規化

---

## 必要条件 / セットアップ

推奨 Python バージョン: 3.10+

依存パッケージ（代表例）
- duckdb
- openai
- defusedxml

インストール例（プロジェクトルートで）:

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   あるいはパッケージ化されていれば:
   pip install -e .

注意: 実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください。

---

## 環境変数 (.env)

プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主な環境変数（最低限必要になるもの）:

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- OPENAI_API_KEY=<your_openai_api_key>
- KABU_API_PASSWORD=<kabu_station_password>
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

設定値はコード中の `kabusys.config.settings` からアクセスできます。

---

## 使い方（主要な操作例）

以下は Python REPL やスクリプトから利用する際の例です。実行前に環境変数を適切に設定してください。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（LLM）を実行:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY 環境変数を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print(res)
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ作成され、スキーマが初期化されます
```

- データ品質チェックの単独実行:
```python
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

- マーケットカレンダー更新ジョブ（夜間バッチ）:
```python
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

備考:
- OpenAI の呼び出しには料金がかかります。API キーの管理には注意してください。
- score_news / score_regime は LLM 呼び出し失敗時にフェイルセーフ（スコア 0 等）で継続する設計です。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構造（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS ニュース収集
    - calendar_management.py        — マーケットカレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（スキーマ定義・初期化）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai, research, data の他に strategy/ execution/ monitoring などが将来の公開対象として __all__ に定義されています。

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下の各モジュールを参照してください。）

---

## 注意点 / 実運用向けメモ

- Look-ahead バイアス対策: 多くの関数は date を明示的に受け取り、内部で date.today() を参照しない設計になっています。バックテストでの使用時は target_date の扱いに注意してください。
- DB（DuckDB）への INSERT は可能な限り冪等（ON CONFLICT）で実装されていますが、運用時はバックアップや監査ログを整備してください。
- J-Quants API のレート制限を守るために内部で RateLimiter を使用しています。大量一括処理時は API 制限に注意してください。
- OpenAI 呼び出しにはリトライロジックがありますが、API 料金／待ち時間を考慮してバッチサイズ・呼び出し頻度を調整してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を基に行われます。テスト環境などで自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## さらに詳しく / 拡張ポイント

- strategy / execution / monitoring モジュールは __all__ に含まれており、発注ロジック・ポートフォリオ管理・監視と連携することで実運用フローを構築できます。
- research モジュールの結果を活用してシグナル生成 → audit テーブルに残すワークフローを組むことで、一貫したトレーサビリティを確保できます。
- テスト: 各 API 呼び出し（OpenAI / J-Quants / RSS）部分は外部依存のためモックしやすい設計になっています（内部で差し替え可能な _call_openai_api / _urlopen 等）。

---

もし README に追加してほしい内容（例: CI / テストの実行方法、詳しいテーブルスキーマ、具体的なサンプルスクリプトなど）があれば教えてください。必要に応じてサンプルコードやコマンドを追記します。