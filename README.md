# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、運用と研究の両面をカバーします。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ基盤と戦略実行のためのモジュール群を提供します。主な役割は以下の通りです。

- J-Quants API 経由で株価・財務・カレンダー等を取得して DuckDB に格納する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS を用いたニュース収集と記事の前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別）とマクロセンチメントによる市場レジーム判定
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 取引の監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- 環境変数 / .env 管理ユーティリティ

設計上の重要点:
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- DuckDB を中心に SQL と Python を組み合わせた処理
- API 呼び出しはリトライ・バックオフやレート制御を備えた堅牢な実装
- 冪等操作（ON CONFLICT DO UPDATE 等）を重視

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API とのやり取り（取得 + DuckDB への保存）
  - pipeline: 日次 ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック群（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策、トラッキングパラメータ除去）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとにニュースを集約し LLM でセンチメント評価 → ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数から設定を読み込む。自動的にプロジェクトルートの .env / .env.local を読み込む（無効化可）

---

## セットアップ手順

※ 以下は一般的なセットアップ手順の例です。プロジェクトの依存パッケージ一覧（requirements.txt / pyproject.toml）があればそちらに従ってください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python バージョン
   - 本コードは型ヒントや union 型（Path | None 等）などを使っているため Python 3.10+ を推奨します。

3. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

4. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai (または openai の新 SDK が使われている場合それに合わせる)
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API 用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知周り（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live')（デフォルト development）
     - LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定

6. データベース初期化（監査ログ等）
   - 監査用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（代表的な例）

以下はライブラリをプログラムから使う際の最小例です。

- DuckDB 接続の作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアの実行（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている前提）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定の実行:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

備考:
- OpenAI クライアントは内部で OpenAI(api_key=...) を作成しています。テスト時は各モジュールの `_call_openai_api` をモックするなどして外部呼び出しを制御できます。
- J-Quants API 呼び出しは jquants_client がレート制御 / リトライ / トークンリフレッシュを扱います。get_id_token() や fetch_* 関数を直接利用可能です。

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token() で利用されます。

- KABU_API_PASSWORD (必須)  
  kabu ステーション API 用のパスワード。

- OPENAI_API_KEY  
  OpenAI API を使う機能（news_nlp / regime_detector）で利用。関数呼び出し時に api_key を明示的に渡すことも可能。

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)  
  DuckDB のファイルパス。

- SQLITE_PATH (デフォルト: data/monitoring.db)  
  監視用 SQLite のパス。

- KABUSYS_ENV (development|paper_trading|live)  
  環境フラグ（Settings.is_live / is_paper / is_dev を参照可能）。

- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑止できます。

自動読み込みの優先順位: OS 環境変数 > .env.local > .env

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py         — マクロ + ETF MA200 乖離による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API client & DuckDB 保存ロジック
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - quality.py                 — データ品質チェック（QualityIssue 等）
    - calendar_management.py     — マーケットカレンダー管理と営業日判定
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - news_collector.py          — RSS 取得と raw_news 保存
    - audit.py                   — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py     — 将来リターン / IC / summary 等
  - research/...                 — 研究用ユーティリティ群

---

## 注意事項 / 運用上のメモ

- ルックアヘッドバイアス対策として、target_date を明示して日付窓を計算する設計です。内部で無闇に現在時刻を参照しない点に留意してください（テスト・バックテストでの再現性を確保）。
- OpenAI 呼び出しは外部 API へのアクセスを伴います。API キー・コスト・レート制限に注意してください。テストでは API 呼び出し関数のモックが想定されています。
- jquants_client は API レート（デフォルト 120 req/min）を守る実装になっていますが、実運用では追加のレート管理やバッチ設計を検討してください。
- DuckDB の executemany はバージョン依存の制約（空リスト不可等）があるため、該当処理では安全側のガードが入っています。
- news_collector には SSRF 対策・受信サイズ制限・XML パーサの安全化（defusedxml）等の防御処理があります。外部 URL の扱いに注意してください。

---

この README は本リポジトリ内のコード（src/kabusys 以下）に基づいて作成しています。実際の運用・デプロイ時は実環境に合わせた設定（環境変数、DB パス、API トークン管理）を行ってください。必要であれば具体的なコマンドや CI / systemd / コンテナ化の手順も追記できます。