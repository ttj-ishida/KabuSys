# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、調査用ファクター計算、監査ログ用スキーマなど、売買戦略の構築と運用に必要な基盤処理を提供します。

---

## 機能一覧

主な機能（モジュール）:
- 設定管理
  - .env 自動読み込み（.env.local > .env）、必須環境変数チェック
- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（株価・財務・カレンダー取得、ページネーション・リトライ・レート制御）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - マーケットカレンダー管理（営業日判定・前後営業日探索・夜間更新ジョブ）
  - ニュース収集（RSS、URL正規化、SSRF対策、XML安全パース）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（signal, order_request, executions 等）
  - 汎用統計ユーティリティ（Zスコア正規化）
- AI（kabusys.ai）
  - ニュースセンチメント分析（gpt-4o-mini を想定、JSON Mode）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
- 研究（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索 / IC 計算 / サマリー統計

設計上のポイント:
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない等）
- DuckDB をデータレイクとして使用（SQL + Python のハイブリッド）
- API 呼び出しはリトライ・バックオフ・レート制御を備えフェイルセーフ
- 冪等性を重視（DB 保存は ON CONFLICT / 単一トランザクションでの操作など）

---

## 必要条件（Prerequisites）

- Python 3.9+（typing 機能のため 3.9 以降を想定）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- J-Quants リフレッシュトークン、OpenAI API Key 等の外部資格情報

（実際の依存リストはプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクト配置）
   - 例: git clone ...

2. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install -r requirements.txt
     - または、開発中であればプロジェクトルートで: pip install -e .

   主要パッケージ例:
   - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - .env.example を参考にして .env を作成してください（プロジェクトルート）。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 環境変数（主なもの）

必須（モジュールで _require() を使用しているもの）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN       - Slack 通知（必要な場合）
- SLACK_CHANNEL_ID      - Slack チャンネルID
- KABU_API_PASSWORD     - kabuステーション連携パスワード（発注系を使う場合）

任意 / デフォルトあり:
- KABUSYS_ENV          - 開発/ペーパー/本番: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL            - ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 自動 .env ロードを無効化（値を set すれば動作）
- KABUSYS_API_BASE_URL - kabu API ベース URL（デフォルトは http://localhost:18080/kabusapi）
- DUCKDB_PATH          - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH          - SQLite（監視用）パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY       - OpenAI API キー（AI モジュール利用時）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

以下は Python API を使った基本的な呼び出し例です。各関数は DuckDB 接続を引数に取る設計です。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントを計算して ai_scores テーブルに書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written scores: {written}")
```

3) 市場レジームをスコアリングして market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ専用 DB の初期化（監査テーブルを含む）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order/signals の挿入や参照が可能
```

注意:
- OpenAI 呼び出しを行う関数は api_key を引数で受け取れます（指定しない場合は環境変数 OPENAI_API_KEY を参照）。
- ETL / API 呼び出しはネットワーク依存・API 資格情報が必須です。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主なソースツリー（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存関数）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集（SSRF 対策・XML安全化）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore 正規化）
    - audit.py                — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリ

（この README にないサブパッケージや将来のモジュールがあります。実装の詳細は各モジュールの docstring を参照してください）

---

## 開発・テスト

- 設定: テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます。
- モジュール内の外部呼び出し（OpenAI / J-Quants / ネットワーク）については unittest.mock を用いた差替え（patch）が想定されています（各モジュール内に _call_openai_api 等の差替えポイントあり）。
- DuckDB はインメモリ（":memory:"）でも初期化可能な関数（init_audit_db 等）を提供しています。単体テストではインメモリ DB を利用すると便利です。

---

## 注意事項 / 運用上のヒント

- OpenAI の呼び出しはコストが発生します。ローカルテストではモックを使うことを推奨します。
- J-Quants API のレート制限と認証フローに注意してください（モジュールはレート制御とトークン自動リフレッシュを実装しています）。
- データのルックアヘッド防止設計が多くの場所に組み込まれているため、バックテストで日付を扱う場合は各関数の引数（target_date 等）を明示的に渡して利用してください。
- news_collector は RSS のパースで defusedxml を使用し、SSRF 対策・レスポンスサイズチェック等の保護を実装しています。

---

もし README の出力に含めたい「動作環境の詳細（pyproject / requirements）」や「サンプル .env.example」を提供いただければ、それに合わせて README を更新します。