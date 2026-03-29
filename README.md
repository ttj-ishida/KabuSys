# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、品質チェック、監査ログなど、投資戦略開発と本番運用に必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴
- Look‑ahead bias（先見バイアス）対策を重視（date 引数を明示的に渡す設計）
- DuckDB をデータベース基盤として使用（ローカルファイル/インメモリ対応）
- J-Quants API から株価・財務・カレンダーを差分取得する ETL パイプライン
- ニュース記事を収集・前処理し、OpenAI（gpt-4o-mini）で銘柄センチメントを算出
- ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）を保存するスキーマ初期化ユーティリティ
- 研究用ファクター計算・統計ユーティリティ（モメンタム、ボラティリティ、バリュー等）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL 検証

- データ取得・ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API 呼び出し（ページネーション・リトライ・レート制御）
  - save_* 関数による DuckDB への冪等保存
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理

- ニュース収集・NLP（kabusys.data.news_collector / kabusys.ai.news_nlp）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI を使った銘柄単位センチメント（バッチ処理・JSON mode）
  - calc_news_window による対象ウィンドウ計算

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA とマクロニュース LLM スコアの合成で daily レジーム判定

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル作成・インデックス
  - init_audit_db / init_audit_schema による初期化ユーティリティ

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
  - QualityIssue の集約・報告

- 研究支援（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats 経由）

---

## セットアップ手順（開発／利用者向け）

前提
- Python 3.9+（プロジェクトの pyproject.toml に依存するため合わせてください）
- DuckDB を同システムにインストール（Python パッケージとして `duckdb` を使用）

推奨インストール手順（例）
1. リポジトリをクローン / ワークディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそれに従ってください）
4. 開発モードでインストール（パッケージ化されている場合）
   - pip install -e .

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネルID
- OPENAI_API_KEY (必須（AI機能を使う場合）): OpenAI API キー
- DUCKDB_PATH (任意): デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意): デフォルト "data/monitoring.db"
- KABUSYS_ENV (任意): "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env 自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要なワークフローとコード例）

以下は簡単な利用例です。関数は外部 API を呼ぶので、稼働環境では環境変数（認証情報）を正しく設定してから実行してください。

共通準備
```python
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイル: settings.duckdb_path か ":memory:"）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定。省略時は今日。
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores）を作成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

3) 市場レジームを判定して保存する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

# 監査 DB を別ファイルで用意する場合
audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

# target_date に対してそれぞれ実行
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

注意点
- OpenAI 呼び出しや J-Quants API は外部通信を行うため、ユニットテストでは該当関数（内部の _call_openai_api や _request など）をモックすることを推奨します（コード中でもその想定で設計されています）。
- DuckDB executemany に関する注意（空リスト渡し不可なバージョンなど）には既に対処済みです。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py              -- パッケージ初期化（__version__ 等）
  - config.py                -- 環境変数/設定管理（.env 自動ロード・検証）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py            -- ETL パイプライン / run_daily_etl
    - etl.py                 -- ETLResult の再エクスポート
    - news_collector.py      -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理 / 営業日判定
    - stats.py               -- zscore_normalize（汎用統計）
    - quality.py             -- データ品質チェック
    - audit.py               -- 監査ログテーブル初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank

---

## トラブルシューティング（よくある問題）

- 必須環境変数未設定
  - 実行中に ValueError が発生する場合、README の「環境変数」セクションにある必須変数が不足しています。例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN 等。

- .env が読み込まれない
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探します。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境を注入してください。

- OpenAI 呼び出しでのエラー
  - rate limit / network / 5xx はリトライ実装がありますが、API キーの権限や割当量により失敗する可能性があります。API レスポンスのパースに失敗した場合はログが出力され、スコアはフェイルセーフで 0 にフォールバックされる箇所があります。

- J-Quants API 呼び出しで 401 が返る
  - jquants_client はリフレッシュトークンから id_token を取得してキャッシュします。401 の場合はトークンを自動更新してリトライしますが、設定の refresh token が誤っていると失敗します。

---

## 開発者向けメモ

- モジュール内の外部 API 呼び出し（OpenAI / J-Quants / HTTP）は、それぞれの内部ヘルパー（_call_openai_api / _request / _urlopen）をモックしてテスト可能な構造になっています。
- DuckDB の日時はコード中で date/datetime を正しく扱うよう注意しています（UTC 基準・naive datetime に変換等）。
- スキーマや DDL は kabusys.data.audit に集約されています。監査スキーマは冪等に作成可能です。

---

必要であれば、README に以下を追加できます：
- サンプル .env.example（各キーの説明付き）
- CI 用のセットアップ例（GitHub Actions など）
- Docker イメージ / Compose 例（J-Quants / kabuステーションのモックと組み合わせたローカル開発環境）