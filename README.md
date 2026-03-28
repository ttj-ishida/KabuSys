# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買補助ライブラリです。J-Quants からのデータ取得（ETL）、ニュース収集と NLP スコアリング（OpenAI）、ファクター計算、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な利用シーン:
- 日次 ETL による価格・財務・カレンダーの差分取得と保存
- ニュースの収集 → LLM による銘柄センチメント評価（ai_scores）
- マクロセンチメント＋MA 乖離からの日次市場レジーム判定
- ファクター計算・IC 解析などのリサーチ用途
- 発注・約定の監査ログ初期化（監査 DB）

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）自動ロード（必要に応じて無効化可能）
  - settings オブジェクト経由で設定値にアクセス可能
- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの差分取得（株価 / 財務 / 市場カレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット、リトライ、トークン自動リフレッシュ対応
  - ページネーション対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への保存想定
- ニュース NLP / マクロレジーム（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI へ送信して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む
  - OpenAI 呼び出しはリトライ・フェイルセーフ設計
- 研究（kabusys.research）
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算 / IC（Spearman） / 統計サマリー
  - zscore 正規化ユーティリティ（kabusys.data.stats）
- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を利用した営業日判定 / next/prev_trading_day / get_trading_days
  - API からの夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査向けに UTC タイムスタンプ固定、冪等性を考慮した設計

---

## 必要条件

- Python 3.10 以上（ソース中での型アノテーションに「|」が使用されているため）
- 以下の主要依存ライブラリ（プロジェクトの requirements.txt がある場合はそちらを参照してください）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime など

（実行 / 開発にあたっては他に linters / test フレームワークなどを追加する場合があります）

---

## 環境変数（主なもの）

このプロジェクトは環境変数から設定を取得します（.env / .env.local を自動ロード）。主要なキー:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知チャネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env.example を参考に .env を作成してください（リポジトリに存在する場合）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . や pip install -r requirements.txt を使用）

4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.local を開発用に利用可）
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードを一時的に無効化するには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB の初期スキーマ（必要に応じて）を作成する
   - スキーマ初期化用のユーティリティがあればそれを実行するか、監査DBを初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は主要な操作の使用例です。各関数は DuckDB 接続（duckdb.connect(...) で得られる接続）を受け取ります。

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付与
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None だと OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化（発注 / 約定テーブル）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って order_requests / executions の挿入やクエリが可能
```

- 研究モジュール（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- カレンダー操作
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- 多くの API 呼び出しは OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等を要求します。
- 外部 API 呼び出し部分はネットワークやレート制限などの外的要因で失敗する可能性があるため、例外処理やログを確認してください。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置されています）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の読み込み・settings オブジェクト
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM スコアリングと ai_scores への書き込み
  - regime_detector.py  — マクロセンチメント + MA200 で市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存関数）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 取得と前処理（SSRF 対策、正規化）
  - calendar_management.py — market_calendar 管理・営業日判定
  - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログスキーマ初期化（signal_events, order_requests, executions）
- src/kabusys/research/
  - __init__.py
  - factor_research.py   — Momentum / Volatility / Value ファクター算出
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- その他
  - data/（デフォルトの DuckDB や SQLite 用ディレクトリ）
  - .env / .env.local（プロジェクトルートに配置して自動読み込み可能）

---

## 設計上の注意点 / ベストプラクティス

- Look-ahead バイアス回避:
  - モジュール内部の多くは datetime.today() を無条件に参照せず、外部から target_date を与える形で動作します。バックテスト等では必ず適切な target_date を指定してください。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。テスト時や一時的に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- フェイルセーフ:
  - OpenAI / J-Quants の API 呼び出しはリトライやフォールバック（例: macro_sentiment=0.0）を行う設計です。Network エラー時はログを確認してください。
- DuckDB との互換性:
  - DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装になっていますが、実際の運用では使用する DuckDB バージョンでの動作確認を推奨します。

---

## ライセンス / 貢献

（README に含めるべきライセンス情報があればここに記載してください）

貢献の流れ:
- Issue を立てる
- Fork → ブランチ作成 → Pull Request

---

もし README に追加したい項目（例: CI / テストの実行方法、より詳細な API 使用例、スキーマ定義 SQL、requirements.txt の正確な内容など）があれば教えてください。必要に応じて追記・整備します。