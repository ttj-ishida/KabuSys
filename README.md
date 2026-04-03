# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
DuckDB をデータストアに、J-Quants（市場データ）や OpenAI（ニュースのNLP評価）を組み合わせて、データの ETL、品質チェック、ファクター計算、ニュースセンチメント、監査ログなどを一貫して扱うことを目的としています。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得・ETL
  - J-Quants から日次株価（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション・トークン自動リフレッシュ・レートリミット制御を実装

- データ品質チェック
  - 欠損データ、前日比スパイク、重複、将来日付・非営業日の存在などを検出するチェック群

- ニュース収集・NLP（OpenAI）
  - RSS 取得（SSRF対策・サイズ制限・トラッキングパラメータ除去）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）に送り、銘柄単位の ai_score を生成

- 市場レジーム判定（AI + 指標合成）
  - ETF（1321）の200日移動平均乖離とマクロニュースの LLM センチメントを重ね合わせて日次のマーケットレジーム（bull/neutral/bear）を算出・保存

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（情報係数）や統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - シグナル→発注要求→約定までを UUID 連鎖でトレースする監査テーブル群（冪等・履歴保持）

---

## 必須および推奨環境変数

以下はいくつかの主要な環境変数（.env に設定）です。プロジェクトはプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL で使用）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注など）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH など: 実行監視関連
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定例はプロジェクトの `.env.example` を参照して作成してください。

---

## 依存ライブラリ（主なもの）

- Python 3.9+（型ヒントに Path | None 等を使用）
- duckdb
- openai（OpenAI SDK）
- defusedxml
- そのほか標準ライブラリ中心に実装されています（詳細は pyproject.toml / requirements を参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成・有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   （プロジェクトに pyproject.toml / requirements.txt がある想定です）

   ```
   pip install -e .            # editable install（パッケージ化されている場合）
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定

   プロジェクトルートに `.env` を作成し、必要なキーを設定します（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   注: 自動ロードは、パッケージの config モジュールが `.git` または `pyproject.toml` を基準にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要APIサンプル）

以下はライブラリを直接使う簡単な例です。実行前に DuckDB ファイル・テーブルなどの初期化が必要な場合があります（初期スキーマはプロジェクト内別モジュールで定義している想定です）。

- DuckDB 接続の作成例

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（差分取得・保存・品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（AI による銘柄別センチメント）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("書込銘柄数:", n_written)
  ```

- 市場レジーム判定（ma200 + マクロニュース）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数から取得
  ```

- 監査ログ DB 初期化（監査用 DuckDB ファイル作成 + テーブル作成）

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests 等の操作が可能
  ```

---

## 自動ロードの挙動（.env）

- パッケージ読み込み時に、プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は `.env` の上書きを防ぎますが `.env.local` は上書きされます（テスト時のホスト上書きなどに便利）。
- 自動読み込みを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェルの export 構文やクォート、コメントなど多くのケースに対応します。

---

## 主要モジュール・ディレクトリ構成

（省略されたファイルがある場合がありますが、概観は次の通りです）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの集約・OpenAI を用いた銘柄センチメント算出
    - regime_detector.py      — マクロセンチメント + MA200 を組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py             — ETL 管理・run_daily_etl 等
    - etl.py                  — ETL インターフェースの再エクスポート（ETLResult）
    - quality.py              — 品質チェック（欠損/スパイク/重複/日付不整合）
    - news_collector.py       — RSS 収集（SSRF対策・前処理）
    - calendar_management.py  — マーケットカレンダーの管理（営業日判定/更新）
    - stats.py                — Zスコア等の統計ユーティリティ
    - audit.py                — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等

---

## 注意点・設計上の要点

- ルックアヘッドバイアス対策
  - 各種処理（ニュースウィンドウ、価格参照等）は明示的な target_date を受け取り、内部で現在日付を参照しない設計になっています。バックテスト用途でも過去情報のみを使うように設計されています。

- フェイルセーフ設計
  - 外部 API の失敗や不正レスポンス時は例外を投げずフォールバック（0.0 スコアやスキップ）する箇所が多く、運用時に一部失敗しても処理全体が停止しにくいようになっています。

- 冪等性
  - J-Quants からの DB 保存処理は ON CONFLICT DO UPDATE を基本に冪等に設計されています。監査ログも order_request_id による冪等を想定しています。

- セキュリティ
  - RSS 取得では SSRF 対策、XML の defusedxml 利用、受信サイズ制限などを実装しています。
  - J-Quants の API 呼び出しはレートリミット、リトライ、トークンリフレッシュ処理を備えています。

---

## 貢献 / 開発

- 追加のユニットテスト、型アノテーションの強化、OpenAI 呼び出しの抽象化（テストのモック化容易化）などが想定されます。
- 大きな変更を行う場合は README と設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を合わせて更新してください。

---

README の簡潔な使い方は以上です。より詳細な API（各関数の引数・返り値・挙動）についてはソースコード内の docstring を参照してください。必要であれば README に含めたい追加の実行例・運用手順（cron / systemd の監視スクリプト例や Docker 化手順など）を教えてください。