# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリセット（KabuSys）。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ETL、データ品質チェック、リサーチ用ファクター計算、監査ログ（監査DB）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤を構築するためのモジュール群です。主な目的は次の通りです。

- J-Quants API を用いた株価・財務・上場情報・市場カレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析（銘柄単位）およびマクロセンチメントと移動平均乖離を合成した市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティなど）
- 監査ログ（signal → order_request → executions の追跡用スキーマ）初期化ユーティリティ

---

## 機能一覧

- 環境設定読み込み・管理（.env 自動ロード、必要環境変数チェック）
- J-Quants API クライアント（レートリミット管理、リトライ、トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- ニュース収集（RSS を安全にフェッチ、正規化、raw_news に保存する想定）
- OpenAI を用いたニュースセンチメント（score_news）と市場レジーム判定（score_regime）
- リサーチユーティリティ（ファクター計算：calc_momentum, calc_value, calc_volatility、将来リターン、IC、統計サマリ）
- 統計ユーティリティ（zscore_normalize）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

---

## 必要条件 / 依存

- Python >= 3.10（型注釈の | 演算子を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS フィードなど）

インストール例（開発環境）:
```bash
python -m pip install -U pip
python -m pip install "duckdb" "openai" "defusedxml"
# パッケージ自体をプロジェクトルートから editable install する場合
python -m pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを用いてください）

---

## 環境変数（必須/推奨）

KabuSys は環境変数または .env ファイルから設定を読み込みます（自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使います。
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード（注文モジュール使用時）
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン（通知モジュールを使う場合）
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID（通知先）
- OPENAI_API_KEY (必要に応じて)
  - news_nlp.score_news / regime_detector.score_regime 等で使用する OpenAI API キー。関数呼び出し時に api_key を渡すこともできます。
- DUCKDB_PATH (任意)
  - DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 sqlite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # または主要依存だけ
   python -m pip install duckdb openai defusedxml
   ```

4. .env をプロジェクトルートに配置（README の環境変数参照）。自動で .env / .env.local を読み込みます。

5. DuckDB 等の初期スキーマ作成（必要に応じてスクリプトを用意）  
   監査ログ用 DB を初期化する例は下記の「使い方」を参照。

---

## 使い方（サンプル）

以下は主なユーティリティの利用例です。

- DuckDB 接続と ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム（マクロ + MA200 乖離）を評価して market_regime テーブルに書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は監査スキーマが作成された DuckDB 接続を返します
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄のモメンタム指標を含む dict のリスト
```

注意点:
- score_news / score_regime では OpenAI API を呼び出します。api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / J-Quants 呼び出しには JQUANTS_REFRESH_TOKEN が必須です。

---

## 自動 .env ロードの挙動

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を起点に .env → .env.local の順で読み込みます。
- OS 環境変数が優先され、.env.local は既存の OS 環境変数を上書きできます（保護されたキーは上書きされません）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（主要ファイルの説明）

(以下は src/kabusys 以下の主要モジュールと役割)

- kabusys/
  - __init__.py
    - パッケージのバージョンと公開サブパッケージ定義
  - config.py
    - 環境変数読み込み・Settings クラス（必須変数チェック・既定値）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を OpenAI に送り、銘柄ごとの ai_score を ai_scores テーブルへ書き込むロジック
    - regime_detector.py
      - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を算出
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存ロジック・レート制御）
    - pipeline.py
      - ETL の主エントリ（run_daily_etl 等）と補助関数
    - etl.py
      - ETLResult を再エクスポート
    - calendar_management.py
      - 市場カレンダー管理と営業日判定ユーティリティ
    - news_collector.py
      - RSS 取得と前処理・SSRF 対策・ID 生成
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック群と QualityIssue 定義
    - audit.py
      - 監査ログスキーマ（DDL）と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク変換等
  - monitoring/ (プロジェクトに含まれる想定の監視モジュール等がある可能性)
  - execution/, strategy/, monitoring/ など（パッケージ __all__ に含まれるサブパッケージ。実装が追加される想定）

---

## 開発・テスト時のヒント

- OpenAI 呼び出し部分は内部でラップされており、テスト時は各モジュールの _call_openai_api をモックできます（unittest.mock.patch を推奨）。
- ネットワークアクセスや外部 API を行う関数はエラー時にフェイルセーフ動作（スコアのデフォルト値やスキップ）をするように設計されていますが、テストでは外部呼び出しをモックして deterministic にするのが良いです。
- DuckDB のバージョン依存（executemany の空リスト扱いなど）を考慮した実装になっています。DuckDB の互換性に注意してください。

---

## 参考（主要 API）

- ETL:
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- ニューススコア:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 監査ログ初期化:
  - kabusys.data.audit.init_audit_db(db_path) / init_audit_schema(conn)

---

この README はコードベース（src/kabusys/*.py）を参照して作成しました。より詳しい使用例や CLI、スキーマ定義、運用手順はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）があればそちらを参照してください。必要であれば README にさらに具体的なコマンド例・スキーマ SQL 抜粋・運用フローを追加します。