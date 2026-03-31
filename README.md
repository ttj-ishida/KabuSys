# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）によるデータ取得、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（監査テーブル）など、取引戦略の研究から運用までを想定したユーティリティ群を提供します。

主な設計方針
- ルックアヘッドバイアス回避（バックテスト用に datetime.today()/date.today() を安易に参照しない）
- DuckDB を中心としたローカル DB によるデータ永続化
- 冪等性（ON CONFLICT / idempotent save）とフェイルセーフ（API 失敗時の安全なフォールバック）
- OpenAI（gpt-4o-mini）を用いたニュース・マクロセンチメント評価（JSON Mode を利用）

---

## 機能一覧
- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出、.env / .env.local）
- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（fetch / save）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
  - ニュース収集（RSS → raw_news、前処理・SSRF対策・トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
- AI（kabusys.ai）
  - ニュースセンチメントスコアリング（score_news）
  - マクロ + ETF MA による市場レジーム判定（score_regime）
- 研究ツール（kabusys.research）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）など

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.10 以上

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 最小依存例:
     - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは pyproject.toml / requirements.txt がある想定です。ローカル開発用に editable install があるなら:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` と `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（運用機能がある場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知連携が必要な場合
   - 任意 / 既定値:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API / 例）

以下は簡単な利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続と ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルを settings.duckdb_path から開く
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日の日付が使われます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} tickers")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（発注・約定ログ用）
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を初期化（":memory:" でインメモリ）
audit_conn = init_audit_db("data/audit.duckdb")
```

- 研究用関数（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# レコードは [{'date': ..., 'code': '1234', 'mom_1m': ..., ...}, ...]
```

- J-Quants トークン取得（内部で自動処理されるが手動で取得も可能）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点
- OpenAI 呼び出しは料金が発生します。API キーと利用ポリシーを確認してください。
- run_daily_etl 等の ETL はネットワーク / API 依存です。ネットワークや API のレスポンスに備えたエラーハンドリングが組み込まれていますが、本番ではログや監視を必ず設定してください。

---

## ディレクトリ構成

リポジトリ（src/kabusys 配下）の主なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー操作/更新
    - etl.py                  — ETL インターフェース再エクスポート
    - pipeline.py             — 日次 ETL パイプライン(run_daily_etl 等)
    - stats.py                — 統計ユーティリティ (zscore_normalize)
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ (監査テーブル定義 / init)
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS ニュース収集（SSRF対策・前処理）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - research/__init__.py

各モジュールは docstring に設計方針、使用方法、返り値・副作用（DB を更新するか等）が詳細に記載されています。

---

## 実運用上の注意
- 環境分け（development / paper_trading / live）を settings.env で切り替えられます。live 環境では発注周りの安全対策を厳格に行ってください。
- 監査テーブル（audit）は削除せず履歴を残す設計です。バックアップ運用を検討してください。
- API レート制限や課金を考慮してバッチ運用（夜間 ETL、API バッチ）を推奨します。
- OpenAI 呼び出しはレスポンス形式のバリデーションを行いますが、モデルの挙動変更に備えてレスポンスパースの堅牢化や例外監視を行ってください。

---

必要なら、README に含めたい追加情報（例: サンプル .env.example、CI / local run の手順、より詳細なコード参照セクション）を教えてください。README をプロジェクトの実際のパッケージ定義（pyproject.toml）やテストコマンドに合わせて調整できます。