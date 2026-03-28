# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ向け README（日本語）

概要、機能、セットアップ、基本的な使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームおよび自動売買基盤を想定した Python モジュール群です。  
主な目的は以下の通りです。

- J‑Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集・NLP（LLM）による銘柄センチメント評価
- 市場レジーム判定（MA と マクロニュースの合成）
- ファクター計算・特徴量探索（リサーチ用途）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用の DuckDB スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、ルックアヘッドバイアスの排除、冪等性の確保（ON CONFLICT / idempotent 保存）、外部 API 呼び出しのリトライやレート制御、及びフェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定のラッパー `settings`
- data
  - jquants_client: J‑Quants API クライアント（ページネーション・リトライ・トークン自動更新・保存関数）
  - pipeline / etl: 日次 ETL パイプライン（市場カレンダー・株価・財務の差分取得、品質チェック）
  - calendar_management: 営業日判定、next/prev_trading_day 等
  - news_collector: RSS 取得と raw_news への冪等保存（SSRF対策・サイズ制限・トラッキングパラメータ除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ（signal_events, order_requests, executions）のスキーマ作成 / 初期化
  - stats: zscore 正規化等の汎用統計ユーティリティ
- ai
  - news_nlp.score_news: 時間ウィンドウ内のニュースを銘柄ごとにまとめて LLM に送り ai_scores を作成
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を作成
  - OpenAI 呼び出しは再利用しやすく、テスト時は内部呼び出しをモック可能
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー等

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントと新しい構文を使用）
- DuckDB、OpenAI クライアント等の依存パッケージ

推奨手順（例）:

1. リポジトリをチェックアウトして開発環境に入る
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必須パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （他にも urllib 系や標準ライブラリで十分な箇所がありますが、上記は主要依存です）

4. 環境変数 / .env を準備
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます（テスト時に無効化可）。

   必須 (Settings 参照):
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>

   任意:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動読み込みを無効化する）

   OpenAI API を使う場合:
   - OPENAI_API_KEY=<your_openai_api_key>
   （score_news / score_regime の api_key 引数でも渡せます）

---

## 使い方（簡易サンプル）

以下はライブラリをインポートして主要処理を実行する例です。実行は Python スクリプトから行います。

- DuckDB 接続を作って ETL を日次実行する（例: run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを付与して ai_scores テーブルへ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY が設定されていれば api_key を省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env または引数で指定
```

- 監査ログ用の DuckDB 初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルに書き込みが可能
```

注意点:
- OpenAI への呼び出しはネットワーク依存であり、テスト時は内部の `_call_openai_api` をモックして返却値を制御できます（unit test を参照）。
- ETL 関数は内部で例外処理を行いますが、部分的な失敗は result.errors に蓄積されます。戻り値の ETLResult を確認してください。

---

## 設定・環境変数

主な環境変数（Settings で参照）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite 用パス（監視用など）
- KABUSYS_ENV (任意): development | paper_trading | live（デフォルト development）
- LOG_LEVEL (任意): DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- OPENAI_API_KEY (任意): OpenAI API キー（score_news / score_regime が使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（ユニットテストで便利）

.env ファイルはプロジェクトルートに置くと自動で読み込まれます。プロジェクトルートはこのパッケージの __file__ を親方向に探索して `.git` または `pyproject.toml` の位置を基準に検出されます。

---

## テスト・開発時のヒント

- OpenAI 呼び出し（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテストでモック可能です。
- ネットワーク呼び出し（jquants_client._request, news_collector._urlopen）もテストでは差し替える設計になっています。
- DuckDB はインメモリ接続（":memory:"）を利用してユニットテストを実行すると高速で簡便です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと簡単な説明です。

- kabusys/
  - __init__.py: パッケージ定義、version
  - config.py: 環境変数・設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースの LLM センチメント解析 / ai_scores 書き込み
    - regime_detector.py: 市場レジーム判定（MA + マクロニュース合成）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult の再エクスポート
    - calendar_management.py: マーケットカレンダー管理と営業日判定
    - news_collector.py: RSS 取得と raw_news 保存（SSRF対策等）
    - quality.py: データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py: zscore_normalize など汎用統計関数
    - audit.py: 監査ログスキーマの初期化・index 定義
  - research/
    - __init__.py
    - factor_research.py: Momentum / Value / Volatility 等の計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ の下にはさらに細かなユーティリティやテストフックがあります。

プロジェクトルート（.git または pyproject.toml のある場所）に .env を置くことで config が自動読み込みします。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で抑制可能です。

---

## 最後に

この README はコードベースから抽出された機能説明と基本的な利用方法をまとめたものです。実運用や本格的な開発を行う際は、各モジュールの docstring・ロギング出力・テストケースを参照のうえ、設定（API トークンや DB パス等）を適切に管理してください。必要であれば README にさらに運用手順（cron / systemd / Docker 化）や実践的なサンプル（ETL スケジュール例・Slack 通知ハンドラ等）を追加できます。