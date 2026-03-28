# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants）による市場データ取得、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ（DuckDB）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の要素を組み合わせて、取引戦略の研究・運用を支援するための基盤を提供します。

- データ収集（J-Quants API からの株価・財務・カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（ETF とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレース）を DuckDB に構築
- 設定管理（.env 自動ロード、環境変数）

設計上の主な方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不必要に使わない）
- 冪等性を重視（DB 書き込みは基本的に ON CONFLICT/DELETE→INSERT による置換）
- フェイルセーフ：外部APIが落ちた場合にも致命的にならない設計

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API からのデータ取得（prices, financials, market calendar 等）
  - DuckDB への保存（save_* 関数、冪等）
  - レートリミッター、トークン自動更新、リトライ処理

- data/pipeline.py
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による結果集約と品質チェック呼び出し

- data/news_collector.py
  - RSS 取得、前処理、raw_news へ冪等保存
  - SSRF 対策、gzip / サイズ制限、トラッキングパラメータ除去

- data/quality.py
  - 欠損・スパイク・重複・日付不整合などの品質チェック

- data/calendar_management.py
  - JPX カレンダー管理、営業日判定・次営業日/前営業日の算出、夜間バッチ更新ジョブ

- data/audit.py
  - 監査ログスキーマ定義と初期化（signal_events, order_requests, executions）
  - init_audit_db / init_audit_schema

- ai/news_nlp.py
  - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でスコアリング、ai_scores へ書き込み

- ai/regime_detector.py
  - ETF（1321）の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して market_regime を算出

- research/
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: forward returns, IC（Spearman）, factor_summary, rank
  - data/stats.py: zscore_normalize

- config.py
  - .env 自動読み込み（プロジェクトルート検出: .git/pyproject.toml を基準）
  - Settings クラス経由で環境変数をアクセス

---

## 必要な環境変数

以下は動作に必須（または推奨される）環境変数の一覧です。README に記載のものは最低限のものです。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL・データ取得）
- SLACK_BOT_TOKEN — Slack 通知を使う場合（必須扱いのコードパスあり）
- SLACK_CHANNEL_ID — Slack 通知送信先
- KABU_API_PASSWORD — kabuステーション API を使う場合

OpenAI 関連:
- OPENAI_API_KEY — ai/news_nlp.py / ai/regime_detector.py が OpenAI を使う場合に必要（関数引数で上書き可能）

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）

自動 .env ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env/.env.local を読み込まない

例（.env）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. Python（推奨: 3.10+）を用意します。

2. 依存パッケージをインストールします（プロジェクトの requirements.txt がない場合の例）:
   - duckdb
   - openai
   - defusedxml

   例:
   pip install duckdb openai defusedxml

   （プロジェクト配布時に pyproject.toml / requirements.txt があればそれを使用してください）

3. リポジトリをクローンしてパッケージをインストール（任意で editable）:
   git clone <repo>
   cd <repo>
   pip install -e .

4. 環境変数を設定:
   - プロジェクトルートに .env/.env.local を作成するか、OS 環境変数に設定してください。
   - config.Settings が自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

---

## 使い方（基本例）

以下はライブラリ関数を直接呼び出す簡単なサンプルです。各関数は DuckDB 接続（duckdb.connect() の戻り値）を受け取ります。

1) DuckDB 接続の作成（ファイル DB）:
from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/kabusys.duckdb")
conn = duckdb.connect(str(db_path))

（監査DB専用に初期化する場合）
audit_conn = init_audit_db("data/monitoring_audit.duckdb")

2) 日次 ETL を実行:
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡す）:
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} stocks")

4) 市場レジーム判定:
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))

5) 研究用ファクター計算:
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))

6) 監査スキーマの初期化（既存接続にテーブルを作る）:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

注意点:
- OpenAI 呼び出しは外部APIでコスト・レート制限があるため実行時に注意してください。
- ETL やニュース取得は外部 API やネットワークに依存するため、ログとリトライ挙動を確認してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 管理、Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py — マクロ + MA から市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得と raw_news 保存
    - calendar_management.py — market_calendar 管理 / 営業日判定
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py — 将来リターン / IC / 要約
  - (その他) strategy/, execution/, monitoring/ は __all__ に含まれるがここで提供するコアは上記

---

## 運用上の注意

- API キーや機密情報は .env に置くかシークレットマネージャーを使ってください。リポジトリにコミットしないでください。
- DuckDB ファイルや SQLite ファイルのパスは Settings で指定できます（DUCKDB_PATH / SQLITE_PATH）。
- OpenAI のコールはコストとレート制限があるため、バッチサイズや頻度を運用で管理してください（news_nlp は銘柄をチャンク処理します）。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑止できます。
- ETL と品質チェックは独立して例外処理されるため、ログを確認して部分的な失敗に対処してください。

---

## 開発・テスト

- 単体テストでは外部API呼び出しをモックしてください（OpenAI / J-Quants / RSS など）。
- news_nlp と regime_detector 内の _call_openai_api はテスト用にモックして差し替え可能です（unittest.mock.patch を想定）。

---

この README はコードベースの注釈・仕様に基づいて作成しています。さらに詳細な API や実行例（SQL スキーマ、テーブル定義、運用ジョブの cron 設定等）が必要であれば教えてください。