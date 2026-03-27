# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・LLM を用いたニュースセンチメント評価、リサーチ用ファクター計算、監査ログ（発注／約定トレーサビリティ）、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得・ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（DuckDB）。
  - 差分更新、ページネーション対応、トークン自動リフレッシュ、レートリミット管理、リトライ（指数バックオフ）。
- データ品質チェック
  - 欠損（OHLC）、スパイク検出（前日比閾値）、主キー重複、将来日付 / 非営業日データ検出。
- ニュース収集
  - RSS フィードを取得して raw_news に保存。URL 正規化・トラッキングパラメータ除去、SSRF 対策、XML デフューズ対策、サイズ制限。
- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）を用いて銘柄ごとのニュースセンチメント（ai_scores）をバッチで評価。JSON Mode / バリデーション / リトライ実装。
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次で市場レジーム（bull/neutral/bear）を算出・保存。
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等の定量ファクター計算、将来リターン計算、IC（ランク相関）やファクター統計サマリ。
- 監査ログ（オーダー／約定トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義・初期化。UUID ベースのトレーサビリティを提供。
- カレンダー管理
  - market_calendar を使った営業日判定・前後営業日の探索・夜間バッチ更新ジョブ。

---

## 前提条件

- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt で管理する想定）

実行環境により追加で Slack クライアントや kabuステーション API 関連ライブラリが必要になる場合があります。

---

## インストール（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（requirements.txt があれば）
   ```bash
   pip install -r requirements.txt
   ```
   または少なくとも：
   ```bash
   pip install duckdb openai defusedxml
   ```

4. パッケージをローカルインストール（編集可能モード）
   ```bash
   pip install -e .
   ```

---

## 環境変数 / .env

このプロジェクトは .env ファイルまたは環境変数から設定をロードします（os 環境変数が優先）。自動ロードはルート（.git または pyproject.toml）を検出して `.env` → `.env.local` の順で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings 参照）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

例 .env テンプレート
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル形式（export KEY=val 等）やクォート、行末コメントにも対応します。

---

## セットアップ手順（初期 DB 等）

- DuckDB 用ファイルは Settings.duckdb_path（デフォルト data/kabusys.duckdb）に保存されます。ディレクトリは自動作成される関数があるので基本的に手動作成不要です。
- 監査ログ用 DB 初期化（任意）:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" でインメモリ可
  ```
- DuckDB 接続例:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

---

## 使い方（主要 API 例）

※ 各関数は Look-ahead バイアス防止のため内部で date.today() を不用意に参照しない設計です。target_date を明示して実行することを推奨します。

- 日次 ETL の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  n = score_news(conn, date(2026, 3, 20))
  print(f"Wrote scores for {n} symbols")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, date(2026, 3, 20))
  ```

- 研究用ファクター計算（例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- カレンダー判定ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,20))
  ```

---

## 実装上の注意 / 動作ポリシー

- Look-ahead bias 対策: 多くのモジュールで target_date を明示的に受け取り、未来データ参照を避ける実装になっています。バックテスト等で使用する際はデータの取得タイミングに注意してください。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini（JSON mode）を使用する設計です。
  - API エラー時はフェイルセーフでスコア 0.0 へフォールバックする実装がありますが、API キーは必須です。
- J-Quants クライアント:
  - レート制限（120 req/min）遵守のため内部でスロットリングしています。
  - 401 受信時にはリフレッシュトークンを使って id_token を自動リフレッシュします。
  - save_* 関数は冪等（ON CONFLICT DO UPDATE）で DuckDB に保存します。
- NewsCollector:
  - RSS のサイズ・圧縮・リダイレクト・SSRF 対策・XML defuse を実装しています。
- テスト:
  - 自動で .env を読み込む初期挙動が妨げになる場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 一部外部 API 呼び出し部分はモック可能なように設計（内部 _call_openai_api など）されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン情報
- config.py — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（LLM）スコアリング、batch 処理、検証
  - regime_detector.py — マクロ + MA200 を合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集、前処理、保存ロジック
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（QualityIssue）
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー 等

（ファイル単位で多くの内部ユーティリティ・設計コメントが付与されています）

---

## 開発上の補足

- 型注釈や DuckDB を前提とした SQL 実行結果処理が多く存在します。DuckDB のバージョンや behavior に依存する箇所があるため、運用時は DuckDB のバージョン確認を行ってください（例: executemany に空リストを渡せない制約への対応など）。
- OpenAI SDK のバージョン差分で例外型やレスポンス構造が異なる可能性があります。テスト時は内部の _call_openai_api をパッチしてスタブ化することを推奨します。
- セキュリティ: news_collector は SSRF や XML Bomb 対策を組み込んでいますが、RSS ソースの管理や取得ポリシーは運用側で適切に管理してください。

---

必要であれば、README に含める具体的な requirements.txt や .env.example を生成することもできます。どの形式でサンプルを欲しいか教えてください。