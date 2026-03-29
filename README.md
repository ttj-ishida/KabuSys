# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集合です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量算出、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含み、バックテスト／運用の基盤として使える設計になっています。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- DuckDB をデータレイヤーに利用（軽量かつ高速な分析向け）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等性を意識したデータ保存（ON CONFLICT / 挿入スキップ等）
- テストしやすいように API 呼び出しを差し替え可能に設計

---

## 機能一覧

- 環境設定読み込み / 管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - 必須環境変数の検証（例：JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- データ ETL（jquants_client 経由）
  - 日次株価（OHLCV）、財務データ、JPXカレンダーの差分取得と保存
  - 差分取得、バックフィル、ページネーション対応
  - レート制御・リトライ・トークン自動リフレッシュ
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue 型で集約（severity により運用判断可能）
- ニュース収集（RSS）と前処理（news_collector）
  - RSS 取得（SSRF 対策、gzip制限、トラッキング除去）
  - raw_news / news_symbols への冪等保存ロジック想定
- ニュース NLP（OpenAI を使用）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメント（ai_scores）を取得（score_news）
  - 市場マクロニュースを LLM で評価し、ETF（1321）MA と組合せて市場レジーム判定（score_regime）
  - gpt-4o-mini + JSON mode 想定、リトライやレスポンス検証を実装
- リサーチ用ファクター計算（research）
  - Momentum / Value / Volatility 等の定量ファクター算出
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- カレンダー管理（market_calendar）
  - 営業日判定、前後の営業日検索、期間内営業日列挙
  - J-Quants からのカレンダー差分取得ジョブ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 まで辿れる監査テーブル定義と初期化ユーティリティ
  - UUID ベースの冪等キー、UTC タイムスタンプ運用を想定

---

## セットアップ手順

前提
- Python 3.10 以上（コード中で `X | Y` 型や future annotations を使用）
- DuckDB を利用するためネイティブ依存が必要な場合があります

1. リポジトリをクローン／フォルダに配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があればそれを使ってください）
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主な必須/推奨環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
  - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネルID（必須）
  - OPENAI_API_KEY: OpenAI を使う機能を使う場合は必須（score_news / score_regime）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

---

## 使い方（代表的な呼び出し例）

以下はライブラリの主要ユーティリティの使い方例です。実際には logging 設定やエラーハンドリングを追加して運用してください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）評価（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使うなら api_key=None
print(f"scored: {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC timezone が設定されます
```

- カレンダーヘルパー
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS フィードの取得（ニュースコレクタの内部ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注記
- OpenAI 呼び出しは API のレート制限／費用に注意してください。
- ETL・AI の各関数は内部で例外を扱い、フェイルセーフを取る実装が多いですが、ログを監視し必要に応じてリトライやアラートを行ってください。

---

## ディレクトリ構成（主要ファイル）

概観（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境設定・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを銘柄別に集約して OpenAI でスコア化
    - regime_detector.py      — ETF MA とマクロニュースを組合せた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API client（取得 + DuckDB 保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL の外部インターフェース（ETLResult 再エクスポート）
    - calendar_management.py  — 市場カレンダー関連ユーティリティ
    - news_collector.py       — RSS 収集・前処理
    - quality.py              — データ品質チェック（各種チェック）
    - stats.py                — 汎用統計ユーティリティ（z-score 等）
    - audit.py                — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリーなど
  - ai, research, data 以下に多数の補助関数やユーティリティが含まれます。

---

## 運用上の注意 / ベストプラクティス

- 環境分離
  - KABUSYS_ENV を使って開発 / paper_trading / live を切り分けてください。live 環境ではより厳格なログ・アラートを推奨します。
- シークレット管理
  - API キーやトークンは直接リポジトリに入れず、環境変数や安全なシークレット管理ツールを使用してください。
- ロギング・監視
  - ETL・AI 呼び出しは外部依存があるため、ログ監視（エラー・WARNING のアラート化）を行ってください。
- テスト
  - OpenAI 呼び出しやネットワークIO はモック可能な設計です（モジュール内の _call_openai_api や _urlopen を patch する等）。
- データ整合性
  - ETL の品質チェック結果（QualityIssue）は停止の判断材料になります。自動停止するかどうかは運用ポリシーに沿って決めてください。

---

もし README に含めたい追加のセクション（例：CI 設定、具体的な .env.example ファイル全文、運用チェックリスト、デプロイ手順）があれば教えてください。必要に応じて追記します。