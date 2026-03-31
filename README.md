# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）、品質チェック、ニュース NLP（LLM）による銘柄センチメント算出、市場レジーム判定、研究用ファクター計算、監査ログ管理などを提供します。

主な設計方針は「ルックアヘッドバイアスの抑制」「冪等性」「フェイルセーフ（API失敗時の継続）」「DuckDB を中心としたオフライン分析可能な設計」です。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API 経由で株価（日足）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - ETL の差分・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィードからの記事収集、前処理、raw_news への冪等保存、銘柄紐付けロジック
  - SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去など堅牢な実装
- ニュース NLP（LLM）
  - 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ保存
  - バッチ・リトライ・レスポンス検証ロジック搭載
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定
  - LLM 呼び出しのリトライやフェイルセーフ対応
- 研究（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリー、Z-score 正規化等
- 監査ログ（audit）
  - シグナル → 発注 → 約定までトレース可能な監査スキーマを DuckDB に初期化・管理
  - 冪等キー（order_request_id / broker_execution_id）設計、UTC タイムスタンプ運用
- カレンダー管理
  - market_calendar を用いた営業日判定／次営業日／前営業日取得／カレンダー更新ジョブ等

---

## 要件（推奨）

- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他の標準ライブラリ：urllib, datetime, json, logging 等）

パッケージ依存はリポジトリに requirements.txt がある想定で、下記のようにインストールしてください：

pip install -r requirements.txt

（requirements.txt がない場合は上記の主要パッケージを個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. Python 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -r requirements.txt

   または最低限：

   pip install duckdb openai defusedxml

4. 環境変数設定（.env ファイルをプロジェクトルートに置くと自動ロードされます）
   - 自動ロードはデフォルトで有効です。テスト時などに無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（アプリを動かすため）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client の get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（システム内で参照）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視・通知に使用）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意／実行時に必要となることが多い:
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で環境変数参照、引数で渡すことも可能）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

例: .env（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と実行例）

以下はライブラリを直接インポートして使う例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 設定読み取り

```python
from kabusys.config import settings

print(settings.duckdb_path)      # Path オブジェクト
print(settings.is_live)          # ランタイム環境判定
```

- DuckDB 接続の作成（デフォルトパスを使用）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（データ取得・品質チェック込み）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ本日で実行
print(result.to_dict())
```

- ニュース NLP（銘柄毎センチメント算出）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で指定可能
print(f"written: {n_written}")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で指定可能
```

- 監査ログスキーマの初期化（別 DB に監査専用 DB を作る例）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成される
```

- 研究用ファクター計算の呼び出し例

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date":..., "code":..., "mom_1m":..., "ma200_dev":... }, ...]
```

- カレンダー関連ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

注意:
- OpenAI 呼び出しを伴う関数（score_news, score_regime 等）は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は「ルックアヘッドバイアスを避ける」ために内部で date.today() を参照しない設計です。必ず target_date を指定してバッチ実行する運用が推奨されます。

---

## 便利な挙動 / 設定

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を自動ロードします。
  - テストなどで無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境名検証
  - KABUSYS_ENV の有効値: development, paper_trading, live
- ログレベル検証
  - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / 設定管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング、ai_scores 書込み
    - regime_detector.py  — 市場レジーム判定（ma200 + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETLResult の再エクスポート
    - stats.py            — zscore_normalize 等のユーティリティ
    - quality.py          — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理（営業日判定 / 更新ジョブ）
    - news_collector.py   — RSS ニュース収集・正規化・保存
    - audit.py            — 監査ログ（signal/order/execution）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン, IC, factor_summary 等
  - monitoring/ (存在は README に合わせて想定)
  - strategy/, execution/, monitoring/ など（パッケージ公開の __all__ に含まれます）

---

## 運用上の注意点

- DuckDB のバージョン依存や executemany の空リスト扱い等、実行環境の DuckDB バージョンに注意してください（コード内で互換性対策あり）。
- OpenAI / J-Quants API の呼び出し回数やレート制限に注意して運用してください（jquants_client にレートリミッタ・リトライ実装あり）。
- LLM 呼び出しは外部 API のため失敗する場合があります。本実装は多くの箇所でフォールバック（0.0 等）や部分失敗時の保護（既存データを消さない等）を行いますが、運用時に監視を組み合わせてください。
- 監査ログ（audit）は削除しない前提で設計されています。DB の保存先・バックアップ方針を事前に決めておくことを推奨します。

---

もし README に追加してほしい具体的なサンプル（.env.example、Dockerfile、CI ワークフロー、デプロイ手順など）があれば教えてください。必要に応じて追記します。