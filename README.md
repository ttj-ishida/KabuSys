# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買向けユーティリティ群をまとめた Python パッケージです。  
DuckDB をデータ層に用い、J-Quants / RSS / OpenAI 等と連携して以下を実現します。

- ETL パイプライン（株価・財務・カレンダー）
- データ品質チェック
- ニュースの NLP スコアリング（OpenAI）
- 市場レジーム判定（テクニカル + マクロセンチメント）
- 研究用ファクター計算 / 特徴量解析
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ

注意: このリポジトリには発注ロジックの骨組みや実行監査用テーブル定義が含まれますが、実際のブローカー送信部分は別モジュール／実装を要します。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得 / 保存 / トークン管理 / レート制御）
  - ニュース収集（RSS）および前処理
  - カレンダー管理（営業日判定 / next/prev_trading_day）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化（監査用テーブル定義・インデックス）
- ai
  - score_news: ニュースを LLM（gpt-4o-mini）でセンチメント解析して ai_scores に保存
  - score_regime: 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- research
  - ファクター計算: momentum / value / volatility
  - 特徴量探索: forward returns / IC / 統計サマリー
  - zscore_normalize：クロスセクション Z スコア正規化
- config
  - .env / 環境変数の自動読み込み・保護・必須チェック
  - settings オブジェクト経由で設定値を取得

---

## 要件（推奨）

- Python 3.10+
- 基本的な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS）

（実際の requirements.txt / pyproject.toml をプロジェクトに合わせてご用意ください）

---

## 環境変数（主なもの）

このプロジェクトは .env（および .env.local）ファイルまたは環境変数を優先して使用します。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN -- J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD -- kabu ステーション API パスワード（発注用、実装次第で利用）
- SLACK_BOT_TOKEN -- Slack 通知用ボットトークン
- SLACK_CHANNEL_ID -- Slack 通知先チャンネル ID
- OPENAI_API_KEY -- OpenAI 呼び出し（ai.score_news / ai.score_regime など）

任意/デフォルト設定:
- KABUSYS_ENV (development / paper_trading / live) - デフォルト: development
- LOG_LEVEL (DEBUG/INFO/...) - デフォルト: INFO
- DUCKDB_PATH - デフォルト: data/kabusys.duckdb
- SQLITE_PATH - デフォルト: data/monitoring.db

注意: Settings クラスのプロパティは未設定時に ValueError を出すものがあります（必須項目）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン:
   git clone <repo-url>
2. Python 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）:
   pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt や pyproject.toml があればそれに合わせてください）
4. 開発モードでインストール（任意）:
   pip install -e .
5. .env を作成:
   プロジェクトルートに .env を作成し、上記の必須環境変数を設定してください。
   例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C...
     KABU_API_PASSWORD=...

---

## 使い方（主要な例）

以下はパッケージをインポートして利用する最小例です。実運用では DB スキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily, etc.）の初期化が必要です。

- DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を実行（必要な環境変数を設定済みであること）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定（ai.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db

# file path: e.g. "data/audit.duckdb" or ":memory:"
conn = init_audit_db("data/audit.duckdb")
# 以降、conn を使って監査テーブルへ挿入やクエリが可能
```

注意点:
- ai モジュールは OpenAI の JSON Mode を利用する想定です。API レスポンスの整合性やレート制御に注意してください。
- ETL / AI 関数はルックアヘッドバイアス防止のために内部で date 引数を受け取り、datetime.today() を直接参照しない設計です。
- J-Quants API 呼び出しは内部でトークンのリフレッシュやレート制御、リトライを行いますが、適切な認証情報を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（score_news）
    - regime_detector.py             -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                    -- ETL パイプライン / run_daily_etl 等
    - jquants_client.py              -- J-Quants API クライアント・保存ロジック
    - news_collector.py              -- RSS 収集・前処理
    - calendar_management.py         -- 市場カレンダー管理
    - quality.py                     -- データ品質チェック
    - stats.py                       -- 共通統計ユーティリティ（zscore_normalize）
    - audit.py                       -- 監査ログテーブル初期化
    - etl.py                         -- ETL インターフェース再公開
  - research/
    - __init__.py
    - factor_research.py             -- Momentum/Value/Volatility
    - feature_exploration.py         -- forward returns / IC / summary
  - ai/、data/ などの他モジュール（strategy / execution / monitoring は __all__ に含まれる想定）

（上記は主要ファイルの抜粋です。実際のリポジトリにはドキュメント・テスト等が含まれる可能性があります）

---

## 設計上の注意点 / ポイント

- Look-ahead Bias の抑制: AI スコアリング / レジーム判定 / ETL は日付引数ベースで実行するよう設計し、内部で現在時刻を直接参照しないように配慮されています。
- 冪等性: J-Quants から取得したデータの保存は ON CONFLICT（アップサート）で実装され、再実行に耐える設計です。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）の一時エラーはリトライやデフォルト値（例: macro_sentiment=0）で処理を継続する方針です。
- セキュリティ:
  - RSS フィード取得では SSRF 対策（プライベートアドレス排除・リダイレクト検査）を実装しています。
  - defusedxml を利用して XML パースの脆弱性を軽減しています。

---

## 貢献 / 開発

- バグ修正・機能追加は PR を歓迎します。
- ユニットテスト（特に外部 API 呼び出し箇所）はモックを用いて実装してください（コード中に差し替え用フックがあります）。
- .env.example や docker / CI の設定があれば README に追記してください。

---

この README はコードベースの主要機能と利用方法をまとめたものです。より詳細な設計文書（StrategyModel.md / DataPlatform.md）や API の利用方法についてはリポジトリ内の別ファイルや運用ドキュメントを参照してください。必要があれば README に追記・改善します。