# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（オーディット）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコア機能を提供する Python パッケージです。主な目的は以下です。

- J-Quants API を用いた市場データ / 財務データ / マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を使った記事・銘柄別センチメントスコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）の永続化スキーマ管理
- データ品質チェック（欠損・スパイク・重複・日付不整合など）

設計方針として「ルックアヘッドバイアスの排除」「冪等性の確保」「外部 API 呼び出しの堅牢なリトライ処理」「DuckDB を中心とした軽量ストレージ」を重視しています。

---

## 機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（jquants_client 経由で差分取得・保存）
  - ETL 結果は ETLResult に集約
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- ニュース収集
  - RSS フィード取得（SSRF 対策・サイズ上限・トラッキング除去）
  - raw_news / news_symbols への冪等保存処理（news_collector）
- AI（OpenAI）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF (1321) の MA 乖離とマクロニュースを合成して market_regime を書き込み
  - 両関数は api_key 引数か環境変数 OPENAI_API_KEY を使用
- リサーチ（研究用）
  - calc_momentum / calc_value / calc_volatility（factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（feature_exploration）
  - zscore_normalize（data.stats）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db：監査用テーブル（signal_events, order_requests, executions）を初期化
- J-Quants クライアント（jquants_client）
  - fetch & save 系 API（daily_quotes, financial_statements, market_calendar, listed_info）
  - rate limiter、リトライ、ID トークン自動リフレッシュ、DuckDB への冪等保存を実装

---

## 必要条件（依存ライブラリ）

最低限の依存例（プロジェクトにより変動する可能性があります）:

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例:

```bash
# 開発インストール（プロジェクトルートで）
pip install -e .
# または必要なパッケージを個別に
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動
2. 仮想環境作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くことが可能）

自動 .env ロードの挙動:
- 起動時にプロジェクトルート (.git または pyproject.toml を基準) を探索して、優先順位に従って読み込みます:
  - OS 環境変数 > .env.local > .env
- 自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）

主要な環境変数（必須/推奨）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（実運用時）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（必要であれば）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必要に応じて) — OpenAI 呼び出し用 API キー（news_nlp/regime_detector で使用）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は最小限の利用例。DuckDB 接続は duckdb.connect() を用います。

1) 基本的な ETL の実行（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコア算出（OpenAI API を使用）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を直接渡すことも可能。省略時は環境変数 OPENAI_API_KEY を使用
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} stocks")
```

3) 市場レジーム判定（ETF 1321 とマクロニュースの合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 例えば settings.duckdb_path.parent / "audit.duckdb"
audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
```

注意点:
- AI 関連関数（score_news, score_regime）は OpenAI の呼び出しを行います。テスト時は内部の _call_openai_api をモックして API 呼び出しを差し替える設計になっています。
- ETL / API 呼び出しは冪等性とリトライを考慮して実装されていますが、実行ログを確認してエラーや品質問題を検出してください。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリは src/kabusys 以下に配置されています。主要ファイル:

- src/kabusys/__init__.py
  - パッケージ定義とエクスポート

- src/kabusys/config.py
  - 環境変数の自動ロード、Settings クラス（設定取得ユーティリティ）

- src/kabusys/ai/
  - news_nlp.py: ニュースの集約・OpenAI による銘柄別センチメント算出（score_news）
  - regime_detector.py: ETF とマクロニュースで市場レジームを日次判定（score_regime）
  - __init__.py: ai パッケージのエクスポート

- src/kabusys/data/
  - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
  - jquants_client.py: J-Quants API クライアント（fetch / save / 認証 / rate-limit / retry）
  - news_collector.py: RSS 取得と raw_news への保存
  - calendar_management.py: マーケットカレンダーの管理と営業日判定
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログスキーマの定義・初期化（signal_events, order_requests, executions）
  - etl.py: ETLResult の再エクスポート

- src/kabusys/research/
  - factor_research.py: Momentum / Value / Volatility / Liquidity 等の計算
  - feature_exploration.py: 将来リターン計算、IC、統計要約、ランク関数
  - __init__.py: 研究用 API の再エクスポート

その他:
- data/ ディレクトリを想定（デフォルトで DuckDB 等を保存）
- .env.example（存在すれば参照）を元に .env を作成してください

---

## 開発者向けメモ / 注意事項

- ルックアヘッドバイアス対策: 多くの関数は date.today() / datetime.today() を直接参照せず、呼び出し側で target_date を明示する設計です。バックテスト等では明示的な日付を渡して使用してください。
- 再現性: ETL や保存処理は基本的に冪等（ON CONFLICT / DO UPDATE）で実装されています。
- テスト: OpenAI の呼び出しやネットワークアクセス部分は内部関数をモック可能な形で実装されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- ログ: settings.log_level に従いログ出力レベルを制御します。運用時は KABUSYS_ENV を適切に設定してください（paper_trading / live）。

---

この README はリポジトリ内のソースコード（src/kabusys）に基づいて作成しています。導入や実運用を行う前に環境変数、DB パス、API キーなどが正しく設定されていることを必ず確認してください。必要であれば各モジュールの docstring を参照して詳細挙動を確認してください。