# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主要な特徴

- データ取得
  - J-Quants API から株価（日足）・財務・上場情報・JPXカレンダーを取得（ページネーション・レート制御・自動リフレッシュ対応）
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
- ETL パイプライン
  - 差分取得、バックフィル、冪等保存（DuckDB）、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリポイント
- AI（OpenAI）連携
  - ニュースの銘柄別センチメント算出（gpt-4o-mini, JSON Mode）
  - マクロニュースと ETF（1321）200日移動平均乖離の合成による市場レジーム判定
  - エラーや API 制限に対するリトライ・フォールバック設計
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー、Z スコア正規化
- 監査（Audit）
  - シグナル → 発注 → 約定までの監査テーブル定義と初期化ユーティリティ（DuckDB）
  - 発注冪等性を考慮した設計（order_request_id を冪等キーとして使用）

---

## 動作要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、RSS、OpenAI）
- DuckDB（Python パッケージを使用）

（実際の requirements.txt/pyproject.toml をプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストールします（例）。

   ```bash
   pip install duckdb openai defusedxml
   ```

   - 実環境では pyproject.toml / requirements.txt を用意して `pip install -e .` や `pip install -r requirements.txt` を使ってください。

3. 環境変数を設定します。ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードは .git または pyproject.toml を基準にプロジェクトルートを特定します）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## .env（例）

以下は主な環境変数の例です。実運用時は機密情報を適切に扱ってください。

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API（必要な場合）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# データベース / ファイルパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視 / プロセス制御
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=1

# 環境 / ログ
KABUSYS_ENV=development         # development | paper_trading | live
LOG_LEVEL=INFO
```

- `settings`（kabusys.config.settings）から各値を参照できます。
- `settings` は自動的に `.env` → `.env.local`（上書き）を読み込み、OS 環境変数を保護します。

---

## 使い方（Python API の例）

以下は代表的な操作例です。DuckDB コネクションには `duckdb.connect(path)` を渡して使用します。

- 日次 ETL を実行する（J-Quants からデータ取得して保存・品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコア（銘柄別センチメント）する（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote ai_scores for {written} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを統合）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベースを初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算（例: momentum）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records: list of dict with keys ['date', 'code', 'mom_1m', 'mom_3m', 'mom_6m', 'ma200_dev']
```

注意:
- OpenAI を利用する関数は、api_key 引数でキーを注入可能。テストでは関数単位で API 呼び出しをモックしてください（コード中にモックしやすい箇所の説明があります）。
- 日付処理はルックアヘッドバイアス防止のため内部で datetime.today() を直接参照しない設計が多く、target_date を明示して呼び出すことが推奨されます。

---

## 設計上の注意点 / 実運用時のヒント

- 自動環境変数ロード
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- フォールバック / フェイルセーフ
  - OpenAI/API 失敗時は多くの処理がフォールバック値（例: マクロセンチメント = 0.0）で継続します。ログに警告が残るため監視してください。
- DuckDB executemany の制約
  - 一部の箇所で DuckDB 0.10 の executemany に空リストを渡すとエラーになるため、コードは空チェックを行っています。
- セキュリティ
  - RSS 収集では SSRF 対策（リダイレクト検査、プライベートIP拒否）や XML 関連の脆弱性対策（defusedxml）を実装しています。
- レート制御・リトライ
  - J-Quants 用に固定間隔によるスロットリングと、HTTP ステータスに応じた指数バックオフを実装しています。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（銘柄別スコア）
    - regime_detector.py         — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value 等
    - feature_exploration.py     — 将来リターン / IC / summary / rank
  - monitoring/ (注：監視関連モジュールが想定されています。コードベースに追加可能)
  - strategy/, execution/ (注：戦略・発注実行モジュール用の名前空間。実装はプロジェクト依存)

---

## テスト・デバッグのポイント

- OpenAI 呼び出しは _call_openai_api 等でラップされているため、unit test では該当関数を patch して期待するレスポンスを返すとテストが容易です（news_nlp, regime_detector 共にテスト用フックが設計されています）。
- J-Quants クライアントは id_token のキャッシュと自動リフレッシュ、レート制御が入っているため、実 API 呼び出しを行う場合は API レートと認証を意識してください。テスト時は jquants_client._request をモックするのが有効です。
- DuckDB をインメモリ（":memory:"）で初期化すると一時的な単体テストが行いやすいです（audit.init_audit_db は ":memory:" を受け入れます）。

---

## 参考 / 環境変数まとめ（抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（関数引数で注入可能）
- KABU_API_PASSWORD — kabu API パスワード（発注機能を使う場合）
- DUCKDB_PATH / SQLITE_PATH — データ保存パス
- KABUSYS_ENV — environment: development | paper_trading | live
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードの抑止

---

必要であれば README に次の項目も追加できます：
- requirements.txt / pyproject.toml の具体例
- CI / デプロイ手順
- 実運用での監視・アラート設計（例: LINE 通知統合方法）
- 既存スキーマ（DuckDB テーブル定義）一覧

追加希望があれば、用途（開発用 README / 運用手順 / API リファレンス など）を指定してください。