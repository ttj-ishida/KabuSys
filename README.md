# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群を集めたパッケージです。  
主に以下を目的とします。

- J-Quants API からのデータ取得（OHLCV / 財務 / 上場情報 / マーケットカレンダー）
- DuckDB を使った差分 ETL パイプライン（品質チェック付き）
- ニュースの収集・NLP（OpenAI を用いたセンチメント判定）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査（audit）テーブルの初期化・管理（発注 → 約定のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理（.env 自動読み込み / Settings オブジェクト）
- J-Quants クライアント（rate limit・リトライ・トークン自動リフレッシュ対応）
- ETL（prices / financials / calendar）の差分更新と品質チェック
- ニュース収集（RSS、SSRF対策、トラッキングパラメータ除去、前処理）
- OpenAI を用いたニュースセンチメント分析（gpt-4o-mini、JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + LLM マクロセンチメント）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal_events / order_requests / executions）のスキーマ作成・初期化
- カレンダー管理（営業日判定・next/prev_trading_day、夜間バッチ更新ジョブ）

---

## 要件

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリと併用）

プロジェクトの依存は setup / pyproject.toml / requirements.txt によります。上記パッケージは最低限必要になります。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてチェックアウト
   - git clone ...  
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクトが提供する requirements / pyproject の指示に従ってください
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在する場所）に `.env` を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須環境変数（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（OpenAI キーは AI モジュールを使う際に `OPENAI_API_KEY` を環境変数で設定するか、該当関数の `api_key` 引数で渡してください。）

---

## 使い方（基本例）

以下はパッケージ API を利用する際のスニペット例です。実行はプロジェクトルートから行ってください。

1) 設定・DB 接続
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path (Path) を使って接続
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメントのスコア付け（OpenAI）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（MA200 + マクロセンチメント）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)
# これで signal_events / order_requests / executions のスキーマが作成されます
```

6) カレンダー・営業日判定（ユーティリティ）
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI モジュール（news_nlp, regime_detector）は OpenAI の API を呼びます。API キーの管理と利用料に注意してください。
- 各関数は Look-ahead bias を避ける設計になっており、内部で date.today() を勝手に参照しないものが多いです。バックテスト等で使用する場合は target_date を明示してください。
- Settings は一部の環境変数を必須とします。未設定だと ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なモジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py (score_news を再エクスポート)
    - news_nlp.py
      - ニュースの集約・OpenAI へのバッチ送信・レスポンス検証・ai_scores 書込
    - regime_detector.py
      - 1321 (ETF) の MA200 乖離とマクロセンチメントを合成し market_regime に書き込み
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar 管理、営業日判定・next/prev/get_trading_days、calendar_update_job
    - pipeline.py
      - 日次 ETL パイプライン（prices / financials / calendar）と ETLResult クラス
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / token管理 / rate limit / retry）
    - news_collector.py
      - RSS フィード取得・前処理・raw_news 書き込み（SSRF 対策・gzip 制限等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ用テーブル DDL と初期化関数（init_audit_schema / init_audit_db）
    - etl.py
      - pipeline.ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

各ファイル内には関数・クラスの docstring が充実しており、処理フローや設計方針が記載されています。

---

## 挙動・運用上のメモ

- .env 自動ロード:
  - プロジェクトルートはこのファイル内で __file__ を基点に .git または pyproject.toml を探して決定します。CWD に依存しません。
  - 読み込み順: OS 環境 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants クライアントは内部で固定間隔レートリミッタを使い 120 req/min を守るように実装されています。
- OpenAI 呼び出しはリトライ・バックオフを備えていますが、API 利用料やレート制限には注意してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンの互換性に配慮した実装が行われています。
- 監査テーブルは削除を想定しておらず、トレーサビリティのためにレコードは保持する設計です。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - settings の必須キー（例: JQUANTS_REFRESH_TOKEN）を .env に設定するか環境変数として渡してください。
- OpenAI 関連エラー
  - OPENAI_API_KEY を環境変数に設定するか関数に `api_key` を渡してください。また API レートやモデル指定（gpt-4o-mini）に注意。
- ネットワーク / 429 等の一時エラー
  - 多くのクライアントは内部でリトライしますが、継続的に失敗する場合は API キーやネットワーク/プロキシ設定を確認してください。

---

必要であれば README に「例: .env.example」のテンプレートや CI / デプロイ手順、より詳しいモジュール毎の使い方（関数引数の説明や返り値）を追加できます。どの情報を優先して追記するか教えてください。