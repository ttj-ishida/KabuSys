# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量/リサーチ、AI を用いたニュースセンチメント、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、上場銘柄一覧、JPXカレンダーの差分取得・ページネーション対応
  - レート制限・再試行・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得・保存・品質チェックをワンストップで実行
  - run_daily_etl による日次パイプライン
- データ品質チェック
  - 欠損（OHLC）・重複・スパイク（急騰・急落）・日付不整合の検出
- ニュース収集 / NLP
  - RSS から記事取得・前処理・DB格納（raw_news）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントのバッチ評価（ai.score_news）
  - マクロニュース + 1321（ETF）MA200乖離を合成した市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等の計算（DuckDB 上で完結）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions を定義し、発注フローをUUIDでトレース
  - 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 前提条件

- Python 3.10 以上
- 必要な外部ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- J-Quants / kabuステーション / Slack / OpenAI の各種認証情報（環境変数で設定）

（プロジェクト環境に応じて requirements.txt を用意してください。ここでは主要な依存を列挙しています。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt があればそれを使用してください）
   ```bash
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # または開発時は editable install
   pip install -e .
   ```

3. 環境変数設定
   プロジェクトルートに `.env` ファイルを置くと自動で読み込まれます（.git または pyproject.toml を基準に探索）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

   必須（最低限）環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション / 推奨:
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime で使用）
   - KABUSYS_ENV: `development`/`paper_trading`/`live`（デフォルト: development）
   - LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
   - SQLITE_PATH: SQLite パス（デフォルト: `data/monitoring.db`）

   `.env.example` を参考に `.env` を作成してください（config.py の _require は .env.example を参照する旨のメッセージを出します）。

---

## 簡単な使い方（サンプル）

以下は最小限の実行例です。DuckDB の DB ファイル（デフォルト data/kabusys.duckdb）を用います。

1. 日次 ETL を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースセンチメント（ai.score_news）を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   print(f"scored {count} symbols")
   ```
   - api_key を省略すると環境変数 `OPENAI_API_KEY` を参照します。
   - API 呼び出しはバッチ（最大 20 銘柄）で行われます。

3. 市場レジーム判定（ai.regime_detector）を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   ```

4. 監査ログ DB の初期化
   ```python
   from pathlib import Path
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(Path("data/audit.duckdb"))
   # conn は初期化済みの DuckDB 接続
   ```

5. RSS フィード取得（ニュース収集ユーティリティ）
   ```python
   from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

   articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
   for a in articles[:5]:
       print(a["id"], a["datetime"], a["title"])
   ```

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数の読み込み・設定検証（自動 .env ロード機能）
- kabusys.data.jquants_client
  - J-Quants API との通信、取得 & DuckDB 保存（save_*）関数
- kabusys.data.pipeline
  - run_daily_etl 等の ETL ワークフロー
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.news_collector
  - RSS 収集、安全対策（SSRF/サイズ制限）付き
- kabusys.ai.news_nlp
  - ニュースを銘柄ごとにまとめて OpenAI に送り、スコアを ai_scores に書き込む
- kabusys.ai.regime_detector
  - ETF（1321）MA200乖離とマクロ記事のLLMセンチメントを合成して市場レジーム判定
- kabusys.research
  - ファクター計算（momentum, value, volatility）、forward returns、IC、統計サマリー
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）DDL & 初期化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                — ETL パイプライン（run_daily_etl など）
    - quality.py                 — データ品質チェック
    - news_collector.py          — RSS 収集（SSRF対策・前処理）
    - calendar_management.py     — 市場カレンダー管理 / 営業日ロジック
    - audit.py                   — 監査ログ初期化 / DDL
    - etl.py                     — ETLResult の再エクスポート
    - stats.py                   — 共通統計ユーティリティ（zscore 正規化）
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility 計算
    - feature_exploration.py     — forward returns / IC / summary / rank

その他、package metadata 等はプロジェクトルートに配置される想定です（pyproject.toml 等）。

---

## 運用上の注意点

- Look-ahead bias に配慮した設計が各所に組み込まれています（date の取り扱い、取得ウィンドウの排他条件など）。バックテスト等で使用する際は、この点を理解した上でデータを扱ってください。
- OpenAI/API の呼び出しはコストやレート制限に注意してください。実行前に API キーやバッチ粒度、リトライ方針を調整してください。
- DuckDB の executemany に関する注意（空リスト不可）は pipeline / news_nlp 等で考慮されています。直接 SQL を実行する際は留意してください。
- .env 自動ロードはプロジェクトルート検出に依存します。CI・テストで制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境変数管理してください。

---

## 貢献・開発

- 追加のユニットテスト、CI、requirements.txt / pyproject.toml の整備を推奨します。
- 外部 API（J-Quants / OpenAI / kabu API）をモックするユーティリティや fixtures を用意するとテストが容易になります。
- 重大な変更を加える場合は Look-ahead bias / 冪等性 / トランザクション境界に特に注意してください。

---

必要に応じて README に追加したい点（例えば具体的な requirements.txt、CI の設定、運用 runbook、データスキーマの詳細など）があれば教えてください。README をプロジェクト実態（パッケージ配布 or 社内運用）に合わせて拡張します。