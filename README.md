# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL、ニュースNLP（LLM利用）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログなど、トレーディング運用・研究に必要な主要コンポーネントを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（重要）
- 使い方（代表的なAPI例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を想定したモジュール群を提供します。

- J-Quants API からのデータ取得（株価・財務・カレンダー）および DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース記事収集・前処理・LLM による銘柄センチメント付与（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- ニュース収集（RSS）でのセキュアな取得ロジック（SSRF対策等）

設計上の特徴：
- ルックアヘッドバイアス回避（API呼び出しや日付処理で現在時刻を直接参照しない旨の設計）
- DuckDB を中心としたローカル分析・永続化
- 冪等保存（ON CONFLICT / UPDATE）やリトライ・レート制御など実運用を意識した実装

---

## 主な機能（モジュール一覧・要約）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートを探して .env/.env.local を読み込む）
  - settings オブジェクト経由で各種設定値を取得（J-Quants トークン、Kabu API 設定、DB パス 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証 / レートリミット / リトライ）
  - pipeline: ETL（差分取得・保存・品質チェック）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理（SSRF対策・トラッキング除去・id生成）
  - calendar_management: 市場カレンダー管理＆営業日判定ユーティリティ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 指定日ウィンドウの記事を LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を合成して market_regime テーブルへ書き込む
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型 | を使用しているため）
- DuckDB を用いるため、依存パッケージが必要

1. リポジトリをクローン（あるいはパッケージソースを取得）
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限の例）
   - pip install duckdb openai defusedxml
   - その他: requests 等が必要な場合は追加（本コードは urllib を使用）
   - 開発時に editable install:
     - pip install -e .

（注）pyproject.toml / requirements.txt がある場合はそれに従ってください。

---

## 環境変数（主要なもの）

プロジェクトは .env ファイルまたは環境変数で設定を行います。プロジェクトルート（.git または pyproject.toml がある場所）を起点に自動で .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

重要な環境変数（settings 経由で参照）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETLで使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（約定用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB など（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEM/DISK 閾値: 監視設定（任意）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

.env.example を用意して必要な値を設定してください（JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY は特に必須となる関数があります）。

---

## 使い方（代表的な例）

以下は代表的な Python スニペット例です。実行はプロジェクトルートで行うか、パッケージをインストールして下さい。

- DuckDB 接続の作成（設定の duckdb_path を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（ただし内部で営業日調整あり）
print(result.to_dict())
```

- ニューススコアリング（LLM を用いて銘柄ごとの ai_scores を書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に API キーを渡すことも可能（None の場合は ENV を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を基に daily regime を作成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査用のスキーマを DuckDB に作成）
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.config import settings

# 既存接続に対してスキーマを初期化
init_audit_schema(conn, transactional=True)

# 監査専用 DB を作成して接続を取得
audit_conn = init_audit_db(settings.duckdb_path)
```

- 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]
```

- RSS フィード取得（ニュース収集）の例
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
# articles は NewsArticle 型のリスト（id, datetime, source, title, content, url）
```

注意:
- score_news / score_regime は OpenAI API キーが必要です。api_key 引数に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- jquants_client のデータ取得は J-Quants の認証トークンが必要です（settings.jquants_refresh_token）。

---

## 運用上のポイント・仕様メモ

- .env 自動読み込み:
  - プロジェクトルートを .git または pyproject.toml から探索し、自動的に .env と .env.local を読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効化されます（テスト時に便利）。
- 冪等性:
  - J-Quants のデータ保存は ON CONFLICT DO UPDATE を利用しているため再実行耐性があります。
  - audit.order_requests などにも冪等キー設計が組み込まれています。
- LLM 呼び出し:
  - gpt-4o-mini を想定し、JSON mode を使って厳密な JSON 出力を期待します。
  - API エラー時はフォールバックやリトライ処理が入る設計ですが、キーが未設定だと例外が出ます。
- セキュリティ:
  - news_collector は SSRF 対策や受信サイズ制限（MAX_RESPONSE_BYTES）などを実装しています。
- DuckDB のバージョン差分に注意:
  - 一部実装は DuckDB の executemany / 列バインド 挙動に依存した実装上の考慮が入っています（空リストの executemany を避ける等）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                          -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                       -- ニュースNLP（score_news）
  - regime_detector.py                -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                 -- J-Quants API クライアント + 保存関数
  - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
  - etl.py                            -- ETLResult の再エクスポート
  - quality.py                         -- 品質チェック
  - news_collector.py                 -- RSS 収集・前処理
  - calendar_management.py            -- 市場カレンダーと営業日判定
  - stats.py                          -- 統計ユーティリティ（zscore_normalize 等）
  - audit.py                          -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                -- モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py            -- 将来リターン・IC・統計サマリー
- ai/__init__.py
- research/__init__.py
- その他モジュール...

（ソースは src パッケージ構成を採用しています）

---

## 最後に

この README はソース内ドキュメント（各モジュールの docstring）を要約したものです。各関数の詳細な振る舞いや引数仕様、戻り値、例外については対象モジュールの docstring を参照してください。

何か特定の使い方（例: ETL スケジュール設定、バックテスト用のデータエクスポート、発注連携のサンプル）について README に追記を希望する場合は、用途を教えてください。