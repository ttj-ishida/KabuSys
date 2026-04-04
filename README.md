# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
主に以下の目的を持つモジュール群を含みます: データ ETL（J-Quants）、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算・特徴量解析）、監査ログ／発注トラッキング、マーケットカレンダー管理など。

---

## 主な機能

- データ収集（J-Quants）
  - 日次株価（OHLCV）取得／保存（差分取得・ページネーション対応・レート制御・リトライ）
  - 財務諸表（四半期データ）取得／保存
  - JPX マーケットカレンダー取得／保存
- ETL パイプライン
  - 差分取得、保存、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- ニュース収集
  - RSS 収集、安全対策（SSRF ブロック、応答サイズ制限）、テキスト前処理
  - raw_news / news_symbols テーブルへの冪等保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント生成（gpt-4o-mini / JSON mode）
  - マクロニュースから市場レジーム判定（regime_detector）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマと初期化関数（init_audit_schema / init_audit_db）
  - 発注・約定のトレーサビリティを UUID 階層で保持
- 設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 環境変数で各種 API キー / パス / 監視閾値を設定可能

---

## 動作要件（目安）

- Python 3.10+
  - 型ヒントに Python 3.10 の union 型（|）が使用されています
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - 標準ライブラリ（urllib, json, logging, datetime 等）

実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン（またはプロジェクトディレクトリへ移動）

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements / pyproject があればそちらを使用）

4. 環境変数の用意
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env に最低限設定する例:
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
OPENAI_API_KEY=あなたの_openai_api_key
KABU_API_PASSWORD=（kabu API を使う場合）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

設定項目（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（NLP / レジーム判定で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（実取引連携時）
- DUCKDB_PATH: データ保管用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- KABUSYS_ENV: development / paper_trading / live
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

## 使い方（コード例）

以下は簡単な実行例です。実際の運用ではログ設定や例外処理を適宜追加してください。

- DuckDB に接続して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env の DUCKDB_PATH を参照
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp.score_news）を実行する例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）を実行する例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

注意:
- OpenAI 呼び出しは API キーが必須です。api_key を明示的に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- テストでは OpenAI クライアント呼び出しをモックすることが想定されています（モジュール内で _call_openai_api を差し替え可能）。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（.env 自動読み込み、必須値検査）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの LLM センチメント解析および ai_scores への書き込み
    - regime_detector.py
      - マクロセンチメントと ETF 200 日 MA 乖離から市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、データ取得、DuckDB 保存関数）
    - pipeline.py
      - ETL パイプラインの本体（run_daily_etl など）
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - JPX カレンダー管理・営業日判定・calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付不整合）
    - audit.py
      - 監査テーブル定義・初期化（signal_events / order_requests / executions）
    - news_collector.py
      - RSS 取得、前処理、raw_news への保存ロジック
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank 関数

---

## テスト・開発上の注意

- テスト時は外部 API 呼び出し（OpenAI, J-Quants, HTTP）をモックしてください。
  - モジュール内の _call_openai_api を unittest.mock.patch で差し替え可能です。
  - news_collector._urlopen も置き換えられるよう設計されています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI などで不要な自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB executemany の仕様により、空のパラメータ配列を渡さないように注意している箇所があります（pipeline / news_nlp など）。

---

## トラブルシューティング（よくある点）

- 「環境変数が設定されていません」エラー
  - config.Settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）を .env に設定しているか確認してください。
- OpenAI 呼び出しで JSON パース失敗
  - LLM の出力が JSON モードでも前後に余計なテキストが混ざることを想定し、パースフォールバックを行いますが、何度も失敗する場合はプロンプトやモデル制約、API レスポンスを確認してください。
- J-Quants API の 401（Unauthorized）
  - get_id_token でリフレッシュトークンを使った自動更新を実装しています。refresh token（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。

---

## ライセンス・貢献

（この README には記載がありません。プロジェクトの LICENSE や CONTRIBUTING を参照してください）

---

以上がこのコードベースの概要と基本的な使い方です。より詳細な仕様や運用ルール（StrategyModel.md / DataPlatform.md 相当）はプロジェクト内の設計ドキュメントを参照してください。必要であれば README に追記するセクション（例: デプロイ手順、CI 設定、実運用時の監視設定）を教えてください。