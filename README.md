# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。ETL、ニュースNLP、ファクター計算、監査ログ、マーケットカレンダー管理などを備え、DuckDB を中心としたデータパイプラインと OpenAI を用いたニュースセンチメント評価を行います。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API障害時は安全にフォールバック）」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト経由）
- データ ETL（J-Quants API 経由）
  - 株価日足（raw_prices）取得 / 保存（ページネーション・レート制御・リトライ）
  - 財務データ取得 / 保存（raw_financials）
  - JPX マーケットカレンダー取得 / 保存（market_calendar）
  - 日次 ETL パイプライン（run_daily_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集 & NLP
  - RSS 収集（SSRF・サイズ制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースの LLM ベース評価と ETF MA の組合せによる市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - シグナル→発注→約定まで追跡する監査テーブル定義・初期化（DuckDB）
  - 冪等性・ステータス管理・UTC タイムスタンプの運用サポート

---

## セットアップ

前提
- Python 3.10+ を推奨（3.10 以降の構文を使用）
- DuckDB を利用（pip パッケージ）
- OpenAI API（ニュース NLP / レジーム判定）を使う場合は OpenAI API キーが必要

インストール（リポジトリルートで）:
```bash
# 開発インストール（setup.py/pyproject.toml がある前提）
pip install -e . 

# 必要な外部ライブラリ例（プロジェクトの requirements を参照してください）
pip install duckdb openai defusedxml
```

環境変数
（プロジェクトルートの .env / .env.local が自動で読み込まれます。読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。）

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知連携を使用する場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI 呼び出しに必要（score_news / score_regime）
（その他）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

.example .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- 自動ロードはパッケージの __file__ を基にプロジェクトルート（.git または pyproject.toml）を探索します。パッケージ配布後も CWD に依存せず動作する設計です。
- テスト等で自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主な例）

以下は Python REPL またはスクリプト内での利用例です。

共通準備（設定読み込み・DuckDB 接続）:
```python
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

1) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しないと today が使われる（内部では ETL 用に営業日調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース NLP スコアを付与（ai_scores テーブルへ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# target_date: スコア生成対象日（ニュースウィンドウは前日15:00 JST ～ 当日08:30 JST）
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

3) 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
# 戻り値 1 (成功)。結果は market_regime テーブルに書き込まれる。
```

4) 監査ログ用 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブル群が作成される
```

5) 研究用ファクター計算の呼び出し例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

テスト・開発のヒント
- OpenAI 呼び出しなど外部依存は関数内部でラップされており、ユニットテストではモック（unittest.mock.patch）して振る舞いを固定できます。
- 自動 .env ロードを無効化して環境を制御するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys パッケージに格納されています。主なモジュール:

- src/kabusys/
  - __init__.py               — パッケージメタデータ（__version__）
  - config.py                 — 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理・判定ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - news_collector.py       — RSS 収集モジュール
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ定義・初期化
    - etl.py                  — ETLResult の再公開インターフェース
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
  - monitoring/                — 監視系（未列挙のモジュールが想定される）
  - strategy/                  — 戦略層（別途実装想定）
  - execution/                 — 実行（注文）層（別途実装想定）

（実際のファイルは src/kabusys 以下に多数の補助関数・ユーティリティが含まれます。上は主要モジュールのサマリです。）

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - settings で必須値がチェックされます。README の .env 例を参考に設定してください。
- OpenAI 呼び出しで失敗する
  - APIキーの有無、レート制限、モデルの利用権限を確認してください。ライブラリはリトライやフェイルセーフ（失敗時は中立スコア 0.0）を実装していますが、キーが無い場合は明示的に例外になります。
- DuckDB ファイル/ディレクトリがない
  - settings.duckdb_path の親ディレクトリは自動作成する箇所がありますが、権限等で失敗する場合は手動で作成してください。
- テスト時に自動 .env ロードを抑制したい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ライセンス、貢献方法、詳細なアーキテクチャ設計（StrategyModel.md / DataPlatform.md 等のドキュメント）が別途ある想定です。必要であれば README に追記する項目（CI、テスト実行方法、詳しい例など）を教えてください。