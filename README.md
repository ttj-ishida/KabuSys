# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL（J-Quants）→ データ品質チェック → ファクター算出 → AI（OpenAI）によるニュースセンチメント評価 → 市場レジーム判定 → 監査ログ管理まで、一連のワークフローを提供します。

主に DuckDB を内部データストアとして想定し、J-Quants / OpenAI / RSS 等の外部データを取り込みます。

---

## 機能一覧

- 環境変数 / .env 自動読み込み管理（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存（ページネーション対応、ID トークン自動リフレッシュ、レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン（差分取得、バックフィル、品質チェック、日次実行エントリ）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合 等
- ニュース収集（RSS） & 前処理（SSRF 対策、トラッキングパラメータ除去、記事IDの冪等化）
- OpenAI を使ったニュース NLP（銘柄別センチメント -> ai_scores テーブルへ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログテーブル（signal_events / order_requests / executions）定義と初期化ユーティリティ
- 汎用統計ユーティリティ（Zスコア正規化 等）

---

## 前提・推奨環境

- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK v1系)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

最低限のインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```
（プロジェクト配布で requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` をロードします（OS 環境変数が優先）。

必須（機能を使う場合）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API の Base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知連携
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
- KABUSYS_ENV — 環境 (development | paper_trading | live)、デフォルトは development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な `.env` 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-....
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業環境を用意
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # ある場合
   # または最低限:
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env` を作成（上の例参照）
   - または OS 環境変数として設定

3. DuckDB 用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

4. 監査ログ DB を初期化（任意）
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # ファイルを作成してスキーマを初期化
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下は Python REPL やスクリプトからの利用例です。DuckDB 接続には duckdb.connect(...) を使用します（settings.duckdb_path を推奨）。

- DuckDB 接続例:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores 書き込み）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は env または api_key 引数で指定
  print("written:", written)
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマ初期化（既存接続へ追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect(str(settings.duckdb_path))
  init_audit_schema(conn, transactional=True)
  ```

- 研究系ユーティリティ（ファクター算出）:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect(str(settings.duckdb_path))
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  ```

注意点:
- 各モジュールはルックアヘッドバイアス防止のため、内部で date.today() などの参照を避け、引数で日付を受け取る設計です。バッチ実行・バックテスト時は必ず target_date を明示してください。
- OpenAI 呼び出し時は API 失敗でフェイルセーフ（多くの関数は失敗時に 0 または空で継続する設計）ですが、APIキーの未設定は ValueError を送出します。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env ローディングと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースのセンチメント評価と ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py — ETL パイプラインと run_daily_etl
  - etl.py — ETLResult の公開
  - calendar_management.py — マーケットカレンダー管理（営業日判定）
  - news_collector.py — RSS 収集と前処理
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログテーブル定義 / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン / IC / ランクなど研究用関数
- research/..., ai/..., data/... に関連する補助モジュール多数

---

## ロギング / モード

- KABUSYS_ENV により実行モードを切り替え（development | paper_trading | live）
- LOG_LEVEL でログレベルを設定（DEBUG/INFO/...）

---

## セキュリティ上の注意

- news_collector は SSRF 対策（ホスト検査・リダイレクト検査）や XML パースの安全化（defusedxml）を行っていますが、実運用ではさらに監査・モニタリングを行ってください。
- J-Quants / OpenAI の API キーは安全に管理し、公開リポジトリに置かないでください。
- duckdb のファイルパスやデータベースファイルの権限管理を適切に行ってください。

---

## 開発・テスト時の便利な設定

- 自動で .env を読み込みたくない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI / ネットワーク呼び出しは各モジュール内部の _call_openai_api / _urlopen 等をパッチしてユニットテストすることを想定して設計されています（unittest.mock.patch など）。

---

## ライセンス・貢献

（ここにプロジェクト固有のライセンス・貢献方法を追記してください）

---

README は以上です。必要であれば「セットアップを自動化するスクリプト」「.env.example のテンプレート」「デプロイ手順（systemd / supervisor 用）」などを追加で作成します。どれを優先しますか？