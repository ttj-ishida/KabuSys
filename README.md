# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター算出 → AIベースのニュース解析 → 監査ログ／発注追跡 といったワークフローをサポートします。

主な対象
- データ取得（J-Quants）と DuckDB への保存
- ニュース収集・前処理・LLM によるセンチメント付与
- 市場レジーム判定（MA と マクロセンチメントの合成）
- ファクター算出（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートの検出）
  - 必須変数チェック経由の安全な取得 API（kabusys.config.settings）
- データ取得（J-Quants）
  - 株価日足、財務データ、上場情報、JPX カレンダーの取得（jquants_client）
  - レート制御・リトライ・401 自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 実行結果を ETLResult で返却
- データ品質チェック
  - 欠損（OHLC）検出、重複、スパイク（前日比閾値）、日付不整合チェック
  - QualityIssue によるサマリとログ出力
- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策、トラッキング除去、gzip ハンドリング）
  - 記事IDを正規化 URL の SHA-256 で生成して冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、ai_scores テーブルへ書き込み（score_news）
  - レート・リトライ・レスポンス検証（JSON mode に基づく）
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロセンチメント（30%）を合成して daily レジームを算出（bull/neutral/bear）
  - OpenAI を使ったマクロセンチメント評価（フェイルセーフで 0 にフォールバック）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルとインデックスを初期化するユーティリティ
  - init_audit_db で専用 DuckDB を初期化可能
- 研究用ユーティリティ（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（スピアマン）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats）

---

## 必要条件

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

pip インストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"  # setuptools/pyproject に依存する場合の仮想的な例
# または最低限:
pip install duckdb openai defusedxml
```

注: 上記はプロジェクト配布方法により変わります。pyproject / requirements.txt があればそちらを使用してください。

---

## 環境変数（主なもの）

以下は主に使われる環境変数の例です。プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（有効化のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能）。

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注周りに使用）

任意（デフォルトあり / 通常は設定しておく）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（default: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に使用）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化（テスト用）

.env 例（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=yourpass
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env の読み込みルール
- 優先度: OS 環境 > .env.local > .env
- .env.local は .env を上書き（override=True）
- OS の既存キーは protected として上書きされません

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   # 任意: 開発用の追加ライブラリをインストール
   ```

3. `.env` を作成（プロジェクトルート）
   - .env.example があればそれを参考にしてください（存在しない場合は上記の必須キーを設定）

4. DuckDB 初期化（監査ログ用 DB など）
   Python REPL で:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # あるいは settings.duckdb_path を使う:
   from kabusys.config import settings
   conn = init_audit_db(str(settings.duckdb_path))
   ```

---

## 使い方（代表的な呼び出し例）

以下はパッケージ内の主要関数を呼ぶ簡単な例です。実運用ではログ設定や例外処理を追加してください。

- ETL（日次パイプライン）実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
print("written:", written)
```

- 市場レジーム判定（OpenAI 必要）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別DBで管理する場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- 研究用ユーティリティ（ファクター算出・IC 計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
# conn は duckdb 接続、target_date は date オブジェクト
```

---

## 主要な API / モジュール一覧（要約・ディレクトリ構成）

- kabusys/
  - __init__.py
  - config.py
    - Settings（環境変数取得ユーティリティ）
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュース集約→OpenAIでスコア→ai_scoresに書込)
    - regime_detector.py (MA200 と マクロセンチメントの合成で market_regime に書込)
  - data/
    - __init__.py
    - calendar_management.py (営業日判定／カレンダー更新ジョブ)
    - pipeline.py (ETL 実行：run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl)
    - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
    - news_collector.py (RSS 取得・前処理・raw_news 保存)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize)
    - audit.py (監査ログ DDL / 初期化)
    - etl.py (ETLResult の再エクスポート)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)

（パッケージの public API は各 __init__.py を参照）

---

## 運用上の注意点・設計方針（抜粋）

- バックテスト／研究での Look-ahead bias 対策：target_date を明示的に渡し、内部で date.today() を参照しない実装箇所が多い。
- OpenAI 呼び出しはリトライ・タイムアウト処理あり。API 失敗時は安全側フォールバック（例: マクロセンチメント 0、スコア取得失敗はスキップ）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装。
- RSS 取得は SSRF・XML攻撃対策（スキーム検査・プライベートホストブロック・defusedxml）を実施。
- カレンダーが未取得でも曜日ベースでフォールバックするため、カレンダー未取得でも動作継続可能。

---

## トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行います。配布形式によっては自動ロードがスキップされることがあります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数をセットしてください。
- OpenAI/API の認証エラー
  - OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN が正しく設定されているか確認してください。jquants_client は 401 発生時に refresh_token から id_token を自動更新します。
- DuckDB に権限やパスの問題
  - settings.duckdb_path の parent ディレクトリが存在しないときは自動で作られますが、ファイルアクセス権限を確認してください。

---

必要であれば README に次の内容を追加できます:
- CI / テストの実行方法
- 詳細なデプロイ手順（systemd / コンテナ化）
- サンプル .env.example の完全版
- API スキーマ（DB テーブル定義の抜粋）

要望があれば追記します。