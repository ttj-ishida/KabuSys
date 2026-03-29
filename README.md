# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュースセンチメント評価、監査ログ等を備えた自動売買支援ライブラリです。本リポジトリは主に以下の用途を想定しています：データ取得（J-Quants）、データ品質チェック、特徴量計算、ニュース NLP（OpenAI）によるスコアリング、マーケットレジーム判定、監査ログ管理。

以下はこのコードベースの概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

注意：この README はコードベース（src/kabusys）に基づいたドキュメントです。実際に本番で売買を行うコードは含まれていないか、別モジュールで管理されることを想定しています。実際の発注処理を行う前に十分なレビューと安全対策を行ってください。

## プロジェクト概要
- データ取得（J-Quants API）および DuckDB への永続化（冪等保存）。
- ニュース収集（RSS）と前処理、銘柄と記事の紐付け。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントおよびマクロセンチメント評価（JSON Mode を活用）。
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索（将来リターン、IC 等）。
- データ品質チェック（欠損・重複・スパイク・日付整合性）。
- マーケットカレンダー管理（JPX カレンダー取得・営業日判定）。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ & 初期化ユーティリティ。
- 環境変数管理（.env 自動読み込み、必須項目の検証）。

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch / save の実装、トークン自動リフレッシュ、レートリミット対応）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 防止、前処理）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - データ品質チェック（missing/duplicates/spike/date consistency）
  - 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 記事群を集約して OpenAI に投げ、ai_scores に書き込む）
  - レジーム判定（score_regime: ETF 1321 の MA とマクロセンチメントを合成して市場レジーム判定）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数の読み込み（プロジェクトルートの .env, .env.local 自動ロード）と必須項目のチェック

## 必要条件 / 推奨環境
- Python 3.10 以上（PEP 604 の union 型表記 (A | B) を使用しているため）
- 推奨パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加パッケージは pyproject.toml / requirements.txt を参照してください）

例（仮）:
pip install duckdb openai defusedxml

※ 実際のプロジェクトでは pyproject.toml / requirements.txt に記載の依存関係を使用してください。

## 環境変数
config.Settings で参照される主要な環境変数（必須・任意）:

必須（少なくともテストや ETL を実行するために設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行時）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合
- KABU_API_PASSWORD — kabu API を使う場合のパスワード

任意 / デフォルトあり
- KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"
- KABUSYS_ENV — 開発環境指定（development / paper_trading / live）。デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト INFO

OpenAI API（ニュース NLP 等）:
- OPENAI_API_KEY — score_news / score_regime が参照。関数呼び出し時に api_key 引数でも指定可能。

.env 自動ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を含む）から .env と .env.local を自動ロードします。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env (簡易)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
KABU_API_PASSWORD=your_kabu_password

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -e .     （プロジェクトが pyproject.toml を含む場合）
   - あるいは個別に: pip install duckdb openai defusedxml
4. .env を作成して必要な環境変数を設定（上記参照）
5. DuckDB 用のデータディレクトリ作成（必要なら）
   - mkdir -p data

補足:
- テスト時に .env 自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しを単体テストでモックするユーティリティがコード内に想定されています（関数単位で _call_openai_api をモック可能）。

## 使い方（代表的な例）
以下は主要機能を呼び出す最小例です。実行には適切な環境変数と DuckDB データベース（スキーマ）が必要です。

- DuckDB 接続の作成（設定されたパスを使う例）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次）を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しなければ今日 (date.today()) が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

- 監査 DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査ログを書けるようになります
```

注意:
- OpenAI API 呼び出しは外部 API を叩きます。テストでは score_news や regime_detector 内の _call_openai_api をモックして API 呼び出しを回避してください。
- ETL や保存関数は DuckDB のスキーマを前提としています。スキーマ作成・初期化は別のモジュール（data.schema 等）で行う想定です。

## よくあるトラブルと対処
- ValueError: 環境変数 'X' が設定されていません。
  - settings が必須とする環境変数が未設定です。.env を用意するか、環境変数を設定してください。
- OpenAI 関連の失敗
  - OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。テスト時は API コールをモックしてください。
- J-Quants API の認証失敗（401）
  - JQUANTS_REFRESH_TOKEN が正しいか確認してください。モジュールは 401 時にリフレッシュを試みます。
- DuckDB の executemany で空リストのエラー
  - 一部の関数は空パラメータで executemany を呼ばないようガードしていますが、独自コードで executemany を呼ぶ際は空リストを渡さないでください。

## ディレクトリ構成（抜粋）
以下は src/kabusys 配下の主要ファイル・モジュールの一覧（提供されたコードベースに基づく抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py (ETLResult エクスポート)
      - etl.py (ETL インターフェース)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py exports...
    - (その他) strategy/, execution/, monitoring/ はパッケージ公開対象として __all__ に含まれていますが、本断片では詳細実装がありません（別ディレクトリに存在する可能性があります）。

各モジュールはドメインごとに整理されており、DuckDB 接続（duckdb.DuckDBPyConnection）を引数として受け取る関数が多く、外部アクセスを隔離した設計になっています（Look-ahead bias 回避の配慮も多数あり）。

## 開発・貢献
- テストを書く際は OpenAI / ネットワーク呼び出しをモックしてください（score_news._call_openai_api 等）。
- .env 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 新たな ETL ジョブやスキーマ変更時はデータ品質チェック（quality.py）に適切なテストを追加してください。

---

必要であれば README に含める追加情報（例: pyproject.toml に基づくインストール手順、CI / テスト実行コマンド、スキーマ定義ファイルの参照方法等）を追記します。どの情報を追加したいか教えてください。