# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants からのデータ取り込み（ETL）・データ品質チェック・ニュース収集・AI によるニュースセンチメント評価・市場レジーム判定・監査ログ管理など、現物/先物アルゴリズム運用で必要になる機能群を提供します。

主な設計方針：
- DuckDB を中心とした軽量なオンプレ/クラウドデータ基盤
- Look‑ahead bias を避ける設計（内部で date.today()/datetime.today() を参照しない関数設計）
- 外部 API 呼び出しはリトライ、バックオフ、レート制御を実装
- 冪等性（ETL 保存、監査ログなど）を重視

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場情報、マーケットカレンダー）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集
  - RSS から記事を収集、前処理、raw_news に保存（SSRF 対策、トラッキングパラメータ除去）
- AI（LLM）によるスコアリング
  - 銘柄ごとのニュースセンチメント評価（news_nlp.score_news）
  - マクロ × ETF（1321）MA200 を組み合わせた市場レジーム判定（regime_detector.score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- ユーティリティ
  - カレンダー管理（営業日判定・前後営業日の取得）
  - DuckDB 用保存ユーティリティ（冪等保存）

---

## 必要条件

- Python 3.10 以上
- DuckDB
- OpenAI Python SDK（gpt 系モデル呼び出し用）
- defusedxml（RSS パースの安全性）
- （オプション）その他利用する機能に応じた依存

推奨の pip パッケージ例（requirements.txt にまとめてください）:
- duckdb
- openai
- defusedxml

（プロジェクトルートに pyproject.toml / setup などがある場合はそこからインストールできます）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール
   例: requirements.txt がある場合
   ```
   pip install -r requirements.txt
   ```
   もしくは最低限:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env を用意
   プロダクションで必要な主な環境変数（.env に設定しておくことを推奨）:

   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - OPENAI_API_KEY=<openai_api_key>  # news_nlp / regime_detector で使用
   - (オプション) KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KABUSYS_ENV, LOG_LEVEL 等

   注意:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベース用ディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（settings.duckdb_path）です。適宜ディレクトリを作成してください。

---

## 使い方（基本例）

以下は主要ユーティリティの利用例です。実際は適切なロギング・エラーハンドリングを追加してください。

- DuckDB 接続の生成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（AI）を計算し ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要なら audit_conn を監査ログの読み書きに使う
  ```

- ファクター計算・リサーチユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- カレンダー系ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## .env の例 (.env.example)
プロジェクトルートに .env を置くと自動読み込みされます（.env.local は上書き可能）。
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込み・管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM センチメントスコアリング
    - regime_detector.py     — マクロ + ETF を用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存/認証）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult を公開
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize など）
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward return / IC / summary / rank

---

## 運用時の注意点

- OpenAI / J-Quants の API キーは適切に管理し、不要な権限や公開を避けてください。
- ETL / LLM 呼び出しはコストが発生します。バッチ粒度・バッチ回数を運用で調整してください。
- DuckDB のスキーマはデータ量に応じて VACUUM やファイル管理を検討してください（大量データではファイルサイズ増加に注意）。
- 本リポジトリの例はライブラリ実装が主体であり、実行用の CLI / サービス化は別途実装してください。

---

## 貢献 / 開発

- コードは src/ 配下に配置してあり、ローカル開発時は `pip install -e .`（または setuptools／pyproject を用いた編集インストール）で取り込み可能です。
- テストはユニットテストで OpenAI・HTTP 呼び出しをモックして実行してください（内部でモック用 hook を使える箇所があります）。
- 自動環境読込を無効にしたいテストでは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

不明点や README に追加したいサンプル（デプロイ手順、CLI 例、CI 設定など）があれば教えてください。README を要望に合わせて拡張します。