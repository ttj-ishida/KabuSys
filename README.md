# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を用いたセンチメント）、ファクター計算、マーケットカレンダー管理、監査ログスキーマなど、システム全体の基盤機能を提供します。

## 主な目的
- J-Quants API を用いた株価・財務・カレンダーデータの差分取得・保存（DuckDB）
- RSS ベースのニュース収集と LLM を用いた銘柄センチメント計算
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- Data（kabusys.data）
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページング・保存）  
  - pipeline: 日次 ETL 実行（run_daily_etl）
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - news_collector: RSS 収集処理（SSRF 対策、トラッキング除去）
  - audit: 監査ログスキーマ初期化 / 専用 DB 初期化
  - quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュースを組合せて市場レジーム判定
- Research（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary / rank）
- 監視・実行（エグゼキューションや Slack 通知等の機能は別モジュールで実装想定）

---

## セットアップ

前提
- Python 3.10+ を推奨（Union 型に | を使用）
- DuckDB、OpenAI SDK、defusedxml 等を使用

推奨的な仮想環境の作成例（Unix 系）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 開発インストール（ソース配布がある場合）
   - pip install -e .

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- SLACK_BOT_TOKEN: Slack ボットトークン（任意だが通知を使う場合は必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知用）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます（OS 環境変数を保護）。
- .env.local は .env を上書きします（ただし OS 変数は保護されます）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env.example
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

以下は基本的な使い方のサンプルです。実際にはエラーハンドリングやログ設定を追加してください。

1) DuckDB 接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成する（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
print(f"scored {count} codes")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成され、UTC タイムゾーン設定が行われます
```

5) ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

ログ設定例（推奨）
- 標準 logging を用いて LOG_LEVEL に合わせてログ出力を行ってください。

---

## 注意点 / 設計上の考慮
- Look-ahead bias 防止:
  - 多くの関数が date や target_date を明示的に受け取り、内部で date.today() を不用意に参照しない設計です。バックテスト使用時は適切に過去データだけを用いてください。
- 冪等性:
  - J-Quants データ保存や ETL は基本的に冪等（ON CONFLICT DO UPDATE）で実装されています。
- フェイルセーフ:
  - OpenAI/API の失敗時にはスコアを 0 にフォールバックする等、処理を中断させない工夫があります（ただし重大な初期設定不足は例外になります）。
- セキュリティ:
  - news_collector は SSRF 対策、XML の安全パーサ（defusedxml）等を取り入れています。
- DB 依存:
  - 実行には DuckDB（python duckdb）が必要です。監査用は別 DB を使うことも可能です（init_audit_db）。

---

## ディレクトリ構成（主要ファイル・モジュール）
src/kabusys/
- __init__.py
- config.py                     - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  - ニュース NLP（score_news）
  - regime_detector.py           - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（fetch/save 系）
  - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
  - etl.py                       - ETLResult 型再エクスポート
  - calendar_management.py       - マーケットカレンダー管理
  - stats.py                     - 統計ユーティリティ（zscore_normalize）
  - quality.py                   - データ品質チェック
  - audit.py                     - 監査ログスキーマ初期化 / init_audit_db
  - news_collector.py            - RSS 収集と前処理
- research/
  - __init__.py
  - factor_research.py           - ファクター計算（momentum/value/volatility）
  - feature_exploration.py       - forward returns / IC / summary / rank
- ai/__init__.py
- research/__init__.py

（上記に加え、strategy / execution / monitoring 等のパッケージが __all__ に示されていますが、ここでは data/ai/research を中心に実装されています）

---

## 開発 / 貢献
- コードスタイル: docstring / 型注釈を重視。ユニットテストを追加して品質を担保してください。
- ローカルでの実行:
  - .env に必須キーを設定後、DuckDB を作成して ETL やスコア処理を実行してください。
- テスト:
  - OpenAI / ネットワーク依存部分はモックしてユニットテストを作成してください（score_chunk や _call_openai_api は差し替え可能に設計されています）。

---

必要であれば、README に「API リファレンス」「具体的な .env.example」「サンプル cron / systemd ジョブ」や「開発用 Docker イメージの例」などの追加セクションも作成します。どの内容を優先して追加しますか？