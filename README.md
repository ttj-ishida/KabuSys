# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。

このリポジトリは、J-Quants / kabuステーション 等からのデータ ETL、ニュース収集・NLP による銘柄スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）や市場レジーム判定までを含む内部ライブラリ群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に格納する ETL パイプライン
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントのバッチスコアリング
- 市場レジーム（bull/neutral/bear）判定（ETF とマクロニュースの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化

設計上の特徴：
- Look-ahead bias 回避（内部処理で datetime.today()/date.today() を不用意に参照しない設計）
- DuckDB を中心としたローカル永続化
- API リクエストのレート制御とリトライ（J-Quants, OpenAI）
- 冪等性を重視した DB 保存ロジック（ON CONFLICT / DELETE→INSERT の置換など）
- フェイルセーフ（API障害時に処理継続する設計、重要箇所はログ出力）

---

## 主な機能一覧

- データ取得 / ETL
  - daily prices（raw_prices）取得・保存（J-Quants）
  - financial statements（raw_financials）取得・保存
  - market calendar（market_calendar）取得・保存
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付整合性チェック（run_all_checks）

- ニュース処理 / AI
  - RSS 取得・前処理（news_collector.fetch_rss / preprocess_text）
  - ニュースを銘柄ごとに集約して OpenAI に投げるスコアリング（ai.news_nlp.score_news）
  - マクロニュース + ETF(1321) の MA 乖離合成による市場レジーム判定（ai.regime_detector.score_regime）

- 研究用モジュール（research）
  - calc_momentum / calc_value / calc_volatility
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- 監査ログ（audit）
  - 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - signal / order_request / executions の DDL とインデックス定義

- J-Quants クライアント（data.jquants_client）
  - 認証（get_id_token）、取得（fetch_*）と DuckDB への保存（save_*）
  - レートリミット管理とリトライ実装

---

## 前提・依存関係

必須（概略）：
- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime など）

インストール例（最小）：
pip install duckdb openai defusedxml

実際のプロジェクト配布では requirements.txt / pyproject.toml を利用してください。

---

## 環境変数と設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数：

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API のパスワード
  - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- OpenAI / ニュース NLP
  - OPENAI_API_KEY — ai.news_nlp / ai.regime_detector で使用
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースのパス（任意）
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視用 DB（デフォルト: data/monitoring.db）
- 監視関連
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1/0)
- 実行環境 / ログ
  - KABUSYS_ENV — 値: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化

例（.env の雛形）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-xxxx...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意: トークンやパスワードは漏洩しないよう取り扱ってください。

---

## セットアップ手順

1. リポジトリをクローンする

   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # mac/linux
   .venv\Scripts\activate     # Windows

3. 依存関係をインストール

   pip install -r requirements.txt
   または最小:
   pip install duckdb openai defusedxml

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、上記の必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定します。
   - テストやローカル用に `.env.local` を使うことも可能（読み込み順は OS 環境 > .env.local > .env）。

5. DuckDB データベースの準備（任意）
   - デフォルトパスは data/kabusys.duckdb（settings.duckdb_path で変更可）。
   - 監査用 DB を別途初期化する場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は Python インタープリタやスクリプトからライブラリを使うサンプルです。

- 日次 ETL の実行（DuckDB 接続を渡す）:
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（特定日）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```
api_key を省略すると環境変数 OPENAI_API_KEY が使用されます。未設定だと ValueError。

- 市場レジーム判定:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算:
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に受け取ります。ETL / スコアリング関数は内部でトランザクション管理を行いますが、必要に応じて外部で接続を明示的に管理してください。

---

## ディレクトリ構成（主要ファイル）

```
src/kabusys/
├─ __init__.py              (パッケージ定義・バージョン)
├─ config.py                (環境変数・設定管理)
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py           (ニュースセンチメントスコアリング)
│  └─ regime_detector.py    (市場レジーム判定)
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py     (J-Quants API クライアント + 保存関数)
│  ├─ pipeline.py           (ETL パイプラインと run_daily_etl)
│  ├─ etl.py                (ETLResult の再エクスポート)
│  ├─ calendar_management.py (市場カレンダー管理・営業日判定)
│  ├─ news_collector.py     (RSS 収集・前処理)
│  ├─ quality.py            (データ品質チェック)
│  ├─ stats.py              (統計ユーティリティ / zscore 正規化)
│  └─ audit.py              (監査テーブル定義・初期化)
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py    (momentum/value/volatility 等)
│  └─ feature_exploration.py (forward returns / IC / factor summary / rank)
└─ ai/                      (上記)
```

各モジュールの目的はファイル先頭の docstring に詳細が記載されています。まずは `kabusys.data.pipeline.run_daily_etl` と `kabusys.ai.news_nlp.score_news` を実行して動作を確認するのが分かりやすい入り口です。

---

## 運用上の注意・ベストプラクティス

- 機密情報（API トークン等）は `.env` や CI のシークレットマネージャで安全に保管してください。
- OpenAI / J-Quants の API 呼び出しは課金・レート制限の対象です。大量バッチ処理では注意して運用してください。
- 本ライブラリはデータ品質チェックを提供しますが、ETL の自動停止や通知の実装は利用側で行ってください（quality.run_all_checks の結果を参照）。
- DuckDB は単一ファイル DB のため、複数プロセスで同時更新する運用には注意が必要です（運用設計を検討してください）。
- テスト時は環境自動読み込みを無効にするため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

---

## 貢献・拡張

- 追加したい機能
  - kabu ステーションへの実際の発注実装（execution モジュール）
  - モデル管理 / 戦略実行の CLI / supervisor
  - UI / ダッシュボード（監視・監査ログ可視化）

プルリクエスト・Issue を歓迎します。コードスタイル・テストカバレッジを維持してください。

---

必要であれば README に実際の requirements.txt、例となる .env.example、簡単な CI 設定やデモスクリプトの追加も作成します。どの内容を優先して追加しますか？