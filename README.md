# KabuSys

日本株向けの自動売買 / 分析プラットフォーム（ライブラリ兼バックテスト実装）。

このリポジトリは、データ取得（J‑Quants）、特徴量生成、シグナル生成、ポートフォリオ構築、約定シミュレーション（バックテスト）、ニュース収集などを含む一連の処理をモジュール化したコードベースです。Look‑ahead バイアス回避や冪等性・エラーハンドリング設計が随所に取り入れられています。

主な設計方針（抜粋）
- ルックアヘッドバイアス防止: target_date 時点で利用可能なデータのみで計算を行う
- 冪等性: DB への書き込みは日付単位の置換や ON CONFLICT を利用
- ネットワーク堅牢性: レートリミット・リトライ・トークン自動更新など実装
- バックテストは DB を読み取り専用でコピーして in‑memory DuckDB 上で実行

---

## 主な機能一覧

- データ取得 / ETL
  - J‑Quants API クライアント（株価・財務データ・市場カレンダー等の取得、保存）
  - RSS ニュース収集（正規化、SSRF 対策、記事 → 銘柄紐付け）
- 研究・特徴量
  - momentum / volatility / value 等のファクター計算（research モジュール）
  - Z スコア正規化、ユニバースフィルタ
- 戦略（シグナル）
  - features + AI スコアを統合した final_score 計算
  - BUY/SELL シグナル生成、Bear レジームによる BUY 抑制、エグジット条件（ストップロス等）
- ポートフォリオ構築
  - 候補選定、等配分／スコア配分、リスクベース配分
  - セクター上限適用、レジーム乗数による資金調整、株数丸め（単元考慮）
- バックテスト
  - 約定・スリッページ・手数料モデルを考慮したシミュレータ
  - 日次ループでシグナル生成 → 約定（翌日始値） → 時価評価 → 指定範囲での評価
  - メトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
  - CLI 実行エントリポイントあり
- 設定管理
  - .env / 環境変数からの設定読み込み（プロジェクトルート探索、自動読み込みを提供）

---

## 必要条件 (依存パッケージの例)

コードベースから利用している主なライブラリ例：
- Python 3.10+
- duckdb
- defusedxml

プロジェクト全体の正確な requirements は本リポジトリに含まれていないため、環境に応じて追加してください（例: pip install duckdb defusedxml）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   ```
   pip install -e .              # パッケージを開発モードでインストール（setup.py/pyproject がある場合）
   pip install duckdb defusedxml
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（あるいは `.env.local`）を作成してください。自動ロード機能により .env が読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション接続パスワード（実運用時）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
     - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は代表的な利用方法の例です。

- バックテストの実行（CLI）
  DuckDB ファイルがあらかじめ prices_daily, features, ai_scores, market_regime, market_calendar 等で準備されている必要があります。

  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db path/to/kabusys.duckdb
  ```

  主なオプション:
  - --start / --end: バックテスト開始/終了日
  - --cash: 初期資金（JPY）
  - --slippage / --commission: スリッページ / 手数料率
  - --allocation-method: equal | score | risk_based
  - --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size

- 特徴量の構築（ライブラリ呼び出し例）
  Python スクリプトから DuckDB 接続を渡して features を作成します。

  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features

  conn = duckdb.connect("path/to/kabusys.duckdb")
  n = build_features(conn, target_date=date(2023, 12, 31))
  print(f"upserted {n} features")
  conn.close()
  ```

- シグナル生成（ライブラリ呼び出し例）
  features と ai_scores が揃っている状態でシグナルを生成して signals テーブルに書き込みます。

  ```python
  from kabusys.strategy.signal_generator import generate_signals
  from datetime import date
  import duckdb

  conn = duckdb.connect("path/to/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2023, 12, 31))
  print(f"generated {count} signals")
  ```

- ニュース収集ジョブ（プログラム呼び出し）
  RSS ソースから記事を収集して DB に保存します。

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("path/to/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 事前に stocks のコードセットを用意
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J‑Quants からのデータ収集例
  fetch + save の流れを利用します。

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb
  from kabusys.data.jquants_client import get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
  conn = duckdb.connect("path/to/kabusys.duckdb")
  saved = save_daily_quotes(conn, recs)
  ```

---

## ディレクトリ構成（主要ファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J‑Quants トークン、kabu API、Slack、DBパスなど）
  - data/
    - jquants_client.py — J‑Quants API クライアント、データ取得／保存関数
    - news_collector.py — RSS ニュース収集、前処理、DB 保存、銘柄抽出
    - (その他データ関連モジュール: schema, calendar_management 等がプロジェクト内に想定)
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリー等の分析ユーティリティ
  - strategy/
    - feature_engineering.py — 生ファクターの正規化・features テーブルへの保存
    - signal_generator.py — features + ai_scores から final_score を算出し signals テーブルへ書き込む
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算（等配分 / スコア配分）
    - position_sizing.py — 株数決定（risk_based / equal / score）、aggregate cap
    - risk_adjustment.py — セクターキャップ適用、レジーム乗数
  - backtest/
    - engine.py — バックテストループ（データコピー、シグナル→約定→評価 の統合）
    - simulator.py — ポートフォリオシミュレータ（約定モデル、mark_to_market、履歴・約定記録）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来用途の模擬時計（現状は使用されない）
  - portfolio/ (エクスポート用 __init__ あり)
  - backtest/ (エクスポート用 __init__ あり)
  - strategy/ (エクスポート用 __init__ あり)
  - research/ (エクスポート用 __init__ あり)
  - execution/, monitoring/ — パッケージ候補（現状空または未実装のサブパッケージ）

---

## 注意事項 / 実運用に向けた補足

- Look‑ahead（情報の先行利用）を厳密に避けるため、特徴量/シグナル生成は target_date 時点で取得可能なデータのみを使う実装になっています。バックテストを行う際は、外部データ（stocks, ai_scores, features 等）を適切にバックフィルしてください。
- DuckDB スキーマ（tables）や初期データの準備は別途 ETL スクリプトが必要です（本コードは DuckDB への書き込みを行いますが、テーブル定義ファイルや初期投入手順はこの README 範囲外です）。
- news_collector では RSS の XML パースや外部接続において安全対策（defusedxml、SSRF 検査、レスポンスサイズ制限）を実装していますが、運用環境のポリシーに合わせて追加の監査や制限を行ってください。
- kabuステーションや実際の注文実行を行う execution 層は本コードからは分離されている想定です。実マーケットでの注文を出す場合は、必ずペーパートレード環境で十分なテストを行ってください。

---

## 開発 / 貢献

- Lint / 型チェック: 任意で flake8 / mypy 等を導入して静的解析を行ってください。
- テスト: ユニットテストや統合テストは本リポジトリに含まれていません。重要ロジック（ポジション計算、サイジング、シグナル生成など）には単体テストを追加することを推奨します。

---

この README はコード内の docstring とコメントを基に手早くまとめた概要ドキュメントです。追加で具体的なセットアップスクリプト、requirements.txt、DB スキーマ (data/schema.py 相当)、および運用手順（ETL ジョブ・監視・Slack 通知フロー等）を整備すると実運用に向けて安全に移行できます。