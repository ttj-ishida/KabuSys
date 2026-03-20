# KabuSys

日本株向け自動売買基盤のコアライブラリ（パッケージ）です。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ等の基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定したトレーディングプラットフォームのコアモジュール群です。

- Data Layer: J-Quants からの株価・財務・カレンダー取得と DuckDB への永続化（差分保存／冪等）
- Processed / Feature Layer: daily prices → ファクター計算 → Z スコア正規化 → features テーブル保存
- Strategy Layer: features + ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成
- Execution / Audit: 発注・約定・ポジション管理・監査ログ用のスキーマ（発注処理は別モジュールで実装）
- Research: ファクター検証・IC/フォワードリターン計算等の補助関数（研究用）

設計上の要点：
- DuckDB を永続層に利用（スキーマ定義と初期化を提供）
- J-Quants API へのリクエストはレート制御・リトライ・トークン自動リフレッシュを実装
- RSS ニュース収集は SSRF 対策・XML 脆弱性対策・トラッキング除去等の安全処理を実装
- 多くの操作は冪等に設計（ON CONFLICT / トランザクション処理）

---

## 主な機能一覧

- 環境変数管理（自動 .env ロード、必須設定チェック）
- DuckDB スキーマ定義および初期化（init_schema）
- J-Quants API クライアント（ページネーション、トークン管理、レート制御、保存関数）
- ETL パイプライン（run_daily_etl、差分フェッチ／バックフィル・品質チェック）
- ニュース収集（RSS の取得・前処理・raw_news 保存・銘柄抽出）
- 研究用ユーティリティ（将来リターン calc_forward_returns、IC calc_ic、summary）
- 特徴量エンジニアリング（build_features：ユニバースフィルタ、Zスコア正規化、features 保存）
- シグナル生成（generate_signals：コンポーネントスコア計算、Bear フィルタ、BUY/SELL 作成）
- 統計ユーティリティ（zscore_normalize 等）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
- 監査ログスキーマ（signal_events / order_requests / executions など）

---

## 要件

- Python >= 3.10
- 依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクト配布用の pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージ配布があれば）pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の最低サンプル（実際の値は適切に設定してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development   # development|paper_trading|live
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

必須環境変数（アクセス時にチェックされる）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

システム用オプション:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプトから使う一例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 引数で target_date / id_token 等を指定可
print(result.to_dict())
```

3) カレンダー更新ジョブ（夜間バッチ等で）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

4) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", ...}  # 収集時に紐付けしたい証券コード集合
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) 特徴量計算（features テーブル作成）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

6) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

7) 研究用関数（IC 計算等）は kabusys.research 以下を利用できます。

---

## 主要モジュール説明（短め）

- kabusys.config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）
  - settings オブジェクトから設定を参照（例: settings.jquants_refresh_token）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化

- kabusys.data.jquants_client
  - J-Quants API 呼び出し・ページネーション・トークン管理（get_id_token）
  - fetch_*/save_* でデータ取得と DuckDB 保存（冪等）

- kabusys.data.schema
  - DuckDB のスキーマ定義と init_schema()

- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック呼び出しを統合

- kabusys.data.news_collector
  - RSS の取得（SSRF／XML安全対策）、記事前処理、raw_news 保存、銘柄抽出

- kabusys.research
  - calc_momentum / calc_value / calc_volatility（factor_research）
  - calc_forward_returns / calc_ic / factor_summary（feature_exploration）
  - zscore_normalize（data.stats の再エクスポート）

- kabusys.strategy
  - build_features（特徴量処理＋features テーブルへ UPSERT）
  - generate_signals（final_score 計算、BUY/SELL 生成、signals テーブルへ UPSERT）

- kabusys.data.calendar_management
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job

- kabusys.data.audit
  - 監査用テーブル DDL（signal_events / order_requests / executions 等）

---

## ディレクトリ構成

（この README が対象としているコードベースの主要ファイル一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他: quality モジュール等が別に存在する想定)
    - monitoring/  (パッケージ __all__ に含まれているが、このリストにはコードがない場合あり)

（実際のリポジトリにはテスト、ドキュメント、pyproject.toml / requirements.txt 等が含まれる想定）

---

## 運用上の注意・設計メモ

- J-Quants API のレート制限（120 req/min）に合わせた内部レートリミッタを備えています。
- API リクエストは一部 HTTP ステータス（408/429/5xx）で指数バックオフ再試行します。401 はリフレッシュトークンを使って自動リフレッシュを試みます。
- ニュース収集は SSRF 対策（リダイレクト検査・プライベートIP検出）と XML 攻撃対策（defusedxml）を実装しています。
- features / signals / raw_* 保存はトランザクション＋バルク挿入で原子性・冪等性を重視しています。
- KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかでなければエラーになります。
- 開発・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑制できます。

---

## 貢献・拡張

- strategy 層の重みや閾値は generate_signals の引数で上書き可能（辞書で指定）。合計が 1.0 に正規化されます。
- execution 層（発注実装）や監視（monitoring）モジュールは設計に合わせて別リポジトリ／別モジュールとして実装できます。
- research の関数群は DuckDB 接続を受け取るため、データ分析スクリプトや Jupyter から直接利用可能です。

---

必要であれば、具体的な CLI スクリプト例、cron／systemd タイマーでの運用例、.env.example のテンプレートやユニットテストの書き方についても追加で記述できます。どの情報が必要か教えてください。