# KabuSys

KabuSys は日本株向けのデータ基盤・研究・自動売買支援ライブラリです。  
J-Quants からのデータ取得、DuckDB による ETL／保存、ニュースの NLP スコアリング、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な設計方針：
- バックテストにおけるルックアヘッドバイアス回避（多くの処理は内部で date を引数として受け、date.today() を直接参照しない）
- DuckDB を中心としたローカルデータ管理（冪等保存やトランザクション管理を重視）
- OpenAI（gpt-4o-mini）を利用したニュース NLP（JSON Mode）や市場レジーム判定
- J-Quants / kabuステーション 等の外部 API と堅牢に連携（レート制御・リトライ・トークンリフレッシュ等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - 差分取得・バックフィル、DuckDB への冪等保存（ON CONFLICT）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集・前処理
  - RSS 取得（SSRF対策・サイズ上限・トラッキングパラメータ除去）
  - raw_news テーブルへの冪等保存、銘柄紐付け処理
- ニュース NLP / レジーム判定（OpenAI）
  - 銘柄ごとのニュースセンチメントスコアを ai_scores に保存（score_news）
  - マクロセンチメントと ETF (1321) の 200 日 MA 乖離を合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ／フェイルセーフで設計（失敗時は 0.0 などのフォールバック）
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを定義・初期化（init_audit_schema / init_audit_db）
  - 発注の冪等キー（order_request_id）や作成日時を含む設計
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - J-Quants からの calendar 更新ジョブ（calendar_update_job）

---

## 必要条件（依存）

主な Python ライブラリ（抜粋）:
- duckdb
- openai
- defusedxml

※実際のインストール時は pyproject.toml / requirements.txt があればそれに従ってください。以下は一例です。

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他、プロジェクトが要求するパッケージをインストール
```

---

## セットアップ手順

1. リポジトリをクローン／配置（パッケージは src/kabusys にあります）
2. 仮想環境作成・依存インストール（上記参照）
3. 環境変数を準備
   - .env ファイル（プロジェクトルート）を作成することで自動読み込みされます
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
4. DuckDB ファイル等の準備（デフォルトは data/kabusys.duckdb、data ディレクトリを作成）

---

## 環境変数

必須（使用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（データ ETL に必須）
- SLACK_BOT_TOKEN — Slack 通知を行う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabuステーション API パスワード（実売買に必要）

任意 / デフォルトあり:
- KABUSYS_ENV — environment: "development"（デフォルト）, "paper_trading", "live"
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に使用）

注意:
- settings モジュール（kabusys.config.settings）からこれらを取得できます。
- settings は .env/.env.local を自動で読み込みます（プロジェクトルートは .git または pyproject.toml によって検出）。

---

## 使い方（主要な例）

以下はライブラリの代表的な使い方のサンプルです。実運用ではログ設定や例外処理、ID トークンの注入などを適宜行ってください。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントをスコアして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

4) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DB 初期化（監査DBを別ファイルで運用する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが作成済みの接続
```

6) ファクター計算・研究ユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
zscore_normalized = zscore_normalize(mom, ["mom_1m", "mom_3m"])
```

7) マーケットカレンダー関数
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

---

## 実装上の注意点（重要）

- 多くの機能は date / conn を明示的に渡す設計です。内部で現在時刻を参照する実装は避け、バックテストでのルックアヘッドを防止しています。
- OpenAI 呼び出しは外部 SDK の例外（RateLimit, Timeout, APIError 等）を考慮し、リトライまたはフェイルセーフ（スコア=0.0）で継続する設計です。
- J-Quants API 呼び出しはレート制限 (120 req/min) を守るための RateLimiter を実装しています。401 受信時はリフレッシュトークンを使って自動リフレッシュします。
- News Collector は SSRF 対策、受信サイズ上限、XML の安全パースなどを備えています。
- DuckDB に対する executemany の一部バージョン制約（空リスト不可）に注意して実装が行われています。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの NLP スコアリング（score_news）
  - regime_detector.py — マクロセンチメント＋MA200 で市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理・判定
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — Z スコア等統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ（テーブル定義・初期化）
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存関数）
  - news_collector.py — RSS 取得・前処理・保存
- src/kabusys/research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- src/kabusys/ai/__init__.py

※上記は実装済み機能の抜粋説明です。細かい実装・追加モジュールはソースを参照してください。

---

## 開発・テストについて

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込みます。テストで自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出し部分はモックしやすいように内部呼び出しを分離しています（ユニットテスト時は該当関数を patch してください）。
- DuckDB を使うためローカルでの高速な単体テストが可能です（":memory:" を使った接続も対応）。

---

## ライセンス・貢献

本リポジトリのライセンス情報やコントリビュートの流れはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に書かれている使用例は簡易的なものであり、本番運用ではログ設定、例外ハンドリング、シークレット管理（Vault 等）の導入、監視・アラート設定を必須としてください。