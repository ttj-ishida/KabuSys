# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）と自動読み込み
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株システム向けに設計された内部ライブラリ群で、以下を主に提供します。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への冪等保存
- ETL パイプライン（日次 ETL 実行）
- ニュース収集（RSS）とニュースの前処理・センチメント化（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- 研究用途のファクター計算・統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（シグナル→発注→約定をトレース可能にするテーブル群）

設計上のポイント：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を無理に参照しない設計）
- DuckDB を主体に SQL+Python で処理（外部 heavy ライブラリに依存しない）
- 外部 API 呼び出しはリトライ・バックオフやレート制御を備える
- 冪等性を重視（DB 保存は ON CONFLICT DO UPDATE / DO NOTHING 等）

---

## 主な機能一覧

- kabusys.config
  - 環境変数管理、自動 .env ロード（プロジェクトルート検出）
  - settings オブジェクト経由でアプリ設定を取得

- kabusys.data
  - jquants_client: J-Quants API 呼び出し・取得（株価・財務・カレンダー）と DuckDB への保存
  - pipeline / etl: 日次 ETL（差分取得、保存、品質チェック）
  - news_collector: RSS 収集、前処理、raw_news への保存（SSRF 対策、圧縮・サイズ制限）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化などの統計ユーティリティ
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）

- kabusys.ai
  - news_nlp.score_news: 指定日ウィンドウのニュースを LLM で銘柄別センチメント化し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存

- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン、IC（情報係数）、統計サマリー、ランク変換など

---

## セットアップ手順

前提: Python 3.10+（型注釈や union 型の記法による）

1. リポジトリをクローンまたはプロジェクトルートに配置（pyproject.toml または .git があることを推奨）。
2. 仮想環境を作成・有効化（任意だが推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .\.venv\Scripts\activate    (Windows)

3. 必要パッケージをインストール（最低限）:
   - duckdb
   - openai
   - defusedxml
   - （その他、ロギング等は標準ライブラリ）

例:
   pip install duckdb openai defusedxml

もしパッケージ化されたセットアップがあるなら:
   pip install -e .

4. 環境変数を準備（詳細は次節）。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは無効化可能）。

5. DuckDB 用ディレクトリを作る（デフォルトの DB パスを使用する場合）:
   mkdir -p data

---

## 環境変数（.env）と自動読み込み

config モジュールはプロジェクトルート（.git または pyproject.toml を上位に探索）を検出し、`.env` → `.env.local` の順に読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。

自動ロードを無効にする:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

重要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 実行時に参照）
- DUCKDB_PATH           : デフォルト DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL             : ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（コード例）

以下は主要な機能を呼び出す最小例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を生成する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定を行う（market_regime に書き込む）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- ファクター計算（研究用途）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- 設定値を参照する:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）を参照します。api_key 引数で直接渡すことも可能です。
- J-Quants API は認証トークン取得（get_id_token）やページネーション、レート制御、リトライを備えています。JQUANTS_REFRESH_TOKEN を .env に設定してください。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの一覧（src/kabusys 配下）です。README 用に抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM スコアリング（ai_scores）
    - regime_detector.py             — 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース再公開
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — 市場カレンダー管理（営業日判定等）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（z-score 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py         — 将来リターン / IC / summary / rank
  - monitoring/                       — 監視・モニタリング系（存在するなら）
  - strategy/                         — 戦略／実行ロジック（存在するなら）
  - execution/                        — 発注実行周り（存在するなら）
  - その他ユーティリティ群

（注）実際に存在するサブパッケージは上記コードベースのとおりです。strategy, execution, monitoring はパッケージ初期化で __all__ に含まれていますが、実装が別ファイルにある場合があります。

---

## 開発・運用上の注意

- 環境変数は機密情報を含みます。リポジトリに直接コミットしないでください。
- OpenAI 呼び出しはコストとレート制限に注意してください。news_nlp / regime_detector はリトライ・バックオフを実装していますが、運用時には API キーやコスト管理が必要です。
- J-Quants API にはレート制限（120 req/min）があるため、jquants_client はレート制御を行います。大量取得の際は注意してください。
- DuckDB のバージョン差異により executemany の空リスト取り扱いなど注意点があるため、関数内で保護処理が入っています。
- テスト時に環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい操作例（CI 用コマンド、Docker 構成、より詳細な .env.example、マイグレーションやスキーマ初期化手順など）があれば、必要に応じて追記します。