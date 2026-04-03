# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ、マーケットカレンダー管理、品質チェックなどを含むモジュール群を提供します。

主な設計方針として、バックテスト等でのルックアヘッドバイアスを避けるために「現在時刻参照を直接行わない」実装が多く採用されています（関数は target_date を受け取る等）。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡易サンプル）
- 主な API / エントリポイント
- ディレクトリ構成（ファイル一覧と簡単説明）

---

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株のデータ取得・品質管理・特徴量抽出・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などを統合するライブラリ群。
- 言語: Python
- DB: DuckDB を主に想定（監視/履歴用に sqlite なども使用可）
- 外部 API: J-Quants（市場データ）、OpenAI（ニュースのセンチメント解析）、kabuステーション API（注文実行用・パスワード項目あり）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 各種）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得、安全対策、raw_news 保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp: ニュースを銘柄ごとに集約して OpenAI に送りセンチメント（ai_scores）を生成
  - regime_detector: ETF（1321）の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定
- research
  - ファクター計算（momentum, value, volatility など）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク変換
- config
  - .env / 環境変数の自動読み込みと Settings オブジェクト（settings）による設定参照
- audit
  - シグナル〜約定までをトレースする監査テーブル DDL と初期化ユーティリティ

設計上、ETL・リサーチ系は DuckDB 接続を受け取りローカルで安全に実行できるように分離されています（実行 API へ直接アクセスするコードは含まれません）。

---

## 前提・依存関係

- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ（urllib, json, logging 等）を使用

（requirements.txt がない場合は必要なパッケージを手動でインストールしてください。将来的に requirements.txt / pyproject.toml を参照することを推奨します）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （パッケージはプロジェクトの pyproject.toml / requirements.txt があればそちらを使用してください）

4. パッケージとして編集インストール（開発用）
   - pip install -e .

5. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env/.env.local を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 環境変数（.env）例

最低限設定が必要なもの:
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
- OPENAI_API_KEY=あなたの_OpenAI_API_キー（ai.score 系で使用）
- KABU_API_PASSWORD=kabuステーション API パスワード（発注機能を使う場合）

その他オプション:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB 等: data/monitoring.db）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_pass
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は config.Settings から参照できます:
```
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## 使い方（簡易サンプル）

以下は最小限の呼び出し例です。すべての関数は DuckDB 接続を受け取るため、DuckDB ファイルを指定して接続を作成してから使用します。

- 日次 ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

注意:
- OpenAI API を使用する関数は OPENAI_API_KEY を環境変数か引数で渡す必要があります（score_news/score_regime は api_key 引数も受け取ります）。
- ETL/保存関数は冪等性を考慮して実装されています（ON CONFLICT DO UPDATE 等）。

---

## 主な API / エントリポイント（抜粋）

- kabusys.config.settings: 環境変数設定オブジェクト
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.pipeline.run_financials_etl(...)
- kabusys.data.pipeline.run_calendar_etl(...)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / save_*
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.data.quality.run_all_checks(...)
- kabusys.research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.audit.init_audit_schema / init_audit_db

---

## ディレクトリ構成

以下は主要なファイル・モジュールと短い説明です（src/kabusys 以下）:

- __init__.py
  - パッケージのトップ（バージョンと公開サブパッケージ列挙）

- config.py
  - .env の自動読み込み、環境設定（Settings クラス）

- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄ごとに集約して OpenAI でセンチメント解析 → ai_scores へ保存
  - regime_detector.py: ETF(1321) の MA 乖離とマクロニュース LLM を合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py: 日次 ETL パイプラインと個別 ETL（prices/financials/calendar）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集、前処理、SSRF 対策、raw_news 保存
  - calendar_management.py: market_calendar 管理・営業日判定・calendar_update_job
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ定義、初期化ユーティリティ（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py: momentum/value/volatility 等のファクター計算
  - feature_exploration.py: forward returns / IC / factor summary 等

- research パッケージや ai パッケージの関数は DuckDB 接続を引数として受け取り、外部 API へは基本的にアクセスしない設計です（一部 AI は OpenAI を利用します）。

---

## 運用上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはレートやレスポンスの不定性があるため、各モジュールでリトライ・フェイルセーフ（失敗時スコア=0 等）が実装されています。運用時は API コストや制限に注意してください。
- J-Quants API はレート制限、401 リフレッシュ対応、ページネーションなどを考慮して実装されています。refresh token（JQUANTS_REFRESH_TOKEN）は必須です。
- DuckDB の executemany の仕様（バージョン依存）を考慮した実装があるため、DuckDB のバージョンに注意してください（コード内にも互換回避のコメントあり）。

---

ご不明点や README に追記したい具体的な利用シナリオ（例: バックテスト連携方法、運用デプロイ手順、CI 用チェック等）があれば、その用途に合わせて使い方・コマンド例を追加します。