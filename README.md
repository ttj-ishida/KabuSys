# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、リサーチ（ファクター計算）、監査ログ（注文・約定トレース）、カレンダー管理など、株式戦略開発と運用に必要な共通処理を提供します。

主な特徴
- J-Quants API を用いた株価・財務・上場情報・マーケットカレンダーの差分取得・保存（DuckDB）
- RSS ベースのニュース収集と前処理（SSRF・サイズ上限対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を使ったニュース / マクロセンチメント評価（JSON mode 対応、リトライ・フォールバックあり）
- 日次 ETL パイプライン（差分取得 / 保存 / 品質チェック）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- リサーチ用のファクター計算・特徴量解析ユーティリティ（DuckDB SQL + Python）
- 環境変数ベースの設定管理（.env 自動ロード機能）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（API リトライ、トークン自動リフレッシュ、レート制御）
  - market_calendar 管理（営業日判定 / next_trading_day / get_trading_days）
  - news_collector（RSS 取得 → raw_news 保存、SSRF・gzip・XML対策）
  - quality（データ品質チェック：欠損、重複、スパイク、日付不整合）
  - audit（監査ログテーブルの DDL / 初期化・専用 DB 初期化ユーティリティ）
  - stats（zscore_normalize 等の統計ユーティリティ）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)：ニュースをまとめて LLM に送り、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF（1321）の MA 乖離とマクロニュースを合成して市場レジームを判定・保存
- research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings オブジェクト（環境変数から設定値を取得、.env 自動ロード機能あり）

---

## 要求事項 / 前提

- Python 3.10+
- 主な Python 依存パッケージ（プロジェクトに requirements.txt があればそちらを参照してください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いですが、上記は主要機能で必要）
- J-Quants のリフレッシュトークン、OpenAI API キー等の環境変数設定が必要

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です（必須は明記）。

必須（起動・フル機能利用時）
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（settings.jquants_refresh_token で参照）
- KABU_API_PASSWORD     : kabuステーション API パスワード（settings.kabu_api_password）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（settings.slack_bot_token）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（settings.slack_channel_id）

OpenAI（AI 機能利用時）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime の api_key 引数を省略した場合参照）

オプション / デフォルト付き
- KABUSYS_ENV           : "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL             : ログレベル（"DEBUG","INFO",... デフォルト "INFO"）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" を設定すると .env 自動ロードを無効化

.env 自動ロード
- パッケージ import 時（kabusys.config）にプロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動ロードします。OS 環境変数が優先されます。.env.local は .env 上書き。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトの要件に合わせて）
   - pip install duckdb openai defusedxml
   - （プロジェクトに setup.cfg/pyproject.toml があれば pip install -e . など）
4. 環境変数を設定
   - プロジェクトルートに .env を配置するのが簡単（.env.example を参照）
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxxx
     - KABU_API_PASSWORD=secret
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な API とサンプル）

以下はライブラリの代表的な利用例です。各関数は DuckDB 接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- 日次 ETL を実行する（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）で銘柄ごとのスコアを作成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしている場合は api_key を省略可能
written = score_news(conn, target_date=date(2026,3,20))
print("書き込み銘柄数:", written)
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を受け取って order/event を記録する処理を実装
```

- ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

- 設定参照
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.kabu_api_base_url)
```

- カレンダー判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注記
- AI 関連の関数は OpenAI の API を呼び出します。API 呼び出しは失敗した場合にフェイルセーフ（スコア 0 やスキップ）となるよう設計されていますが、利用時は API キーとコスト管理に注意してください。
- DuckDB のバージョンや環境により executemany の振る舞いが若干異なるため、ETL 実装では空リストバインドを避ける処理が含まれています。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch / save）
    - pipeline.py                     — ETL 実行ロジック（run_daily_etl 等）
    - etl.py                          — ETL の公開型（ETLResult）
    - news_collector.py               — RSS 収集・正規化
    - calendar_management.py          — マーケットカレンダー管理
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - audit.py                        — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — Momentum/Value/Volatility 等
    - feature_exploration.py          — forward returns / IC / summary

---

## 開発・デバッグのヒント

- テスト時に .env 自動ロードを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を回避
- OpenAI 呼び出し部は内部で _call_openai_api 等の関数に抽象化されており、unittest.mock.patch で差し替えてテスト可能
- DuckDB はファイルベースで軽量なので開発時は :memory: を利用して単体テストを実行できます
- ETL は個々のステップ（calendar / prices / financials）を独立して実行できるため、障害切り分けが容易です

---

## ライセンス / 貢献

（リポジトリ側で別途 LICENSE を用意してください）

貢献やバグ報告は Pull Request / Issue を通じて受け付けてください。ドメイン固有（証券 API、実運用）のため、取り扱いには注意してください。

---

README は本プロジェクトの主要点をまとめたものです。詳細は各モジュールの docstring（src/kabusys 以下）を参照してください。