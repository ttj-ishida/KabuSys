# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株のデータ取得・ETL、ニュース NLP、ファクター計算、監査ログ、簡易的な戦略リサーチ用ユーティリティを提供する Python パッケージです。本リポジトリはバックテスト／研究／本番運用のデータ基盤と一部の AI 支援モジュール（OpenAI）を含みます。

主な設計方針:
- ルックアヘッドバイアスを避ける（日時参照やクエリの排他条件に注意）
- DuckDB を中心としたローカル DB ベースの ETL と品質チェック
- API 呼び出しにはリトライ・レート制御を実装
- 冪等性を重視した DB 書き込み（ON CONFLICT / DELETE→INSERT のパターン等）
- テスト可能性を考慮して API キー注入や自動 .env 読み込みの無効化が可能

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）について
- 使い方（代表的な呼び出し例）
- ディレクトリ構成

---

プロジェクト概要
- データ取得: J-Quants API 経由で株価（OHLCV）、財務データ、JPX カレンダー等を取得するクライアント（rate limiting / retry / token refresh 対応）
- ETL: 差分取得、保存、品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集: RSS から記事取得・正規化・raw_news 保存（SSRF 対策、サイズ制限）
- AI: OpenAI を使ったニュース NLP（銘柄別センチメント）とマクロセンチメント＋MA200 での市場レジーム判定
- 監査ログ: シグナル→発注→約定のトレーサビリティを担保する監査テーブル初期化ユーティリティ
- 研究用: ファクター計算・将来リターン・IC 計算・統計サマリーなどのユーティリティ

---

機能一覧（抜粋）

- kabusys.config
  - Settings: 環境変数取り扱い、.env 自動ロード（プロジェクトルート検出）
  - 必須変数チェック（_require）

- kabusys.data
  - jquants_client: J-Quants API クライアント + DuckDB 保存関数
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 取得・正規化・前処理
  - calendar_management: 営業日判定 / next_trading_day / get_trading_days / calendar_update_job
  - audit: 監査ログスキーマ作成（init_audit_schema, init_audit_db）
  - stats: zscore_normalize 等

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込む

- kabusys.research
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量分析・統計）

---

セットアップ手順

前提:
- Python 3.10+（コードの型記述で Union | を使用しているため）を推奨
- DuckDB, OpenAI Python SDK, defusedxml 等の依存パッケージが必要

例: 仮想環境作成・インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージ例（実プロジェクトの pyproject.toml / requirements を参照してください）
pip install duckdb openai defusedxml
# 開発時にパッケージを editable インストール
pip install -e .
```

（注）requirements ファイルや pyproject.toml がある場合はそちらを参照してください。

---

環境変数（.env）について

設定は環境変数またはプロジェクトルートの .env/.env.local から読み込まれます。読み込み優先順位:
OS 環境変数 > .env.local > .env

自動ロードを無効化したい場合（テスト等）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な環境変数（本システムで参照される例）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャネル ID（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 呼び出し時に必要）
- DUCKDB_PATH : デフォルト DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite DB パス（省略時 data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live
- LOG_LEVEL : DEBUG/INFO/...

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

KabuSys 内の Settings は未設定の必須キーに対して ValueError を投げます（早期検出のため）。

---

使い方（代表的な例）

1) DuckDB 接続の準備（デフォルトパスを使う場合）
```python
import duckdb
# デフォルトパスを使う場合は settings.duckdb_path を参照してもよい
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants トークンは settings か id_token 引数で注入）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

4) 市場レジーム判定（OpenAI API キーが必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

5) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_duck.db")
# conn_audit は監査用テーブルが作成済みの DuckDB 接続
```

6) 研究系ファクターの計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意点:
- AI 呼び出しは外部APIに依存するため、ローカルテストではモック（unittest.mock）で差し替えることを推奨します。各モジュールは _call_openai_api を patch しやすい構成です。
- ETL / 保存処理はいずれも冪等設計になっていますが、DuckDB のバージョンに依存する挙動（executemany 空リスト等）に注意してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP スコアリング（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント / 保存関数
    - pipeline.py                       — ETL パイプライン / run_daily_etl
    - etl.py                            — ETLResult 再エクスポート
    - news_collector.py                 — RSS 取得・前処理
    - calendar_management.py            — マーケットカレンダー管理 / 営業日判定
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログスキーマ初期化
    - stats.py                          — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — 将来リターン・IC・統計サマリー

（リポジトリには上記以外にも補助的モジュールやユーティリティが含まれます。実際のファイル一覧はリポジトリルートで確認してください。）

---

運用上のヒント / 注意事項
- J-Quants API はレート制限があるため、jquants_client は内部で固定間隔レートリミッタを用いています。個別で多量のリクエストを投げる場合は注意してください。
- OpenAI 呼び出しは失敗時にフェイルセーフとしてスコア 0.0 を返す設計の箇所があります。運用ポリシーに応じたログ監視・再実行戦略を用意してください。
- settings.env に設定ミスがあると早期に ValueError を投げる仕組みになっています。ci / production 環境での環境変数管理に注意してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップ・排他アクセス（複数プロセス並行実行）については運用で対処してください。

---

サポート / 開発
- テストや CI を追加する際は、環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うとテスト用の環境セットアップが容易になります。
- OpenAI / J-Quants への実際の API 呼び出しはモックしやすい構造になっているため、ユニットテストは外部依存を切り離して実装してください。

---

この README はコードベースの説明を中心にまとめたものです。実際の導入・運用では pyproject.toml / requirements.txt / デプロイスクリプト、ならびに運用ドキュメントを合わせて参照してください。