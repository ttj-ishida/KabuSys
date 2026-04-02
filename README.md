# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・ニュースNLP（LLM を用いたセンチメント）・市場レジーム判定・リサーチ用ファクター計算・監査ログスキーマなどを含むモジュール群を提供します。

## 主要な特徴
- J-Quants API 経由で株価・財務・上場情報・マーケットカレンダーを差分取得／保存（DuckDB）
- ニュース RSS 収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
- OpenAI を用いたニュースセンチメント（gpt-4o-mini, JSON mode）による銘柄別 ai_score 生成
- ETF（1321）の200日移動平均乖離とマクロニュースセンチメントを合成した「市場レジーム判定」
- ETL パイプライン（差分取得・保存・品質チェック）と品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal_events / order_requests / executions）スキーマ生成ユーティリティ（冪等）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、将来リターン、IC、統計サマリ等）
- 環境変数/.env 自動ロード機構（プロジェクトルート検出）および安全な設定管理

---

## 動作要件
- Python 3.10 以上（型ヒントの union 演算子（|） を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（プロジェクトの実際の requirements.txt/pyproject.toml に合わせてインストールしてください）

---

## インストール（開発環境例）
仮想環境を使うことを推奨します。

bash
- python -m venv .venv
- source .venv/bin/activate
- pip install --upgrade pip
- pip install duckdb openai defusedxml
- pip install -e .

（プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください）

---

## 環境変数（.env）
kabusys はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用される環境変数（必須となるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用の Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime の呼び出し時に必要）
その他（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 初期設定（DB 初期化）
監査ログなど専用スキーマを作成するユーティリティが用意されています。監査用 DuckDB を初期化する一例：

python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection

既存の DuckDB 接続に監査スキーマを追加する：
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

---

## 使い方（主要 API のサンプル）

前提：DuckDB 接続を用意し `settings` からパスを参照することもできます。

- 日次 ETL 実行（株価・財務・カレンダー + 品質チェック）
python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（ai_scores 生成）
python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", num_written)

- 市場レジーム判定（market_regime 生成）
python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数で指定

- 研究（ファクター計算）
python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))

- 統計ユーティリティ（Zスコア正規化）
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

---

## 監視・実行プロセス関連
- 設定に pid ファイルパスや閾値（CPU/メモリ/ディスク）があり、監視モジュールから使用されます（詳細は kabusys.monitoring モジュール等に実装予定／存在する場合参照）。

---

## 実装上の注意点 / 設計方針（抜粋）
- ルックアヘッドバイアス対策: 関数内部で datetime.today() / date.today() を直接参照しない設計になっている箇所が多く、target_date を明示して処理します。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE（または INSERT ... DO NOTHING）を用いて冪等性を確保。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）の障害発生時は、可能な限り処理を継続し、ログ出力して安全側（ゼロスコア／スキップ等）にフォールバックする実装が多く含まれます。
- セキュリティ: RSS 収集では SSRF 対策・受信サイズ上限・XML パーサに defusedxml を使用しています。

---

## ディレクトリ構成（抜粋）
以下はこのリポジトリの主要ファイル構成（src/kabusys 以下の抜粋）です。

src/kabusys/
- __init__.py
- config.py                     -- 環境変数 / .env ロードと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py                 -- ニュースセンチメント（score_news）
  - regime_detector.py          -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py                 -- ETL パイプライン / run_daily_etl 等
  - etl.py                      -- ETLResult 再エクスポート
  - jquants_client.py           -- J-Quants API クライアント & DuckDB 保存
  - news_collector.py           -- RSS 取得・前処理・保存
  - calendar_management.py      -- 市場カレンダー管理
  - quality.py                  -- データ品質チェック
  - stats.py                    -- 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                    -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          -- モメンタム / ボラ / バリュー 等
  - feature_exploration.py      -- 将来リターン / IC / 統計サマリ
- ai/, data/, research/ はそれぞれ公開関数を __all__ で整理しています

---

## ロギングとデバッグ
- 設定ファイルの LOG_LEVEL（環境変数）でログレベルを調整できます。
- ETL や API 呼び出しは内部で詳細ログを出力するため、問題調査はログを参照してください。

---

## 開発・貢献
- 関数単位で外部 API 呼び出しを差し替えやすく設計してあるため、ユニットテストのモックが容易です（たとえば news_nlp._call_openai_api を patch）。
- PR や issue により改善・拡張を歓迎します。大きな変更は設計方針（ルックアヘッド防止、冪等性、フェイルセーフ等）を尊重してください。

---

もし README のサンプル .env.example、requirements.txt、簡易 CLI スクリプト（例: scripts/run_etl.py）などを追加してほしい場合は、その内容を指定していただければ作成します。