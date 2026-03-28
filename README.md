# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP による銘柄センチメント評価、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）等のユーティリティを含みます。

主な目的は「データ取得 → 品質チェック → 特徴量生成 → シグナル生成 → 監査・実行」に至る一連の処理を安全に、かつバックテストでルックアヘッドバイアスを発生させない設計で提供することです。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務（四半期）データ、JPXマーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得・ページネーション・トークン自動リフレッシュ・レート制御・リトライ実装

- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比閾値超え）、日付不整合（未来日付／非営業日のデータ）を検出

- ニュース収集・NLP
  - RSS フィードから記事を安全に収集（SSRF対策、サイズ制限、トラッキングパラメータ除去、正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント評価（batch処理、JSON-mode、リトライ、スコアクリップ）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で `'bull'|'neutral'|'bear'` を判定・保存

- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリューなどのファクター計算（DuckDB + SQL）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー等

- 監査（Auditing）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル定義・初期化ユーティリティ（監査 DB 初期化機能あり）

- 設定管理
  - .env / .env.local / 環境変数から設定を自動ロード（プロジェクトルート検出）し、settings オブジェクト経由で参照可能

---

## 前提 / 必要環境

- Python 3.10 以上（型記法 Path | None 等を利用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード 等）

インストール例（仮）:
pip install duckdb openai defusedxml

※パッケージ配布（pyproject.toml / requirements.txt）がある場合はそちらに従ってください。

---

## 環境変数 / .env (主なもの)

kabusys はプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token で使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (任意)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)  
  環境: development | paper_trading | live（デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

- OPENAI_API_KEY (必要な処理時)  
  OpenAI API 呼び出しに使用（news_nlp, regime_detector 等）

注意: settings は kabusys.config.settings 経由で参照できます。必須変数が未設定だと ValueError が発生します。

---

## セットアップ手順（例）

1. リポジトリをクローン／コピー
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール
   pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）
4. 環境変数設定
   プロジェクトルートに `.env` を作成（.env.example を参照して必要キーをセット）
   例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. DuckDB 初期スキーマ／監査 DB の作成（必要に応じて）
   - 監査テーブルを初期化:
     from kabusys.data.audit import init_audit_db
     init_audit_db("data/audit.duckdb")
   - その他スキーマはプロジェクトの schema 初期化ユーティリティに従ってください（本リポジトリにスキーマ作成ロジックがある想定）

---

## 使い方（代表的な操作例）

以下は Python REPL / スクリプト内での呼び出し例です。

- DuckDB へ接続:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL（J-Quants から差分取得・品質チェック）:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント評価（target_date のウィンドウで記事を集約して ai_scores に書き込む）:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  cnt = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {cnt} codes")

- 市場レジーム判定（score_regime は market_regime テーブルへ書き込む）:
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（監査専用 DB を作る）:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 設定参照:
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

ヒント:
- OpenAI API を使う処理は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバック（失敗時はセンチメント 0.0）を備えていますが、キーがないと ValueError を発生させます。
- 自動で .env を読み込まないようにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - 多くの関数は datetime.today()/date.today() を内部で直接参照せず、target_date を明示的に受け取ります。バックテストでは必ず過去データのみ参照するように設計されています。

- フェイルセーフ:
  - ニュース NLP や LLM 呼び出しは失敗時に明確なフォールバック（スコア 0.0）を行い、ETL 全体を停止させない設計です。ただし結果の欠落が生じうるため監視が必要です。

- 冪等性:
  - ETL の保存処理は ON CONFLICT（upsert）や個別 DELETE+INSERT を用いて冪等に動作するよう設計されています。

- セキュリティ:
  - news_collector モジュールは SSRF 対策（リダイレクト検査、プライベート IP 判定）、XML パースの安全実装（defusedxml）、レスポンスサイズ制限 を備えています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         # ニュースセンチメント評価（OpenAI）
  - regime_detector.py  # マーケットレジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py   # J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py         # ETL パイプライン（run_daily_etl 等）
  - quality.py          # データ品質チェック
  - news_collector.py   # RSS ニュース収集
  - calendar_management.py # カレンダー（営業日判定等）
  - audit.py            # 監査ログ（監査テーブル定義・初期化）
  - etl.py              # ETLResult 再エクスポート
  - stats.py            # 統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py  # モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py # 将来リターン, IC, 統計サマリー 等
- research/*.py (その他研究用モジュール)

---

## よくある運用フロー（例）

1. 夜間バッチ（Cron/CI）で run_daily_etl を実行 → DuckDB にデータを蓄積
2. ニュース収集ジョブを定期実行（RSS） → raw_news に保存
3. 朝のマーケット前に score_news / score_regime を実行して AI スコア・レジームを更新
4. 戦略モジュールがデータ・スコアを参照してシグナルを生成し、監査テーブルに保存
5. 実際の発注処理は execution 層（kabu API 経由）で実行し、order_requests / executions に記録

---

## そのほか

- ロギングはモジュールごとに行われます。LOG_LEVEL を環境変数で調整してください。
- DuckDB バージョン依存の留意点（executemany の空リスト制約等）についてはコード内コメントを参照してください。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って外部環境の影響を制御できます。

---

問題や改善点、README に加えてほしいサンプルやスクリプトがあれば教えてください。README をプロジェクト実態に合わせて調整して提供します。