# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI でのセンチメント）、ファクター計算、監査ログ（約定トレース）、市場レジーム判定など、アルゴリズムトレードに必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（duckdb）
  - 差分更新・バックフィル・ページネーション・リトライ・レートリミット制御
- ニュース処理
  - RSS フィードからのニュース収集（SSRF/サイズ制限対策、トラッキング除去）
  - raw_news と銘柄紐付け（news_symbols）
- ニュース NLP / AI スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（score_news）
  - マクロニュース + ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（score_regime）
  - 冪等処理・バッチ処理・リトライ・レスポンス検証を備えた堅牢実装
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）・ランク化・Zスコア正規化
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合などのチェック機能
- 監査ログ（オーダー・約定トレーサビリティ）
  - signal_events / order_requests / executions テーブルや索引を初期化するツール
  - order_request_id を冪等キーとして二重発注を防止
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config.settings）
  - 実行環境（development / paper_trading / live）やログレベル管理

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションで | を使用するため）を推奨
- インターネット接続（J-Quants / OpenAI への API アクセス）

1. リポジトリをチェックアウトまたはコピー

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低依存例（ローカルで開発する場合）:
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを利用してください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env`／`.env.local` を配置すると自動で読み込まれます（モジュール import 時に自動ロード）。
   - 自動ロードを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須環境変数（最小セット）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL 用）
- KABU_API_PASSWORD: kabuステーション等の発注 API パスワード（発注層を使う場合）

OpenAI 関連
- OPENAI_API_KEY: OpenAI API キー（news_nlp.score_news / regime_detector.score_regime を使う場合）

任意 / 通知系
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）

DB パス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

システム設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

---

## 使い方（主要な API/コマンド例）

以下は Python から使う基本例です。事前に依存ライブラリと .env を設定しておいてください。

1) DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL（データ取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（OpenAI を使う）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

4) 市場レジーム計算
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# momentum は dict のリスト（各銘柄のファクター）
```

6) 監査ログ DB 初期化（別ファイルで監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作られる
```

注意点:
- OpenAI 呼び出しは API レートや料金に注意してください。テスト時は各モジュールの _call_openai_api を mock できます。
- J-Quants API 呼び出しには rate-limit とリトライが組み込まれていますが、API 資格情報が正しいことを確認してください。
- 関数群は「ルックアヘッドバイアス」を避ける設計思想（target_date に対して過去データのみを参照）で実装されています。バックテストで利用する際も同様の注意を払ってください。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): ニュースの銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): 市場レジームを market_regime に書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save 系関数）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存ロジック
    - calendar_management.py
      - market_calendar の管理、営業日判定など
    - stats.py
      - zscore_normalize 等の汎用統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化関数
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (パッケージ用意済みとして __all__ に含むが実装ファイルはここ以外のコードベースに依存する場合あり)
  - strategy/, execution/（高レベルの戦略・発注層を想定したパッケージプレースホルダ）

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for 発注): kabu API のパスワード
- OPENAI_API_KEY (必要時): OpenAI API キー
- DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（既定: development）
- LOG_LEVEL: ログレベル（INFO など）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 = .env 自動ロードを無効化

.env.example を作成してプロジェクトルートに置くのが推奨です。

---

## トラブルシューティング & 注意事項

- 環境変数が足りないと Settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN 未設定）。
- OpenAI API 呼び出しで JSON パースに失敗した場合、スコアはフェイルセーフで 0.0 にフォールバックする設計の部分があります（ログに警告が出ます）。
- DuckDB のバージョン差異により executemany の空リスト渡しが問題になるため、コード中で空チェックが行われています。DB エラーが出る場合はログを参照して下さい。
- news_collector は SSRF 対策・レスポンスサイズ制限を行います。RSS フィード URL に対して正しいスキーム（http/https）と到達可能性を確認してください。
- 当ライブラリは本番口座（is_live）とペーパー（is_paper）を区別する設定があるため、実アクション（発注）を有効にする際は環境設定を必ず確認してください。

---

## 開発・テストについて

- 各 AI 呼び出し部（news_nlp._call_openai_api / regime_detector._call_openai_api）は単体テスト時にモック差し替え可能なように作られています。外部 API 呼び出しを直接行いたくないテストではモックしてください。
- ETL ロジックや品質チェックは DuckDB 接続を注入して分離テスト可能です。

---

この README は主要機能・使い方の概要を示しています。詳細はソースコード内の docstring（各モジュール・関数の説明）を参照してください。さらに具体的な使い方（バックテスト統合、実際の発注フロー等）が必要であれば、そのユースケースに合わせたサンプルや手順を追加で作成します。