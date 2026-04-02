# KabuSys

日本株向けの自動売買／データプラットフォーム用のライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよび研究プラットフォーム向けの共通ライブラリ群です。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と記事前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄毎）およびマクロセンチメントの合成による市場レジーム判定
- ファクター計算・特徴量探索・IC 計算などのリサーチ機能
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定に至る監査ログテーブル（監査用スキーマ）の初期化ユーティリティ
- 設定は環境変数（またはプロジェクトルートの .env / .env.local）で管理

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可能）
  - 各種必須環境変数（J-Quants, Kabu API, Slack 等）の取得ラッパー
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl による市場カレンダー・株価・財務の差分取得・保存と品質チェック
  - jquants_client 経由で API ページネーション・レートリミット・リトライを処理
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）、将来日付/非営業日データ検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等挿入
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄別に記事を集約して OpenAI に投げ、銘柄ごとの ai_score を ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して market_regime を作成
- 研究用（kabusys.research）
  - モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC、統計サマリ
- 監査ログ初期化（kabusys.data.audit）
  - signal_events, order_requests, executions 等の DDL とインデックスを冪等に作成
- レポート・ユーティリティ（kabusys.data.stats など）
  - Z スコア正規化等の軽量統計ユーティリティ

---

## 必要条件（推奨）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, datetime, json 等を使用

（実際の requirements.txt / setup はプロジェクトに合わせてください）

pip 例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env を推奨）

必須の主要環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD    : kabu ステーション API パスワード（発注等がある場合）
- SLACK_BOT_TOKEN      : Slack 通知用トークン（オプションだが config が必須にしている場合あり）
- SLACK_CHANNEL_ID     : Slack チャネル ID

オプション・デフォルト:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
- SQLITE_PATH — data/monitoring.db（デフォルト）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env と .env.local を自動で読み込みます
- 自動読み込みをオフにする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主な利用パターン）

以下は Python REPL / スクリプト例です。DuckDB 接続は duckdb.connect を使って行います。

- ETL を実行（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄ごと）をスコアリングして DB に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {num_written}")
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化（別ファイルで監査専用に切る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等が作成されます
```

- J-Quants API を直接呼ぶ（テストやカスタム取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境に必要
rows = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意点:
- OpenAI 関連（news_nlp, regime_detector）は OPENAI_API_KEY を環境変数に設定するか api_key 引数を渡す必要があります。
- ほとんどの処理は「ルックアヘッドバイアス防止」を考慮して実装されています（内部で date.today() 等を使わない等）。バックテスト用途のときはデータの取扱いに注意してください。

---

## 設定と運用メモ

- .env / .env.local の読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- デバッグ: settings.log_level や環境変数 LOG_LEVEL を使ってログレベルを調整
- データベースパスは settings.duckdb_path / settings.sqlite_path で取得可能
- ETL の run_daily_etl は品質チェックオプションやバックフィル日数を調整可能

---

## ディレクトリ構成

（重要なファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（銘柄別）
    - regime_detector.py            -- 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得 / 保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETL 型や再エクスポート
    - news_collector.py             -- RSS 取得・前処理・raw_news 保存
    - calendar_management.py        -- 市場カレンダー管理（営業日判定等）
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      -- 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Value/Volatility 計算
    - feature_exploration.py        -- 将来リターン、IC、統計サマリ、ランク化
  - ai/, data/, research/ の他に strategy/, execution/, monitoring などのサブパッケージを想定（__all__ に列挙）

---

## 開発時のヒント

- テスト時に .env 自動読み込みを避けたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI の呼び出しはモック可能:
  - モジュール内部で _call_openai_api を patch することで API 呼び出しを差し替え可能
- DuckDB executemany は空リストを受け付けないバージョンに注意（コード内でチェック済み）

---

## ライセンス・貢献

この README にはライセンスの記載がありません。実際のプロジェクトでは LICENSE ファイルを追加してください。貢献ガイド（CONTRIBUTING.md）や issue/PR フローはプロジェクト独自に定めてください。

---

以上がこのコードベース (KabuSys) の README.md です。必要であれば、README に以下を追加できます：
- 具体的な requirements.txt（バージョン固定）
- CI / テストの実行方法
- デプロイ（監視・Supervisor / systemd のサンプル）
- よくあるトラブルシューティング（J-Quants トークン更新、OpenAI レート制限対応 など）

追加希望があれば指示してください。