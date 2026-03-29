# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants）、ニュース収集、AIによるニュースセンチメント解析、ファクター計算、取引監査ログなど、運用に必要なコンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような用途を想定した Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ベースのニュース収集（SSRF/サイズ制限等の安全対策を実装）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄別センチメント）と市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- 取引フローの監査テーブル（signal → order_request → execution のトレーサビリティ）

設計上の特徴：
- Look-ahead バイアスを避けるため datetime.today() を直接参照しない設計
- DuckDB を中心としたオンプレミス／ファイルベースのデータ管理
- API 呼び出しに対するリトライ／バックオフ、フェイルセーフ（API失敗時はスコアを 0 にフォールバック等）
- 冪等保存（ON CONFLICT / DO UPDATE）を多用

---

## 主な機能一覧

- ETL / pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants からの差分取得、保存（save_*）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks
- ニュース収集
  - fetch_rss / preprocess_text / ニュースの正規化と raw_news への保存（news_collector）
- AI（OpenAI）
  - score_news（銘柄別ニュースセンチメントを ai_scores に保存）
  - score_regime（ETF 1321 の MA とマクロニュースを合成して market_regime を生成）
- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- データユーティリティ
  - market_calendar 管理 / is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - jquants_client：API クライアント（認証・ページネーション・レートリミット対応）
- 監査ログ
  - init_audit_schema / init_audit_db（監査テーブルの初期化と専用 DB 作成）

---

## 動作環境・前提

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス：J-Quants API、RSS ソース、OpenAI 等に接続可能であること

（プロジェクト配布時に requirements.txt / pyproject.toml で依存関係を管理してください）

---

## 環境変数 / 設定

KabuSys は .env ファイルおよび環境変数から設定を読み込みます（自動ロード機能あり）。
プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` を自動で読みます。

主要な環境変数（必須またはデフォルト）：

- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD  
  - kabuステーション API パスワード（必須）
- KABU_API_BASE_URL  
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN  
  - Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID  
  - Slack 通知先チャネル ID（必須）
- OPENAI_API_KEY  
  - OpenAI を利用する場合に必要（score_news / score_regime など）
- DUCKDB_PATH  
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH  
  - 監視用途の sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV  
  - 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL  
  - ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）

自動環境読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

例（.env の最低例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   ※ プロジェクトで pyproject.toml / requirements.txt がある場合はそちらを利用してください。
   - pip install -e .    （パッケージとしてインストールする場合）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください（上記参照）。

5. DuckDB データベース（初期化）
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - またはコードから自動的にテーブル作成を呼び出すことができます。

---

## 使い方（主要な呼び出し例）

以下はライブラリの主要機能を呼ぶ最小例です。実運用時はエラーハンドリング・ログ設定・認証トークン管理を適切に実装してください。

1) DuckDB 接続を作成して ETL を実行（1日分）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

3) 市場レジーム判定を実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

注意:
- score_news / score_regime の OpenAI 呼び出しは API 料金とレイテンシが発生します。API キーは OPENAI_API_KEY で設定できます（関数引数で上書き可能）。
- テスト時はモジュール内の _call_openai_api をパッチしてモックできます（ユニットテスト向けに設計されています）。

---

## ディレクトリ構成（概要）

リポジトリは src/kabusys 下に主要コンポーネントを配置しています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定の読み込みロジック（.env 自動ロード）
  - ai/
    - news_nlp.py         : ニュースセンチメントのスコアリング（score_news）
    - regime_detector.py  : 市場レジーム判定（score_regime）
  - data/
    - jquants_client.py   : J-Quants API クライアント（fetch / save 等）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - news_collector.py   : RSS ニュース収集と正規化
    - quality.py          : データ品質チェック（check_*）
    - stats.py            : 共通統計ユーティリティ（zscore_normalize）
    - audit.py            : 監査ログ / スキーマ初期化
    - etl.py              : ETLResult の再エクスポート
  - research/
    - factor_research.py  : モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - research/__init__.py（便宜的に関数を再エクスポート）
  - ai/__init__.py

各モジュールはドキュメンテーション文字列と明確な設計方針が付与されています。詳しい実装は各ファイルの docstring を参照してください。

---

## 運用上の注意点

- API キーの取り扱い：OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等は安全に管理してください（CI/CD シークレット管理を推奨）。
- 自動環境読み込み：テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。
- DuckDB の executemany は空リストを受け付けないバージョン制約があるため、呼び出し側は空リストをチェックする必要があります（実装で考慮済み）。
- ニュース取得は SSRF 対策・レスポンスサイズ制限等の安全策を実装していますが、運用時にはフィード先の信頼性を監査してください。
- OpenAI 呼び出しはリトライ・フェイルセーフ実装がありますが、API レートやコスト管理が必要です。

---

## テストとモック

- OpenAI 呼び出しやネットワークアクセス部分はモジュール内で分離されており、ユニットテスト時は _call_openai_api / _urlopen 等を mock.patch で差し替えてテスト可能です。
- DuckDB 接続は ":memory:" を指定してインメモリ DB でテストできます。

---

## ライセンス / 貢献

- この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。
- 貢献する場合は PR と簡単な説明（変更点、テスト方法）を添えてください。

---

質問や追加してほしいサンプル（CI 設定例、requirements.txt、.env.example の自動生成スクリプト等）があれば教えてください。README を用途に合わせて拡張します。