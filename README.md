# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI ベースのニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- ETL パイプライン
  - 株価日足（raw_prices）・財務データ（raw_financials）・市場カレンダーの差分取得と DuckDB への冪等保存
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL の包括的実行（run_daily_etl）
- J-Quants API クライアント
  - レートリミット制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - daily_quotes / financial_statements / trading_calendar / listed_info の取得
- ニュース収集
  - RSS フィード取得、前処理（URL 正規化・トラッキングパラメータ除去）、SSRF 対策、raw_news への冪等保存（ID は正規化 URL の SHA-256）
- AI 支援機能
  - ニュースの銘柄別センチメントスコアリング（OpenAI を利用、gpt-4o-mini を想定）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成）
  - API 呼び出しはリトライ・フェイルセーフ設計（失敗時はゼロ補正など）
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを保証する監査スキーマ定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み（自動読み込み）、必須値チェックを提供

---

## 必要要件（主要ライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（その他標準ライブラリや urllib 等を使用）

pip で必要パッケージをインストールしてください（プロジェクトの requirements.txt があればそれを利用してください）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（設定項目）

主に `kabusys.config.Settings` で管理される環境変数（主なもの）:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で使用）
  - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で使用）
- 任意 / デフォルト付き
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH (data/execution.pid), KILL_FLAG_PATH (data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視の閾値）
  - KABUSYS_ENV: development / paper_trading / live (default: development)
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のある位置）にある `.env` と `.env.local` を自動で読み込みます。  
- 優先順位: OS 環境変数 > .env.local > .env。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカルで動かす最小手順）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. データディレクトリを作成（設定に合わせて）
```bash
mkdir -p data
```
5. `.env` をプロジェクトルートに作成し、必須環境変数（特に JQUANTS_REFRESH_TOKEN）を設定
6. DuckDB ファイルを作成するか、初期化処理（audit.init_audit_db など）を実行してスキーマを用意

---

## 使い方（簡易ガイド・コード例）

以下はライブラリの代表的な使い方例です。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または引数で渡す
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit）スキーマ初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで用意することも推奨
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- ニュース RSS の取得（news_collector のユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI 呼び出しには `OPENAI_API_KEY` を環境変数に設定するか、関数の `api_key` 引数で渡してください。
- J-Quants API 呼び出しには `JQUANTS_REFRESH_TOKEN` が必須です。

---

## 主要モジュールの説明（短い注釈）

- kabusys/config.py
  - .env 自動読み込み・環境変数管理・必須チェックを行う Settings クラス
- kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py / etl.py: ETL パイプライン、run_daily_etl の実装
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py: RSS 収集・前処理・SSRF 対策
  - calendar_management.py: 市場カレンダー管理（営業日判定、calendar_update_job）
  - audit.py: 監査ログ（監査テーブル定義と初期化）
  - stats.py: zscore_normalize などの統計ユーティリティ
  - pipeline の ETLResult: ETL 実行結果のデータクラス
- kabusys/ai/
  - news_nlp.py: タイムウィンドウ計算、ニュースを銘柄別に集約して OpenAI に投げて ai_scores に保存
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime を書き込む
- kabusys/research/
  - factor_research.py: モメンタム・ボラティリティ・バリューなどのファクター計算
  - feature_exploration.py: 将来リターン、IC、rank、factor_summary 等
- その他
  - __init__.py: パッケージの公開 API（data, strategy, execution, monitoring 等を想定）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成（src/kabusys）:

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
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター関連ユーティリティ等）

（README に使える単純なツリーとして）

---

## 運用上の注意 / 設計思想のハイライト

- Look-ahead bias を避ける設計
  - 関数群は内部で date.today() を参照しない設計（ターゲット日を明示的に引数で与える）
  - DB クエリは target_date 未満または対象日条件でルックアヘッドを防止
- フェイルセーフ
  - 外部 API（OpenAI、J-Quants 等）失敗時は可能な限りフェイルセーフ動作（部分スキップ・スコア 0 など）により処理継続
- 冪等性
  - DB への保存は基本的に ON CONFLICT（UPSERT）で実装
  - 発注監査の order_request_id 等は冪等キーとして設計
- セキュリティ
  - news_collector は SSRF 対策、トラッキングパラメータ除去、XML パースの安全化（defusedxml）を実施

---

## 貢献 / 拡張案

- strategy / execution / monitoring モジュール（発注ロジック、ポジション管理、監視エージェント等）の実装
- バックテスト用のインターフェース（過去データを用いた戦略検証）
- LINE / Slack 通知の強化やダッシュボード連携
- より詳細なユニットテストと CI パイプラインの追加

---

README に記載されていない詳細や、特定機能の使い方（例: ETL のトラブルシュート、OpenAI レスポンスのフォーマット注意点、DuckDB スキーマ定義等）が必要でしたら、どのトピックを深掘りするか教えてください。