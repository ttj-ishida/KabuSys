# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集と AI によるニュースセンチメント、研究用ファクター計算、監査ログなどを備え、バックテスト／本番のデータ基盤・研究環境を支援します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ収集（ETL）
  - J-Quants API から株価日足、財務データ、JPXマーケットカレンダーを差分取得・保存
  - 差分更新、バックフィル、ページネーション対応、レートリミット・リトライ実装

- データ品質管理
  - 欠損、重複、スパイク、日付不整合などの自動チェック（quality モジュール）

- ニュース収集
  - RSS から記事を取得し前処理して raw_news に冪等保存
  - SSRF / Gzip / XML インジェクション対策あり

- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル初期化・運用ヘルパー（audit）

- DuckDB を主データストアとして利用（デフォルト経路: data/kabusys.duckdb）

---

## 前提・依存関係

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（必須／任意）

必須（利用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD : kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（通知連携がある場合）
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意・デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化
- OPENAI_API_KEY : OpenAI 呼び出し時に利用（score_news / score_regime に引数で渡すことも可能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

自動で .env / .env.local をプロジェクトルートから読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと無効化可能）。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements または pyproject があればそちらを使用）
4. .env を作成
   - プロジェクトルートに .env または .env.local を配置して必要な環境変数を設定
5. DuckDB データベース用ディレクトリを作成（自動で作られますが確認）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの利用例です。すべての API は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- DuckDB 接続を作成する例:
from pathlib import Path
import duckdb
conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL を実行する（run_daily_etl）:
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む:
from datetime import date
from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用

- 市場レジームをスコアリングする:
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算:
from datetime import date
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

- 監査ログスキーマを初期化する（監査用 DB を分けて作る例）:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

注意事項:
- score_news / score_regime は OpenAI API を呼び出します。APIキーは引数か環境変数 OPENAI_API_KEY を指定してください。
- ETL / API 呼び出しはネットワーク・認証トークンを必要とします。J-Quants トークン設定を忘れないでください。
- duckdb.executemany に空リストを渡すことができないバージョンの挙動に配慮した実装になっています。

---

## よく使う関数・モジュール一覧

- kabusys.config.settings : 環境設定とデフォルト値（DUCKDB_PATH 等）
- kabusys.data.pipeline : run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
- kabusys.data.jquants_client : J-Quants との HTTP クライアントと save_* / fetch_* 関数
- kabusys.data.news_collector : RSS 取得・前処理
- kabusys.data.quality : データ品質チェック（run_all_checks）
- kabusys.data.calendar_management : 営業日判定・カレンダー更新ジョブ
- kabusys.data.audit : 監査ログテーブル初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp : score_news（銘柄単位ニュースセンチメント）
- kabusys.ai.regime_detector : score_regime（市場レジーム判定）
- kabusys.research.* : ファクター計算や特徴量解析ユーティリティ

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                    # 環境変数と設定の管理
- ai/
  - __init__.py
  - news_nlp.py                 # ニュースの NLP スコアリング
  - regime_detector.py          # マクロ + MA200 を用いた市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py      # 市場カレンダー管理とユーティリティ
  - etl.py                      # ETL の公開インターフェース
  - pipeline.py                 # ETL 本体（run_daily_etl 等）
  - stats.py                    # 統計ユーティリティ（z-score など）
  - quality.py                  # データ品質チェック群
  - audit.py                    # 監査ログスキーマ初期化 / DB 初期化
  - jquants_client.py           # J-Quants API クライアントと保存ロジック
  - news_collector.py           # RSS 取得と前処理
- research/
  - __init__.py
  - factor_research.py          # Momentum / Volatility / Value の計算
  - feature_exploration.py      # 将来リターン / IC / 統計サマリー 等

ドキュメントや設計（Design/MD）を参照することで、より詳細な処理フローや設計方針が確認できます（コード内 docstring にも各処理の設計方針と注意点が記載されています）。

---

## テスト・デバッグに関するヒント

- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで明示的に環境をセットしたい場合に便利）。
- OpenAI 呼び出しやネットワーク依存処理はモジュール内の private 関数（_call_openai_api など）をモックすることでテストしやすく設計されています。
- DuckDB は軽量で :memory: による単体テストの利用が可能です（init_audit_db(":memory:") 等）。
- ログレベルは LOG_LEVEL で変更できます。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

---

## ライセンス・貢献

この README はコードベースの概要と主要な使い方を説明するためのドキュメントです。プロジェクトのライセンスや貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING 等のファイルを参照してください。

---

必要であれば、README に追加する以下の内容を作成します:
- セットアップ用の具体的な requirements.txt / pyproject.toml の例
- よくあるエラーとトラブルシュート集
- より詳細な関数使用例（スクリプトテンプレート）