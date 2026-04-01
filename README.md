# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、リサーチ（ファクター計算・IC 解析）、監査ログ（発注〜約定のトレーサビリティ）などを包括的に提供します。

主な設計方針
- ルックアヘッドバイアスを避けるため、内部関数は date.today()/datetime.today() を直接参照しない設計。
- DuckDB を主なオンディスク DB として使用（軽量で分析向け）。
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、ニュースのセンチメント等を取得。
- J-Quants API からのデータ取得はリトライとレート制御を備え、取得時刻（fetched_at）を記録してトレース可能にする。
- ETL / 品質チェック / カレンダー管理 / 監査ログなど、実運用を想定した堅牢な実装。

---

## 機能一覧

- 設定管理
  - .env / 環境変数からの自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）
  - settings オブジェクトからプロジェクト設定を取得

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価日足、財務データ、JPX カレンダーの差分取得・保存
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策・サイズ制限・URL 正規化）
  - raw_news / news_symbols への冪等保存ロジック

- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウ内の記事を銘柄別に集約し、OpenAI でセンチメントを評価して ai_scores に保存
  - バッチ／リトライ／レスポンス検証

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離 + マクロニュース LLM センチメント を合成し市場レジーム（bull/neutral/bear）を判定
  - 結果を market_regime テーブルへ冪等書き込み

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの保持、営業日判定（next/prev/get_trading_days/is_sq_day など）
  - DB データがない場合は曜日ベースのフォールバック

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化
  - init_audit_db による監査用 DuckDB 初期化（UTC タイムゾーン固定）

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出し、認証（refresh token → id token）、ページネーション、保存関数（raw_prices / raw_financials / market_calendar）を提供
  - レート制御、リトライ、401 時のトークン自動リフレッシュ

---

## 前提（Prerequisites）

- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI 等）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれを利用してください。以下は最低限の例）

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置
   - 開発時: pip install -e . などでインストール可能（setuptools/pyproject を用意している場合）。

2. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必要な主な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C12345678
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

   サンプル .env（.env.example としてプロジェクトに追加すると良い）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB 用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

4. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   または最低限:
   ```
   pip install duckdb openai defusedxml
   ```

---

## 使い方（簡単なコード例）

以下は主要な操作の例です。すべての操作は DuckDB 接続（kabusys.config.settings.duckdb_path を利用可）を引数に取ることが多いです。

- 設定と DB 接続の準備
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックを順次実行）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores へ書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 第3引数 api_key を渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（market_regime へ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマ初期化（監査用 DuckDB を初期化）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて監査テーブルにアクセスできます
```

- 研究用ファクター計算・IC
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点
- OpenAI 呼び出しや外部 API はネットワークリスクがあるため、production では適切なエラーハンドリング・ロギング・レート制御を行ってください。ライブラリ側でも多くのフェイルセーフが組み込まれています（API失敗時にスコアを 0 にする、リトライ等）。
- ETL / ニュース収集などはスケジューラ（cron/airflow 等）から日次で呼ぶことを想定しています。

---

## 環境変数 / 設定一覧（代表的なもの）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD      : kabuステーション API パスワード
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（モニタリング用）デフォルト data/monitoring.db
- KABUSYS_ENV            : development | paper_trading | live
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL

設定は .env / .env.local / OS 環境変数の順に解決されます。プロジェクトルートは .git または pyproject.toml の位置から自動検出します。

---

## ディレクトリ構成（パッケージ内概観）

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / settings 管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュースセンチメント（OpenAI）
    - regime_detector.py      -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       -- J-Quants API クライアント（fetch/save）
    - news_collector.py       -- RSS ニュース収集（SSRF 対策等）
    - calendar_management.py  -- 市場カレンダー管理 / 営業日判定
    - quality.py              -- データ品質チェック
    - stats.py                -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                -- 監査ログスキーマ初期化
    - etl.py                  -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      -- Momentum / Value / Volatility 等
    - feature_exploration.py  -- 将来リターン / IC / summary / rank

各モジュールは API ドキュメント（docstring）を充実させており、関数の引数・戻り値・副作用（DB テーブル参照等）が明記されています。

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API キー等）は .env.local を使い、リポジトリには含めないこと。
- OpenAI 呼び出しは有料リソースのため、ローカルでのデバッグ時はモック（unittest.mock.patch）で置き換えること。
- ETL は外部 API 依存のためリトライ・ロギングを十分に行い、失敗時の通知（Slack 等）を別途組み合わせてください。
- DuckDB のファイルは定期的にバックアップしてください。監査ログは原則削除しない運用を想定しています。
- 本リポジトリのコードは「実運用を想定した設計」を多く含みますが、証券取引や実際の発注を行う前に必ずペーパートレード環境で十分に検証してください。

---

必要であれば、README に以下の追加情報を追記できます：
- 依存関係の完全な requirements.txt（バージョン固定）
- よくあるエラーとトラブルシュート
- CI / ローカルテストの実行方法（pytest 等）
- データベーススキーマの詳細（DDL抜粋）  

追記希望があれば教えてください。