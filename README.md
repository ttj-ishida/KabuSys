# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買サブシステム群を集めたライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能
- 必要な環境変数
- セットアップ手順
- 使い方（簡単な例）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量生成・AIによるニュース解析・市場レジーム判定・監査ログなど、アルゴリズムトレーディング用の基盤処理群を提供します。  
設計上、バックテストでのルックアヘッドバイアスを避ける工夫や、API 呼び出しの堅牢なリトライ/レート制御、DuckDB を用いたローカル永続化などが実装されています。

---

## 主な機能

- データ取得（J-Quants API 経由）
  - 日次株価（OHLCV）
  - 財務データ（四半期など）
  - JPX マーケットカレンダー
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
- ニュース収集と前処理（RSS）
  - URL 正規化・SSRF 防御・Gzip サイズチェック
- ニュース NLP（OpenAI を利用した銘柄別センチメント）
  - news_nlp.score_news(conn, target_date)
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  - ai.regime_detector.score_regime(conn, target_date)
- ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - research.calc_momentum / calc_value / calc_volatility など
- 統計ユーティリティ
  - zscore_normalize など
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（signal → order_request → executions のトレーサビリティ）
  - audit.init_audit_db / init_audit_schema

---

## 必要な環境変数

（.env / .env.local から自動読み込みします ※後述）

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（必要な場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

OpenAI：
- OPENAI_API_KEY — news_nlp / regime_detector などで使用（引数で注入可能）

その他オプション：
- KABUSYS_ENV — environment ('development' / 'paper_trading' / 'live')（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 をセット）

.env の自動ロード挙動：
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を判定し、優先順は OS 環境変数 > .env.local > .env です。  
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効にできます。

---

## セットアップ手順

1. Python と仮想環境の準備（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（一例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使ってください。)

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env を置くか、CI/OS の環境変数として設定してください。
   - 最低でも JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（news/AI を利用する場合）を設定してください。

例 (.env):
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345678
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

以下はライブラリの主要な使い方例です。実行はプロジェクトの仮想環境内で行ってください。

- DuckDB 接続を作成して日次 ETL を実行する例:

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # 今日を対象に ETL を実行
print(result.to_dict())
```

- ニュースセンチメント（特定日）を計算して ai_scores に書き込む例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームスコアを算出して market_regime に書き込む例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する例:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査 DB に使うか別パスを指定
conn = init_audit_db(settings.duckdb_path)
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 研究用ユーティリティ（ファクター計算・IC 計算）例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2026, 3, 20)
momentum = calc_momentum(conn, t)
forward = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## ディレクトリ構成（主要ファイル）

(プロジェクトルート)/src/kabusys/
- __init__.py — パッケージ初期化（__version__ 等）
- config.py — 環境変数 / 設定読み込み、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントの集約・OpenAI 呼び出し・ai_scores 書込
  - regime_detector.py — ETF(1321) MA とマクロニュースを使った市場レジーム判定
- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - jquants_client.py — J-Quants API クライアント・保存関数
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - etl.py — ETLResult の再エクスポート
  - audit.py — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

（上記は抜粋。実装は各モジュール内の docstring に詳細があります。）

---

## 注意事項 / 運用メモ

- OpenAI（gpt-4o-mini など）の呼び出しは API キーが必要です。score_news / score_regime は api_key 引数で直接渡すこともできます。
- J-Quants API はレート制限があり、jquants_client は内部でスロットリングと再試行を行います。J-Quants の認証はリフレッシュトークン経由です（JQUANTS_REFRESH_TOKEN）。
- ETL とリサーチ処理はルックアヘッドバイアスの防止を考慮して設計されています。関数は内部で date.today() を参照しないか、明示的に target_date を受け取ります。
- .env の自動読み込みはプロジェクトルート検出に依存します。CI 環境やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB のバージョン差異に起因する挙動（executemany の空リスト扱い等）に気を付けていますが、実運用前に使っている DuckDB バージョンで動作確認してください。
- news_collector では defusedxml と SSRF 対策を実装しています。外部 RSS を収集する場合はソースの安全性に注意してください。

---

README の内容はモジュール内 docstring を要約したものです。詳細は各モジュールの docstring と関数定義を参照してください。必要があれば README にチュートリアルや具体的な運用手順（cron / コンテナ化 / CI など）を追加できます。どういった追加情報が必要か教えてください。