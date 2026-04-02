# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、研究用ファクター計算、監査ログ（取引トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・自動売買に必要となる共通機能群をまとめたパッケージです。主な目的は以下：

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント・マクロセンチメント評価
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）を保管する DuckDB スキーマ生成
- データ品質チェック（欠損、スパイク、重複、日付整合性）

設計方針として「Look-ahead bias の排除」「冪等性」「フェイルセーフ（API障害時の妥当なフォールバック）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証、ページネーション、保存用関数）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（銘柄ごとのニュースセンチメント: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成: score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索 / IC / 統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env または環境変数からアプリ設定をロードする Settings（自動ロード機能あり）

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（型ヒントの | 演算子や型注釈を使用）
- pip install で入れる主な依存:
  - duckdb
  - openai
  - defusedxml

推奨インストールコマンド（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時は -e . (パッケージ化されていれば) やテスト依存を追加
```

（リポジトリに requirements.txt があればそちらを利用してください。）

---

## 環境変数（主な設定）

パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動的に読み込みます（無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（Settings._require により必須となるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（実環境での発注に利用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

OpenAI / その他:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 内で使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境 (development, paper_trading, live)
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

.env.example をプロジェクトルートに置いて設定してください。

---

## セットアップ手順（ローカル開発向けの簡単な流れ）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存をインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトがパッケージ化されていれば pip install -e .）
4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
5. DuckDB 用ディレクトリを用意（必要に応じて）
   - mkdir -p data

---

## 使い方（例）

基本は Python スクリプトやスケジューラー（cron / systemd timer）から各 API を呼び出して使います。

- DuckDB 接続（例）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（株価・財務・カレンダー取得＋品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で設定しておく
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 を用いた MA200 + マクロセンチメント合成）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査用 DB を別に用意したい場合）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を既存 conn に対して実行
```

- 研究用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentums = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は dict のリスト: [{ "date": ..., "code": "1301", "mom_1m": ..., ...}, ...]
```

注意点:
- news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY または api_key 引数が必要です。
- ETL 周り（J-Quants）の呼び出しは JQUANTS_REFRESH_TOKEN の設定が必須です。
- DuckDB バージョンによって executemany の挙動が異なる場合があるため、空パラメータを渡さないように設計されています（実装済み）。

---

## ディレクトリ構成

（リポジトリの src/kabusys を抜粋した構成）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄別ニュースセンチメント算出（OpenAI）
    - regime_detector.py     — マーケットレジーム判定（ETF1321 MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプラインと run_daily_etl
    - etl.py                 — ETLResult 型の公開
    - calendar_management.py — マーケットカレンダー判定と更新ジョブ
    - news_collector.py      — RSS 取得・前処理・保存
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - research, ai, data の各モジュールは互いに適切に分離されており、本番口座へのアクセスは execution/発注モジュール（将来的実装）に限定できる設計です。

---

## 運用上の注意 / ベストプラクティス

- 環境変数は CI / 本番ではシークレット管理ツール（Vault / Secrets Manager 等）で管理してください。`.env` をコミットしないでください。
- OPENAI API 呼び出しはレートやコストに注意。バッチ化・チャンク化やリトライ・バックオフは既に実装されていますが、運用ルールを定めてください。
- ETL は定期実行（夜間バッチ）を想定しています。日付調整やカレンダーの先読みは pipeline.run_daily_etl が扱います。
- 監査ログ（audit）スキーマは冪等に作成されますが、本番移行時はバックアップ・マイグレーション方針を検討してください。
- テスト時は自動 .env ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）すると良いです。OpenAI 呼び出しなどはモック化してテストしてください。

---

## 追加情報 / 開発メモ

- self-contained な SQL / DuckDB による処理を基本とし、外部状態への依存を最小化しているため、バッチ処理やバックテスト環境に組み込みやすい設計です。
- OpenAI 呼び出し部分はレスポンスの堅牢性（JSON モードでも余計なテキストが混ざるケースへの対応）や再試行ロジックを持ち、安全にフェイルオーバーします。
- news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）、defusedxml による XML パース保護、レスポンスサイズ制限などセキュリティ面の配慮をしています。

---

必要であれば、README に以下を追加で記載できます：
- 具体的な schema 定義（テーブル DDL の抜粋）
- systemd / cron での日次ジョブの例
- Dockerfile / compose のテンプレート
- テスト実行方法・ユニットテスト方針

どの情報を追加したいか教えてください。