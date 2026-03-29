# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）でのデータ収集、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター計算、品質チェック、監査ログ（発注→約定のトレース）など、実運用を想定したコンポーネント群を提供します。

---

## 特徴（概要）

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB をストレージとして利用する ETL / 保存処理（冪等保存）
- ニュース収集（RSS）と LLM による銘柄別センチメントスコアリング（gpt-4o-mini）
- マクロニュース + ETF（1321）200日移動平均乖離を用いた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と研究ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 環境変数 / .env 自動ロード（プロジェクトルート検出・上書き制御・無効化フラグあり）

---

## 機能一覧（主要 API）

- データ収集 / ETL
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client.fetch_* / save_*（J-Quants 連携）
- データ品質
  - quality.run_all_checks(conn, ...)
- ニュース & NLP
  - news_collector.fetch_rss(...)
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
- 市場レジーム
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 監査ログ（初期化）
  - data.audit.init_audit_db(db_path)
  - data.audit.init_audit_schema(conn, transactional=False)
- 研究用ユーティリティ
  - research.calc_momentum / calc_value / calc_volatility
  - research.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- カレンダー管理
  - data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - data.calendar_management.calendar_update_job

---

## 必要要件（推奨）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（依存は環境に応じて requirements.txt / pyproject.toml で管理してください）

---

## セットアップ手順

1. リポジトリをクローンしてローカルに展開
   - 例: git clone ...

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージインストール（開発モード）
   - pip install -e ".[all]"  （プロジェクトの pyproject.toml / extras がある場合）
   - 最低限:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）に `.env` / `.env.local` を配置できます。パーサは Bash 風の key=value 形式に対応し、引用符・エスケープ・インラインコメントの扱いも考慮します。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数例
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client により ID トークン取得に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出し時に指定可）

設定値の補足（Settings API）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB 用、デフォルト data/monitoring.db）

---

## 使い方（クイックスタート）

以下は簡単な Python スニペット例です。適宜 logging 設定や例外処理を追加してください。

- DuckDB 接続の作成（デフォルトファイルパスを使用）
```python
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行（J-Quants ID トークンは settings から自動取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み／参照が可能
```

- ファクター計算（研究用途）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

---

## 重要な設計・運用上の注意点

- ルックアヘッドバイアス防止
  - 多くの関数は内部で datetime.today() を参照せず、明示的な target_date を受け取る設計です。バックテスト時は必ず履歴データのみを参照するようにしてください。

- .env パーサの挙動
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（#）の扱いなどをサポートしています。
  - OS 環境変数はデフォルトで保護され、.env は上書きされません。上書きを許可するには .env.local（override=True）を使うか、環境変数をクリアしてください。

- API レート制御・リトライ
  - J-Quants は固定間隔スロットリング（120 req/min）と指数バックオフで保護しています。OpenAI 呼び出しにもリトライ・バックオフ処理が組み込まれています。

- フェイルセーフ
  - LLM や外部 API が失敗した場合、致命例外を投げるのではなくフォールバック値（例: macro_sentiment=0.0）やスキップ動作をする箇所が設計上存在します。運用上はログを監視してください。

---

## ディレクトリ構成（概要）

（主要ファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult エクスポート
    - news_collector.py      — RSS 収集
    - calendar_management.py — 市場カレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 特徴量探索・IC・forward returns

その他、戦略（strategy）、実行（execution）、監視（monitoring）関連のパッケージは将来的に公開する想定です（__all__ に含まれます）。

---

## ライセンス / 貢献

- 本リポジトリのライセンスや貢献ルールはプロジェクトのルートにある LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

この README はコードベースの主要な使い方と運用上の注意点をまとめたものです。具体的な運用フロー（本番発注、ポジション管理、リスク制御）については本 README の範囲を超えるため、個別ドキュメントや設計書を参照してください。必要であればサンプルの運用スクリプト例や CI/CD、監視設定のテンプレートも作成します。必要なものがあれば教えてください。