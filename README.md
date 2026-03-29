# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォームと研究・戦略モジュールを備えた自動売買基盤のライブラリです。
本リポジトリは ETL（J-Quants 経由の株価 / 財務 / カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（DuckDB）などの機能を提供します。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数
- ディレクトリ構成（主要ファイル一覧）
- 設計上の注意点 / 補足

---

## プロジェクト概要
KabuSys は以下を目的とした内部向けのライブラリ群です。
- J-Quants API からのデータ取得（OHLCV / 財務 / 上場情報 / カレンダー）
- DuckDB を用いたデータ格納・品質チェック・ETL パイプライン
- RSS ニュース収集と前処理（SSRF 対策, トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_scores / マクロセンチメント）
- ファクター計算・研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- 発注／約定に関する監査ログ（audit テーブル群）を DuckDB で初期化・管理

設計方針の要点：
- ルックアヘッドバイアス回避：関数内で datetime.today() 等を直接参照しない。対象日を明示的に渡す設計。
- 冪等性：DB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等で安全に。
- フェイルセーフ：外部 API（OpenAI / J-Quants 等）失敗時は可能な範囲でフォールバックして継続。

---

## 主な機能（モジュール別）
- kabusys.config
  - .env 自動読み込み（.env.local 上書き）、必須設定の取得ラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API の取得/保存ロジック（rate-limit / retry / token refresh 対応）
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存用ユーティリティ（SSRF 対策）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー判定ロジック（営業日判定 / next/prev / get_trading_days 等）
  - audit: 発注／約定の監査テーブル初期化ユーティリティ（init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: RSS から集めた raw_news を銘柄別に LLM でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロ記事の LLM センチメントを合成し market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター算出）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - 監査ログ用の DDL と初期化処理（監査テーブル群・インデックス）

---

## セットアップ手順（開発環境）
例: Python 3.10+ を想定

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - またはプロジェクトの requirements.txt / pyproject.toml に従ってインストールしてください。

   ※ 他に urllib3 等の標準ライブラリで十分な部分が多いですが、OpenAI SDK / duckdb は必須です。

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（およびローカル overrides を `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数
必須や有用な設定（主要なもの）：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY  
  OpenAI を直接呼ぶ場合に利用（score_news / score_regime のデフォルト参照先）。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（Settings.kabu_api_password）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)  
  Slack 通知を行う場合の Bot token とチャンネル ID。

- DUCKDB_PATH (任意)  
  デフォルト DB パス: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  監視用 sqlite のパス: data/monitoring.db

- KABUSYS_ENV (任意)  
  "development" / "paper_trading" / "live" のいずれか（設定ミスは例外）。

- LOG_LEVEL (任意)  
  "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

詳細: Settings クラス（kabusys.config）を参照してください。`.env.example` を用意している場合はそれを参考に .env を作成してください。

読み込み順（優先度）:
- OS 環境変数 > .env.local > .env

---

## 簡単な使い方（コード例）
以下はライブラリを使った最小実行例です。すべて Python スクリプト内から呼び出します。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY でも渡せます）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written scores: {written}")
```

- 市場レジーム判定（regime scoring）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- マーケットカレンダーの利用例
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（主要ファイル）
以下は本リポジトリの主要なモジュールとファイルの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (README の要件に基づくがコード内に該当ファイルがない場合があります)
  - execution/, strategy/  (パッケージ公開用の __all__ にありますが、詳細実装は別途)

（上記に示したファイル以外にも補助ユーティリティ等が含まれる可能性があります）

---

## 設計上の注意点 / ベストプラクティス
- ルックアヘッドバイアスに注意：多くの関数は target_date を引数に取り、内部では現在時刻を参照しないように設計されています。バックテスト等で使用する場合は対象日の取り扱いに注意してください。
- OpenAI / J-Quants の API 呼び出しはネットワーク障害やレート制限を考慮したリトライ実装がありますが、API キーや利用量には注意してください。
- news_collector は SSRF 対策・最大レスポンスサイズ制限等の安全対策を実装しています。外部 RSS を扱う場合はこれらの制約を確認してください。
- DuckDB の executemany に関するバージョン差異（空リストを受け付けない等）を配慮した実装になっています。

---

もし README に追加したい項目（例: CLI コマンド、CI 設定、DB スキーマ定義の詳細、開発ワークフロー、テスト手順）があれば教えてください。必要に応じてサンプル .env.example のテンプレートも作成します。