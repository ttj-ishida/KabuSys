# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants / RSS / OpenAI 等と連携してデータ取得、品質チェック、AI を用いたニュースセンチメント、戦略用ファクター計算、監査ログ管理までをカバーします。

この README ではプロジェクト概要、機能一覧、セットアップ手順、主要な使い方例、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

- ターゲット: 日本株の自動売買・リサーチ基盤
- 主な役割:
  - J-Quants からの株価・財務・カレンダーの差分 ETL（DuckDB 保存）
  - RSS ニュース収集 -> raw_news 保存および記事の銘柄紐付け
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント / 市場レジーム判定
  - ファクター計算（Momentum, Value, Volatility 等）と特徴量探索ユーティリティ
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ（signal / order_request / executions）のスキーマ初期化・管理
  - kabu/証券会社/LINE 等への通知や実行層（コードベースの一部）

- 設計方針:
  - ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない）
  - DuckDB を主要ストレージとして利用（軽量で SQL に対応）
  - API 呼び出しはリトライ・レートリミット制御を備える（J-Quants / OpenAI 等）
  - 冪等性を重視した保存ロジック（ON CONFLICT / DELETE→INSERT 等）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env/.env.local の自動ロード（プロジェクトルート探索）
  - 環境変数経由の設定管理（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・ページネーション・レート制御）
  - pipeline: 日次 ETL 実行 run_daily_etl（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策・トラッキング除去）
  - calendar_management: JPX カレンダー管理（営業日判定 / next/prev / 更新ジョブ）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ
  - stats: zscore_normalize（クロスセクション正規化）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント生成（OpenAI + JSON Mode）
  - regime_detector.score_regime: ETF(1321) MA200 乖離 + マクロニュースを合成して市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（統計解析）

---

## 前提・必要な環境変数

主に以下の環境変数が使用されます（プロジェクトは .env / .env.local を自動ロードします）。

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（`jquants_client.get_id_token` 用）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector で使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注機能利用時）

オプション:
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH など監視関連

自動 env ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル .env（プロジェクトルートに置く）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は例として主要ライブラリをインストール:
     - pip install duckdb openai defusedxml
   - （プロジェクトパッケージがあれば）開発インストール:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を作成（上記サンプル参照）
   - または CI / 実行環境で環境変数を設定

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な呼び出し例）

以下は Python スクリプト/REPL からの使用例です。DuckDB 接続は各関数が期待する DuckDBPyConnection を渡してください。

共通準備:
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL（市場カレンダー・株価・財務・品質チェックを実行）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を渡せます
print(result.to_dict())
```

2) ニュースセンチメントの計算（OpenAI を使う）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコア生成日（例: date(2026,3,20)）
n_written = score_news(conn, target_date=date.today())
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date.today())
```

4) ファクター計算（リサーチ用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date.today())
val = calc_value(conn, date.today())
vol = calc_volatility(conn, date.today())
```

5) 監査ログスキーマの初期化（監査DBを作成）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# または ":memory:" を渡してメモリDB
```

6) JPX カレンダー更新ジョブを単体で実行
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("保存レコード数:", saved)
```

注意:
- OpenAI を使う機能は環境変数 OPENAI_API_KEY を必ず設定してください（api_key を直接渡すことも可能）。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN を必要とします。

---

## 注意点 / 運用メモ

- ルックアヘッドバイアス回避のため、各スコアリング関数は target_date 引数を明示的に渡す想定です。内部で date.today() を参照しない実装方針が取られています（ただし ETL のデフォルトは省略時に今日を使います）。
- DuckDB の executemany による空リストバインドに注意（コード側でチェックされています）。
- J-Quants の API レート制限や OpenAI のレート制限に配慮して実装されています。環境によってはさらにスロットリングを追加してください。
- news_collector は SSRF 防止、XML デフューズ等の対策を実装していますが、外部ソースに対する取り扱いには注意してください。

---

## ディレクトリ構成（要約）

リポジトリの主要ファイル・モジュール（src/kabusys 以下）:

- __init__.py
- config.py — 環境変数・設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント / 保存ロジック
  - pipeline.py — ETL パイプライン / run_daily_etl 等
  - news_collector.py — RSS 収集と前処理
  - calendar_management.py — 市場カレンダー判定・更新
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ初期化
  - etl.py — ETLResult の再エクスポート
  - stats.py — zscore_normalize 等
- research/
  - __init__.py — 公開 API 集約
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン/IC/統計サマリー

（上記に加え、strategy/ execution/ monitoring/ などのパッケージも __all__ に用意されていますが、README 用に主にデータ・AI・リサーチ関連を抜粋しています。）

---

## サポート / 開発者向けメモ

- 環境設定・テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを抑制できます。
- OpenAI 呼び出し部分はテスト用にモックしやすいように内部コールを独立させた実装になっています（ユニットテストでの差し替えを想定）。
- DuckDB スキーマ初期化関数（audit.init_audit_schema など）は transactional オプションに注意してください（DuckDB はネストトランザクション非対応）。

---

必要に応じてこの README を拡張します。特に導入手順（requirements.txt, pyproject.toml に基づくインストール方法）、運用スクリプト（systemd / cron / container 実行例）、CI 設定などを追加できますので希望があれば教えてください。