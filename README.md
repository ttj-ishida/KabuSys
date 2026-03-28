# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）、品質チェック、ニュース NLP、ファクター・リサーチ、監査ログ、マーケットカレンダー管理、戦略/約定監視までを提供します。

以下はこのリポジトリのREADME.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのモジュール群です。主に以下を目的としています。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への保存
- RSS ニュース収集と OpenAI を用いたニュースセンチメント評価（ai_score）
- マクロニュース + ETF MA200 乖離を合成した市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）算出とリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引フローの監査ログ（signal → order_request → execution）を格納する監査 DB 初期化ユーティリティ
- kabuステーション連携（発注／監視）や Slack 通知等のための設定管理基盤

設計における共通方針（抜粋）:
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を直接参照しない設計を心がけています。
- DuckDB を第1の永続化先として想定。
- OpenAI 呼び出しや外部 HTTP はリトライ・バックオフ等を備えた堅牢な実装。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）と環境変数化
  - 必須設定取得用 Settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）と ETLResult
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS フィード収集・前処理・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブルの初期化・監査 DB の作成（init_audit_db）
  - stats: zscore 正規化などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): マクロ + MA200 を合成して market_regime に書き込み
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns, calc_ic, factor_summary, rank
- その他：data.audit.init_audit_schema / init_audit_db、data.jquants_client の save_* / fetch_* 等

---

## セットアップ手順

※以下は一般的なセットアップ手順です。プロジェクト用の requirements.txt 等が無い場合は、最低限の依存関係をインストールしてください。

1. Python バージョン
   - Python 3.9+（typing の一部表記や型ヒントに依存）

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - requests（本実装では urllib を使っていますが、環境依存で必要に応じて）
   - （任意）pytest, mypy など

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時
pip install -e .
```

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト目的などで無効化可）。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（jquants_client が使用）
- SLACK_BOT_TOKEN: Slack 通知用（Slack 機能を使う場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を使う場合）

オプション（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト localhost のモック）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY: OpenAI 呼び出しのデフォルトキー（ai.score_* 関数で未指定時に参照）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=~/.kabusys/kabusys.duckdb
```

---

## 使い方（基本例）

以下は Python REPL やスクリプトから直接呼び出す際のサンプルです。

- DuckDB 接続を作って ETL を回す（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API が必要）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にある場合、api_key=None で OK
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# OpenAI のキーを明示的に渡すことも可能
result = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化（監査ログ用 DuckDB を作る）:

```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- ファクター計算 / リサーチ例:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意点:
- OpenAI 呼び出し（news_nlp / regime_detector）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必要です。
- ETL / 保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）が前提です。スキーマ初期化スクリプトはプロジェクトに含まれている想定ですが、必要に応じてスキーマ作成手順を実行してください（本 README では DDL の自動生成は省略）。

---

## 実行時の設定フローと安全策

- 環境変数は .env（プロジェクトルート）および .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV により挙動（本番 / ペーパー / 開発）を制御できます。例: 本番では is_live の判定で実注文を有効化するなど。
- OpenAI 呼び出しはリトライとフォールバック実装があります。API 失敗時は安全側のデフォルトスコア（0.0 等）にフォールバックする設計です。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの一覧（このリポジトリの一部）：

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              -- ニュース NLP（score_news）
    - regime_detector.py       -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（fetch/save）
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - etl.py                   -- ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py        -- RSS ニュース収集
    - calendar_management.py   -- マーケットカレンダー管理
    - quality.py               -- データ品質チェック
    - stats.py                 -- 統計ユーティリティ（zscore_normalize）
    - audit.py                 -- 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py       -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   -- 将来リターン / IC / サマリー / ランク
  - ai/, data/, research/ 以下にテスト可能な小単位の関数が揃っています

（上記はリポジトリ内のファイル群を抜粋した構成です）

---

## 開発者ノート / 補足

- DuckDB に対する executemany の挙動等（空リスト不可など）に配慮したコード設計がなされています。
- 外部 HTTP 呼び出し（RSS / J-Quants / OpenAI）はタイムアウト・サイズ制限・SSRF対策・リトライ等の安全対策を実装しています。
- LLM による出力は JSON モードを期待して厳密な JSON のみを返すようプロンプトで指示していますが、万が一のパース失敗にはフォールバックロジックがあります。
- 監査ログは削除しない前提で設計され、order_request_id を冪等キーとして二重発注防止を支援します。

---

## 参考と次のステップ

- 実環境で運用する場合は KABUSYS_ENV=live を設定し、十分なテストを行ってください（paper_trading での検証推奨）。
- DuckDB のスキーマ作成・マイグレーション、バックテスト用のデータ準備スクリプト、監視（Prometheus/ログ送出）の組み込みはプロジェクト固有に追加してください。
- セキュリティ面では環境変数の管理、OpenAI キーの取り扱い、kabu API の認証情報保護に注意してください。

---

必要であれば、この README に以下を追加作成できます:
- requirements.txt / pyproject.toml の推奨依存関係
- DuckDB のスキーマ初期化 SQL サンプル
- よくあるトラブルシュート（OpenAI エラー、J-Quants 401、RSS の SSRF ブロック等）
- 実行スクリプト（cron / systemd / GitHub Actions 用ワークフロー）テンプレート

ご希望あれば追記します。