# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
J-Quants / kabuステーション / OpenAI（LLM）を組み合わせて、データ収集（ETL）、品質チェック、ニュースのNLP評価、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを差分で取得・保存（ページネーション・レート制御・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質管理
  - 欠損、重複、将来日付、スパイク検出などの品質チェック群（quality モジュール）
  - 日次 ETL パイプライン（run_daily_etl）で品質チェックの実行可能

- ニュース収集・NLP
  - RSS フィードからニュースを安全に収集して raw_news に保存（SSRF / Gzip / XML の安全対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュースと ETF の移動平均乖離を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）

- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（data.audit）
  - order_request_id を冪等キーとして二重発注防止

- 設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - settings オブジェクト経由で環境変数を安全に参照（型チェック、必須チェック）

---

## 必須環境変数（主なもの）

README にある機能を動かすには少なくとも以下を設定してください（.env 推奨）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（利用する場合）
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID（利用する場合）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
- KABUSYS_ENV — (任意) "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — (任意) "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

自動 .env 読み込みは、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると無効化できます。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python（3.10+ を想定）を用意します。
2. リポジトリをクローンしてパッケージをインストールします（開発モード推奨）:

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e ".[all]"  # もし extras を用意している場合
   ```

   必要な主要パッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   上記が揃えば core 機能は動作します。プロジェクトの requirements.txt / pyproject.toml を参照して追加パッケージをインストールしてください。

3. プロジェクトルートに `.env` を置いて環境変数を設定します（config モジュールが自動ロードします）。

4. データ格納用ディレクトリ（デフォルト: `data/`）を作成するか、環境変数でパスを上書きします:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB, デフォルト: data/monitoring.db）

---

## 使い方（主要な例）

以下は簡単な Python スニペット例です。実行前に `.env` を用意し、必要な API キーを設定してください。

- DuckDB 接続の作成:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（run_daily_etl）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 対象日を指定するか省略して今日で実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄ごと）を取得して ai_scores に書き込む:

```python
from datetime import date
from kabusys.ai import score_news  # ai.__init__ でエクスポート済み

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム評価（ETF 1321 の MA200 乖離 + マクロニュース）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（監査専用 DuckDB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 研究用ファクター計算（例: Momentum）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（date, code, mom_1m, ...）
```

テストや CI で LLM 呼び出しを差し替えたい場合、モジュール内の `_call_openai_api` を unittest.mock.patch でモックする設計になっています。

---

## 実装上の注意点・設計方針（抜粋）

- Look-ahead バイアス対策
  - 各モジュールは内部で datetime.today() / date.today() を直接参照しないよう配慮（外部から target_date を注入）。
  - ETL / AI スコアリングは target_date 未満のデータのみを参照する等の対策がされています。

- フォールトトレランス
  - LLM API や J-Quants API 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時は中立値で続行）を採用。
  - DB 書き込みはトランザクションで包み、失敗時にロールバックする設計。

- セキュリティ
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限等を実装。
  - .env の自動ロードはプロジェクトルート検出に基づき行い、必要に応じて無効化可能。

---

## ディレクトリ構成（主要部分）

以下は src/kabusys 配下の主要ファイル / モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定管理、.env 自動ロード、settings オブジェクト
  - ai/
    - __init__.py — score_news をエクスポート
    - news_nlp.py — ニュース NLP（銘柄別センチメント）とバッチ処理
    - regime_detector.py — ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py — RSS 収集と前処理
    - quality.py — データ品質チェック群
    - stats.py — 統計ユーティリティ（zscore_normalize など）
    - audit.py — 監査ログスキーマ、初期化ユーティリティ
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター実装
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - research/*（ユーティリティやラッパー）

（リポジトリのルートには pyproject.toml / .git があると config の自動 .env 検出が動作します）

---

## テスト / 開発ヒント

- 環境変数の自動ロードを無効にするには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト環境で明示的に環境をコントロールしたい場合に便利です。

- OpenAI 呼び出しやネットワークを伴う部分はモック可能なフックが組み込まれています（例: ai.news_nlp._call_openai_api / regime_detector._call_openai_api、news_collector._urlopen など）。

- DuckDB を使うため、スキーマやテーブルは ETL 実行前に用意しておくか、別途 schema 初期化機能（未提供の場合は SQL で作成）を実行してください。audit.init_audit_db は監査用テーブルを作成します。

---

## 付記

この README はコードベースの主要機能・セットアップ方法・簡易利用例をまとめたものです。詳細な API 仕様や DB スキーマの列定義、運用手順についてはプロジェクト内の各モジュールの docstring（ソースコード内コメント）を参照してください。必要であれば README に具体的な SQL スキーマや運用例、Docker / systemd などのデプロイ手順を追記できます。