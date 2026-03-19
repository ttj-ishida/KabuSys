# KabuSys

日本株向け自動売買システムのライブラリ群（KabuSys）。  
データ収集（J-Quants/ RSS）、DuckDBベースのデータ管理、研究（ファクター計算／探索）、特徴量生成、シグナル生成、監査ログまでを包含するモジュール群を提供します。

主な設計方針
- DuckDB をローカルDBとして使用し、冪等な保存・更新を行う。
- ルックアヘッドバイアスを防ぐ設計（target_date 時点のみ参照）。
- API呼び出しはレート制御・リトライ・認証リフレッシュ対応。
- ニュース収集は SSRF・XML攻撃・GzipBomb などを考慮した安全実装。

---

## 機能一覧

- データ収集 / ETL
  - J-Quants API クライアント（株価、財務、マーケットカレンダー取得）
    - レートリミット順守、リトライ、401時のトークン自動リフレッシュ
  - RSS ニュース収集（トラッキングパラメータ除去、URL正規化、銘柄抽出）
  - DuckDB スキーマ初期化・保存関数（raw / processed / feature / execution 層）
  - 日次差分 ETL（バックフィル、品質チェックのフック）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ

- 戦略（Strategy）
  - feature_engineering: research で作成した raw factor を正規化して `features` テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を計算し BUY/SELL シグナル生成、`signals` へ保存

- その他
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログ（signal→order→execution のトレース設計）
  - ニュースの銘柄抽出・保存（raw_news / news_symbols）
  - セキュリティ配慮（RSSのSSRF対策、XMLパースの安全化等）

---

## 前提・依存関係

- Python 3.10+
  - 型ヒント（`X | Y`）などにより Python 3.10 以上を想定しています。
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクト配布側に requirements ファイルがあればそちらを使用してください）

---

## セットアップ手順

1. Python 3.10+ をインストール。

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください）

4. パッケージを開発モードでインストール（任意）
   プロジェクトルートに pyproject.toml がある場合:
   ```bash
   pip install -e .
   ```

5. 環境変数を設定
   - .env または OS の環境変数に以下を設定します（必須は README の該当を確認）。
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — environment（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
   - .env 自動読み込み: パッケージ内でプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local をロードします。自動ロード無効化は:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

6. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```
   ":memory:" を渡すとインメモリ DB として初期化できます。

---

## 使い方（簡易例）

以下は典型的な日次処理の流れの例です（ETL → 特徴量作成 → シグナル生成）。

1. 日次 ETL を実行してデータを取得・保存する
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量 (features) を構築する
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   # conn は上で初期化した DuckDB 接続
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

3. シグナルを生成する
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals

   n = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {n}")
   ```

4. ニュース収集ジョブの実行例
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は有効な銘柄コード集合（例: prices_daily の code 一式）
   known_codes = {"7203", "6758", ...}
   result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(result)
   ```

主要な API の返り値や振る舞いは各モジュールの docstring を参照してください（例: run_daily_etl は ETLResult を返す、generate_signals は書き込んだシグナル数を返す等）。

注意点
- generate_signals / build_features は target_date 時点のデータのみを参照するため、実行タイミングと market_calendar に注意してください（休日は調整されます）。
- J-Quants の API レート制限は内部で制御していますが、大量バッチ等は考慮して下さい。

---

## 主要設定（環境変数）

必須・代表的な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（値は任意）

config モジュールは .env ファイルの自動読み込み機能を持ち、.env/.env.local のルールで OS 環境変数と統合します。

---

## ディレクトリ構成（抜粋）

（ソースツリーは `src/kabusys/` 配下）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得/保存関数）
    - news_collector.py       — RSS 取得・前処理・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — 差分ETL / run_daily_etl 等のオーケストレータ
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - features.py             — data.stats の再エクスポート
    - calendar_management.py  — カレンダー更新・営業日判定ユーティリティ
    - audit.py                — 監査ログ用DDL・初期化（signal/events/order/execution など）
    - (その他: quality, monitoring などが存在する想定)
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py             — 発注・約定処理のためのプレースホルダ（実装は別）
  - monitoring/               — 監視・メトリクス関連（実装は別）

---

## 実装上の注意・設計メモ（要約）

- ETL と特徴量／シグナル生成は冪等に動くように設計（DELETE→INSERT の日付単位置換、ON CONFLICT 等）。
- J-Quants クライアントは固定間隔スロットリングを実装し、ページネーション・リトライ・401リフレッシュを扱います。
- NewsCollector は URL 正規化・トラッキング除去・SSRF対策・XMLパースの安全化・Gzipサイズ制限などを備えています。
- Strategy 層は AIスコアや各コンポーネントのスコアを組み合わせて final_score を算出し、Bear レジームでは BUY を抑制する等のポリシーを実装しています。
- 設計ドキュメントの参照箇所（StrategyModel.md, DataPlatform.md 等）を実運用/拡張時に確認してください。

---

## 開発・貢献

- バグ報告・機能提案は Issue へお願いします。
- ローカルでの動作確認は DuckDB の ":memory:" を使うと簡単です。
- 長期的な拡張点として execution 層（ブローカー連携）やリスク管理モジュールの実装が想定されています。

---

README の内容はソースコードの docstring を元にまとめています。より詳細なAPIやパラメータの振る舞いは各モジュールの docstring を参照してください。