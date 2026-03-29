# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants API によるデータ取得、DuckDB ベースの ETL、ニュースの NLP 処理（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ管理などを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける実装（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中心としたローカルデータストア
- J-Quants / OpenAI API 呼び出しに対するリトライ・レート制御・フェイルセーフ
- ETL / 品質チェック / 監査ログの冪等性を重視

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーなどを差分取得して DuckDB に保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
- データ品質チェック
  - 欠損値、重複、スパイク、日付不整合の検出（quality モジュール）
- ニュース収集 / NLP
  - RSS からニュースを取得し raw_news に保存（news_collector）
  - OpenAI を使った銘柄ごとのニュースセンチメントスコアリング（news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日MA 乖離とマクロニュース LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの初期化（data.audit.init_audit_schema / init_audit_db）
- 環境設定管理
  - .env / .env.local の自動読み込み、環境変数アクセス用 Settings（config.settings）

---

## 必要な環境変数

主要な環境変数（README にある関数が依存するもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行モード (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env ロード:
- パッケージ起動時、プロジェクトルート（.git または pyproject.toml が見つかる）から `.env` を読み込み、続けて `.env.local` を上書きで読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: Settings の必須プロパティは未設定時に ValueError を送出します。

---

## セットアップ手順

1. リポジトリをクローン（あるいはソースを配置）
2. Python 環境を準備（推奨: 仮想環境）
3. 必要パッケージをインストール

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発インストール（プロジェクトルートに pyproject.toml/setup.cfg がある想定）
pip install -e .
```

4. 環境変数（または .env/.env.local）を設定
- .env.example を参照して .env を作成してください（このリポジトリ内で .env.example がある想定）。
- 最低限 JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（news/regime 機能を使う場合）は設定が必要です。

5. DuckDB データベースファイルの初期化（任意）
- 監査ログ専用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```
- その他スキーマ初期化はプロジェクトのスキーマ初期化ユーティリティに従ってください（本 README の範囲外）。

---

## 使い方（簡易ガイド）

以下に代表的な利用例を示します。すべて Python API 呼び出し例です。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定しなければ今日扱い（内部で調整）
print(result.to_dict())
```

2) ニュースのスコア付け（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で環境変数 OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

3) 市場レジーム判定（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマの初期化（既存の DuckDB 接続へ）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

ログ・例外:
- 多くの API は失敗時にログを出し、可能な限りフェイルセーフ（処理継続）する設計です。致命的なエラーは例外として上位へ伝搬します。

---

## ディレクトリ構成（主なファイル・モジュールの説明）

プロジェクトの主要パッケージは `src/kabusys` に配置されています。以下は抜粋と概要です。

- src/kabusys/__init__.py
  - パッケージ定義・バージョン

- src/kabusys/config.py
  - 環境変数読み込み（.env/.env.local 自動ロード）および Settings クラス

- src/kabusys/ai/
  - news_nlp.py: ニュース記事を OpenAI でセンチメント分析して ai_scores に書き込む
  - regime_detector.py: ETF MA 乖離とマクロニュースの LLM スコアを合成して市場レジームを判定

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline.py: ETL パイプライン（run_daily_etl 他）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集と raw_news への保存ロジック
  - calendar_management.py: 市場カレンダー管理（営業日判定・更新ジョブ）
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ定義・初期化

- src/kabusys/research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
  - __init__.py: 主要関数群を再エクスポート

- src/kabusys/ai/__init__.py
  - score_news を公開

その他、細かいユーティリティや補助モジュールが含まれます。各モジュールには docstring と設計ノートが豊富に記載されていますので、内部実装や挙動の詳細は該当ファイルを参照してください。

---

## 開発・運用上の注意

- OpenAI と J-Quants の API キーは適切に管理してください。README にある環境変数を .env に記載する際はアクセス権に注意してください。
- DuckDB のファイルパス（デフォルト data/kabusys.duckdb）は Settings.duckdb_path で制御されます。バックアップ・ローテーションを運用で考慮してください。
- news_collector は外部 RSS を取得するため SSRF や巨大レスポンス対策を実装していますが、運用環境でのネットワーク設定やプロキシに応じて適切にテストしてください。
- ETL は差分更新・バックフィルを行う設計です。初回ロードや過去データのリロード時はパラメータに注意してください。
- DuckDB のバージョン差異（executemany の挙動など）に留意していますが、運用時は使用する DuckDB バージョンでの動作確認をお願いします。

---

もし README に追加したい内容（例: CLI コマンド、.env.example の内容、CI 設定、実運用の推奨設定等）があれば教えてください。必要に応じて追記します。