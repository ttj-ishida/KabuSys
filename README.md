# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・AI支援市場判定・監査ログを備えた自動売買基盤のライブラリです。  
主に DuckDB をデータレイヤ、J-Quants API をデータソース、OpenAI をニュースのセンチメント評価に用いる設計になっています。

バージョン: 0.1.0

## 主な特徴（機能一覧）
- ETL（データ取得・保存・品質チェック）
  - J-Quants から株価（日足）・財務データ・マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション対応・レートリミット/リトライ実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と記事前処理、記事 → 銘柄紐付け
- ニュース NLP（OpenAI）による銘柄別センチメント評価（ai_scores テーブルへ書込）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化 等）
- マーケットカレンダー管理（営業日判定・next/prev trading day 等）
- 監査（audit）テーブル群の初期化と監査ログの管理（signal → order_request → executions のトレーサビリティ）
- J-Quants API クライアント（認証、取得、DuckDB への冪等保存）

## 必要な環境
- Python 3.10 以上（| 型注釈などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（プロジェクトに requirements.txt がある場合はそれを使用してください）

## セットアップ手順（ローカル開発向け）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実運用で Slack や追加機能を使う場合は適宜パッケージを追加してください（slack_sdk 等）。

3. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml のある階層）に `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   主要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須：ETL を実行する場合）
   - OPENAI_API_KEY — OpenAI を使う場合は API キー（news NLP / regime 判定）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注同期などがある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — 動作モード
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   .env のパースはシェル形式の export= や引用文字列、インラインコメントなどを考慮した実装になっています。

4. データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

## 基本的な使い方（コード例）
以下は主要 API の使い方例です。Python スクリプトや Jupyter などから呼び出して利用します。

- DuckDB 接続の作成（デフォルトパスを使用）
```
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI キーは環境変数 OPENAI_API_KEY または api_key 引数）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（1321 + マクロニュース）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（監査専用 DB を分けたい場合）
```
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別パス
```

- マーケットカレンダー関連ユーティリティ
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_open = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))
```

- 研究用ユーティリティ（ファクター計算等）
```
from kabusys.research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
```

注意:
- AI を呼び出す関数は OpenAI の API キー（OPENAI_API_KEY）を必要とします。api_key 引数で直接渡すことも可能です。
- DuckDB の変更はトランザクションで保護される箇所があります。関数の戻り値やログを確認してエラー処理を行ってください。

## 環境変数の自動読み込み仕様（簡単）
- 自動ロード順序: OS 環境変数 > .env.local > .env
- プロジェクトルートはこのファイル位置から親ディレクトリを遡り `.git` または `pyproject.toml` を検出して決定
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風の export 支持・クォート/エスケープ・インラインコメント取り扱い等を行います。

## 主要モジュールとディレクトリ構成
（プロジェクトの src/kabusys 配下の主なファイルと役割）

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に保存するロジック
    - regime_detector.py — ETF (1321) の MA とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証・取得・DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS からニュースを収集・前処理して raw_news に保存
    - calendar_management.py — マーケットカレンダー管理・営業日判定・更新ジョブ
    - quality.py — データ品質チェック群と QualityIssue 型
    - stats.py — Zスコア正規化などの統計ユーティリティ
    - audit.py — 監査ログテーブル DDL / 初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム・ボラティリティ・バリュー等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/regime_detector.py, ai/news_nlp.py — (上記) OpenAI 呼び出しはリトライとフォールバックを備える
  - その他: logging による詳細ログが豊富に入る設計

各モジュールは「ルックアヘッドバイアス防止」を念頭に設計されており、date.today()/datetime.today() を不用意に参照しないよう配慮されています（ETL/研究処理は target_date を明示的に受け取る形）。

## 運用上の注意
- OpenAI / J-Quants の API キーは外部サービスの利用料やレート制限に注意して管理してください。
- news_nlp / regime_detector の呼び出しは API コストがかかります。バッチ化とレート管理を検討してください。
- DuckDB ファイルのバックアップや監査ログの保持方針を運用で定めてください。
- データ品質チェックは ETL 後に実行され、重大な問題は結果の has_quality_errors フラグ等で検出できます。運用フローに組み込んでください。

---

追加で README へ記載したい情報（インストール用の requirements.txt、CI 実行方法、例の設定ファイル .env.example、開発フローや API キーの取り扱いガイド等）があれば教えてください。必要に応じて追記して詳細なセットアップ手順や運用ガイドを作成します。