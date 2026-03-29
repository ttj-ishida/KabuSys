# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants からの市場データ取得・ETL、ニュース収集と AI によるニュース/マクロセンチメント評価、ファクター計算、研究ユーティリティ、監査テーブル（オーダー追跡）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータベース設計（冪等保存）
- 外部 API 呼び出しはレート制御・リトライ・フェイルセーフを考慮
- テストが容易になるように API キー注入やモック差し替えをサポート

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検査（`kabusys.config.settings`）

- データ ETL（J-Quants）
  - 株価日足（OHLCV）の差分取得・保存（ページネーション対応、レート制御）
  - 財務データ（四半期 BS/PL）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（差分取得 / 保存 / 品質チェック）

- データ品質チェック
  - 欠損値検出、スパイク（急変）検出、重複チェック、日付整合性チェック
  - `QualityIssue` オブジェクトで詳細を取得

- ニュース収集
  - RSS フィード取得・前処理（URL 正規化、トラッキングパラメータ除去）
  - SSRF 対策・サイズ制限・XML の安全パース
  - raw_news / news_symbols への冪等保存（実装は jquants_client / 保存関数と併用）

- ニュース NLP / マクロレジーム検知（OpenAI）
  - 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価（JSON Mode）
  - マクロニュース + ETF(1321) の 200 日 MA 乖離を合成して市場レジーム（bull/neutral/bear）判定
  - API 呼び出しはリトライ / エラーハンドリングあり（フェイルセーフで 0.0 にフォールバック）

- リサーチ用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 監査ログ（オーダー追跡）
  - signal_events / order_requests / executions の DDL と初期化
  - 監査 DB 初期化ユーティリティ（DuckDB）

---

## 前提（推奨環境）

- Python 3.10+
- 必要パッケージ（最小限、用途に応じて追加）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

※ 実際のパッケージ管理（pyproject.toml / requirements.txt）はこのリポジトリに依存します。ローカルでの実行前に必要な依存をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements ファイルがあればそれを使ってください：
   ```
   pip install -r requirements.txt
   ```

4. 開発インストール（ソースから編集しながら使う場合）
   ```
   pip install -e .
   ```
   ※ パッケージが src レイアウトのため、リポジトリルートで実行してください。

5. 環境変数の設定
   プロジェクトルートに `.env`（および任意で `.env.local`）を用意すると自動で読み込まれます（読み込みは .git または pyproject.toml を起点にルート探索）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文実装に使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（任意）
   - SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID（任意）
   - OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム判定で使用）

   任意 / デフォルト値を持つ変数:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB の SQLite パス（デフォルト data/monitoring.db）

---

## 使い方（主な API と実行例）

以下はライブラリをインポートして操作する簡単な例です。実運用時はログ設定や例外処理を適切に行ってください。

- DuckDB 接続の準備（デフォルト path は settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダーの差分取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {written} symbols")
  ```

- マクロ＋MA による市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- research（ファクター計算）の利用例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査ログ DB 初期化（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions のテーブルが作成される
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

注）OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を使用する想定です。API 呼び出しの詳細は kabusys.ai.* の実装を参照してください。API の失敗時はフェイルセーフで 0.0 を返す設計になっています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 ただし Slack を使う場合) — Slack Bot Token
- SLACK_CHANNEL_ID (必須 ただし Slack を使う場合) — Slack チャンネル
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH — デフォルト DuckDB ファイル（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定

設定は .env / .env.local に記述できます。自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に行われます。

---

## ディレクトリ構成

リポジトリ内の主なファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定・.env 読み込みロジック（settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの OpenAI スコアリング
    - regime_detector.py     — マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL のインターフェース再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py      — RSS 収集、前処理、SSRF 対策
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計関数（zscore_normalize）
    - audit.py               — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ 以下に更に細かな実装が含まれます

- pyproject.toml / setup.cfg / requirements.txt（存在する場合） — パッケージ管理

---

## 開発上の注意点 / 設計ノート

- Look-ahead Bias を防ぐため、関数は target_date を明示的に受け取り、内部で現在時刻を勝手に参照しない実装が多く採用されています。
- 外部 API（J-Quants / OpenAI）呼び出しはレート制御・リトライ・エラー時のフォールバックを備えていますが、API キーの管理や料金、レート制限は利用者側で注意してください。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT）で行われ、ETL は部分失敗時に既存データを不必要に削除しない設計です。
- テスト時にはモック差し替えポイント（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen など）を利用してください。

---

## サポート / 貢献

不具合や機能要望があれば Issue を立ててください。プルリク歓迎です。コーディング規約やユニットテストを整備した上での PR をお願いします。

---

README は以上です。必要であれば「セットアップの自動化（docker / github actions）」や「サンプルデータの準備方法」「詳細な API 使用例（J-Quants レスポンス形式に合わせた ETL）」など追加で追記できます。どのセクションを詳しくしたいか教えてください。