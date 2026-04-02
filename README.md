# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、研究用ユーティリティ、監査ログ（約定トレーサビリティ）などを一貫して提供します。

主な設計方針は「バックテスト時のルックアヘッドバイアス回避」「DuckDB を中心としたローカル永続化」「外部 API 呼び出しのフェイルセーフ化とリトライ」「SQL ベースで効率的に処理すること」です。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日次 OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（fetch / save）
  - 日次 ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを順に実行
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付整合性（未来日・非営業日）を検出
- ニュース処理
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols テーブルへの冪等保存ロジック
- NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント取得（gpt-4o-mini を想定） → ai_scores へ保存（score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を合成して市場レジーム判定（bull/neutral/bear）（score_regime）
  - LLM 呼び出しはリトライ・エラーハンドリング済み（フェイルセーフで 0.0 にフォールバック）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数から設定自動ロード（プロジェクトルート検出）および Settings API

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK; 現コードは chat.completions の JSON mode を利用)
- defusedxml
- （その他標準ライブラリ）

※ 実行環境により追加パッケージが必要になる場合があります。pip install 時に依存関係を確認してください。

---

## セットアップ手順（開発 / 実行）

1. リポジトリをクローン / 配布パッケージを配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （パッケージ配布用に setup/pyproject があれば pip install -e .）
4. 環境変数（必須）を設定
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
   - SLACK_BOT_TOKEN: Slack 通知が必要な場合
   - SLACK_CHANNEL_ID: Slack 通知の送信先
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行時に使用）
   - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime）
   - （任意）KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, 各種監視閾値、KABUSYS_ENV 等
5. .env 自動ロードについて
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込みします。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: プロジェクトルートに .env を配置して以下を設定
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=secret
```

---

## 使い方（代表的な操作例）

下記は Python REPL やスクリプトから利用する簡単な例です。DuckDB 接続や OpenAI API キーは Settings または引数から注入できます。

- 共通インポート
```python
import duckdb
from kabusys.config import settings
```

- DuckDB 接続（デフォルト DB パス: data/kabusys.duckdb）
```python
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコア付け（OpenAI が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # api_key を引数で渡すことも可能
print(f"written {n_written} ai_scores")
```

- 市場レジームスコア（ETF 1321 の MA200 とマクロセンチメントの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログテーブルの初期化（専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以後 audit_conn を監査用に使用
```

- 研究用ファクター計算（例：モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# momentum は dict のリスト（各要素: date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

- 設定参照（Settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

---

## 注意点 / 運用メモ

- Look-ahead バイアス防止
  - 多くのモジュールは date.today() を直接参照せず、関数呼び出し時の target_date を明示的に渡す設計です。バックテストでは必ず過去の状態のみ参照するよう target_date を固定してください。
- OpenAI / J-Quants エラーハンドリング
  - LLM 呼び出しはリトライやフォールバック（0.0）を行うため、API エラーでも処理継続する設計です。ただし設定漏れ（API キー未設定）は ValueError を投げます。
- DB 書き込みは原則冪等（ON CONFLICT で上書き）を採用しています。
- news_collector は RSS パースに defusedxml を利用し、SSRF 対策・レスポンスサイズ制限などセキュリティ考慮済みです。
- 自動 .env 読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存します。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

---

## ディレクトリ構成（主なファイル）

（ルート = src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     --- 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  --- ニュースセンチメント（score_news）
    - regime_detector.py          --- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           --- J-Quants API クライアント / save_* / fetch_*
    - pipeline.py                 --- ETL パイプライン（run_daily_etl 等）
    - etl.py                      --- ETLResult の再エクスポート
    - news_collector.py           --- RSS 取得・前処理・保存
    - calendar_management.py      --- 市場カレンダーの判定・更新ロジック
    - quality.py                  --- データ品質チェック
    - stats.py                    --- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                    --- 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py          --- モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py      --- 将来リターン/IC/統計サマリー 等
  - ai/、research/、data/ に他の補助モジュールあり

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for NLP): OpenAI API キー（score_news / regime_detector）
- KABU_API_PASSWORD (必須 if using kabu API)
- KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須 if Slack を使う)
- SLACK_CHANNEL_ID (必須 if Slack を使う)
- DUCKDB_PATH (任意): デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意): デフォルト "data/monitoring.db"
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視用）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL: "DEBUG" / "INFO" / ...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

---

## 最後に

この README はコードベースの主要機能と典型的な利用方法をまとめたものです。詳細な挙動（SQL スキーマ、プロンプト定義、パラメータ値、エラーハンドリングの細部等）は各モジュールの docstring を参照してください。開発・運用にあたっては API キーや DB パスなどのシークレット管理と権限設定を十分に行ってください。