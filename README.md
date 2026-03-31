# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL、ニュース収集・NLP、AI によるニュースセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなど、実運用を意識したモジュール群を提供します。

主な設計方針
- Look-ahead バイアス対策（内部で date.today() / datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータプラットフォーム（冪等保存・トランザクションを考慮）
- 外部 API（J-Quants / OpenAI 等）はリトライ・レートリミット・フェイルセーフ実装
- テスト容易性を考慮した依存注入ポイント（API呼び出しの差し替え等）

---

## 機能一覧

- data (ETL / calendar / jquants_client / news_collector / quality / audit / stats)
  - J-Quants から株価・財務・マーケットカレンダーを取得・保存（差分取得、ページネーション対応、リトライ・レート管理）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - マーケットカレンダー管理・営業日判定ユーティリティ
  - ニュース RSS 収集（SSRF や XML 攻撃対策、トラッキング除去、ID 生成）
  - 監査ログテーブル定義と初期化（signal / order_request / executions の監査）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai (news_nlp / regime_detector)
  - ニュース記事をまとめて OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコア化（ai_scores テーブルへ保存）
  - マクロニュース + ETF(1321) の 200 日 MA 乖離から市場レジーム（bull/neutral/bear）をスコア化し market_regime に保存
  - API 呼び出しはリトライ・フォールバック（失敗時はセンチメント=0 等のフェイルセーフ）
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリー
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルートを .git または pyproject.toml から特定）
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

---

## セットアップ

前提
- Python 3.10+（typing | 型注釈の書き方より）
- DuckDB を利用するため適切な環境

推奨インストール（例）
```bash
# 開発環境としてパッケージを編集インストールする場合
pip install -e .

# または最小依存を個別にインストールする例
pip install duckdb openai defusedxml
```

（プロジェクト配布形態に応じて requirements.txt / pyproject.toml を用意してください）

環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=...       # J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD=...           # kabuステーション API パスワード（必須）
- KABU_API_BASE_URL=http://...    # kabuAPI のベース URL（省略時は http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN=...             # Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID=...            # Slack チャンネル ID（必須）
- DUCKDB_PATH=data/kabusys.duckdb  # DuckDB ファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db   # SQLite パス（監視用）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|... 
- OPENAI_API_KEY=...              # OpenAI API キー（AI モジュール利用時に必要）

自動読み込みについて
- パッケージはインポート時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動的に読み込みます。
- 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

基本的に DuckDB 接続を作成し、各モジュールの関数に接続と対象日を渡して使用します。

1) DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（ai_scores）を算出する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI APIキーは環境変数 OPENAI_API_KEY または引数 api_key に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

4) 市場レジーム判定を行う
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
# 戻り値は成功時 1。結果は market_regime テーブルに保存される
```

5) 監査ログ（audit）テーブルを初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成して監査スキーマを初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

6) 研究系（ファクター計算 / 正規化 / IC）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))

# 複数ファクターの Z スコア正規化
normalized = zscore_normalize(momentum, ["mom_1m","mom_3m","ma200_dev"])
```

補足
- OpenAI 呼び出しは内部でリトライや例外ハンドリングを行いますが、APIキーが設定されていない場合は ValueError が発生します。
- ETL / news の処理は外部 API へ多数回アクセスするため、ネットワークやキーの管理に注意してください。

---

## ディレクトリ構成

以下は主要なファイル / モジュールの階層（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / .env 読み込み・設定管理
    - ai/
      - __init__.py
      - news_nlp.py                # ニュースの LLM スコアリング（ai_scores へ書込み）
      - regime_detector.py         # ETF MA + マクロセンチメントから市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得・保存ロジック）
      - pipeline.py                # ETL パイプライン（run_daily_etl 等）
      - etl.py                     # ETLResult の再エクスポート
      - news_collector.py          # RSS 収集・前処理・raw_news 保存
      - calendar_management.py     # マーケットカレンダー・営業日ユーティリティ
      - quality.py                 # データ品質チェック
      - audit.py                   # 監査ログテーブル初期化 / init_audit_db
      - stats.py                   # zscore_normalize 等
    - research/
      - __init__.py
      - factor_research.py         # モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py     # 将来リターン / IC / 統計サマリー
    - research/ ... (他モジュール)
    - ai/ ... (上記)
- pyproject.toml / setup.cfg 等（プロジェクトルートを特定する用途で参照されます）

---

## 注意事項 / 運用ヒント

- 環境変数は .env / .env.local に保持できます。パッケージはプロジェクトルート検出により自動で読み込みます（ただしテスト時などで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください）。
- OpenAI / J-Quants の API 呼び出しはコスト／レートに注意して運用してください（モジュール内でレートリミット・リトライを実装していますが、実運用では追加のスロットリングが必要になる場合があります）。
- DuckDB テーブルスキーマは本リポジトリの DDL を参照してください（audit.init_audit_schema 等は冪等でテーブルを作成します）。
- テスト時は各モジュールの外部呼び出しポイント（OpenAI 呼び出しや _urlopen 等）をモック可能です。コード内に差し替えを想定した設計箇所があります。
- production 環境（live）では `KABUSYS_ENV=live` を設定し、実際の発注や Slack 通知など運用判断に基づく処理を行ってください。

---

必要であれば README に次の内容も追加できます：
- 依存関係の正確な一覧（requirements.txt / pyproject.toml から）
- データベースのスキーマ定義 / マイグレーション手順
- CI / テスト実行方法（ユニットテストの実行例、モックの利用例）
- 運用手順（ETL スケジューリング、監視・アラート）