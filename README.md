# KabuSys

日本株の自動売買／バックテスト・データパイプライン用ライブラリ群です。  
ポートフォリオ構築、ファクター生成、シグナル生成、バックテストエンジン、J‑Quants API クライアント、RSS ニュース収集などの機能を提供します。

主な設計方針（抜粋）
- 研究用モジュール（research）や戦略（strategy）はルックアヘッドバイアスを避けるため、必ず target_date 時点までのデータのみを使用。
- 多くの DB 操作は冪等（上書き/ON CONFLICT）で実装。
- J‑Quants クライアントはレート制限・リトライ・トークン自動リフレッシュを備える。
- ニュース収集は SSRF 対策・XML 攻撃対策（defusedxml）を実施。

---

## 機能一覧

- データ取得・保存
  - J‑Quants API クライアント（fetch/save：日足・財務・上場情報・カレンダー）
  - RSS ニュース収集と記事→銘柄紐付け
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - ファクター探索ユーティリティ（将来リターン、IC、統計サマリ等）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - raw ファクターの正規化、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナル出力
  - Bear レジームでの BUY 抑制、SELL（ストップロス・スコア低下）判定
- ポートフォリオ構築（portfolio）
  - 候補選別、等配分/スコア加重、リスクベースのサイジング
  - セクター集中制限、レジーム乗数
- バックテスト（backtest）
  - インメモリ DuckDB コピーによる安全なバックテスト環境構築
  - ポートフォリオシミュレータ（スリッページ・手数料・部分約定対応）
  - バックテストメトリクス（CAGR、Sharpe、MaxDD、勝率等）
  - CLI エントリ（python -m kabusys.backtest.run）
- 設定管理（config）
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検知）
  - 必須環境変数チェック

---

## 必須環境変数

（README 作成時点でコードから参照される主要キー）
- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（任意: デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネルID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

注意
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、自動で `.env` と `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発向け）

前提
- Python 3.10 以上（型ヒントで | を使用）
- Git リポジトリのルートに移動して作業することを想定

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージをインストール
   - 最低限必要な外部依存（例）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを利用してください）
3. パッケージをローカルインストール（任意）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 最小例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

5. DuckDB スキーマ初期化
   - コード中で参照される `kabusys.data.schema.init_schema` を使って DB 初期化を行ってください（スキーマ作成ロジックは別モジュールにある想定）。

---

## 使い方（代表例）

バックテスト実行（CLI）
- 事前に DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar 等の必要テーブルが準備されていることが必要です。
- 実行例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb

ライブラリとして（Python API）
- DuckDB 接続初期化（例）:
  ```py
  from kabusys.data.schema import init_schema
  conn = init_schema("path/to/kabusys.duckdb")
  ```
- 特徴量構築:
  ```py
  from kabusys.strategy import build_features
  from datetime import date
  build_features(conn, target_date=date(2024, 1, 31))
  ```
- シグナル生成:
  ```py
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  ```
- ニュース収集ジョブ:
  ```py
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, known_codes=set_of_codes)
  ```
- J‑Quants データ取得 + 保存:
  ```py
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, recs)
  ```

バックテスト API（プログラムから）
```py
from kabusys.backtest.engine import run_backtest
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history, result.trades, result.metrics を利用
```

注意点
- strategy / research モジュールは DB の features / prices_daily / raw_financials 等を参照します。バックテストでは run_backtest が本番 DB からインメモリ接続へ必要データをコピーして安全に実行します。
- live 環境での発注・execution 層の実装は別途必要（execution パッケージはプレースホルダ）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数・設定管理（.env 自動読み込み、必須キー検査）
- data/
  - jquants_client.py — J‑Quants API クライアント（レート制限・リトライ・保存）
  - news_collector.py — RSS 収集、前処理、raw_news 保存、銘柄抽出
  - (schema, stats, calendar_management など別モジュールを参照)
- research/
  - factor_research.py — momentum / volatility / value の定量ファクター計算
  - feature_exploration.py — forward returns / IC / summary
- strategy/
  - feature_engineering.py — ファクター正規化・features テーブルへの書き込み
  - signal_generator.py — final_score 計算、BUY/SELL 判定、signals テーブル書き込み
- portfolio/
  - portfolio_builder.py — 候補選別・重み計算
  - position_sizing.py — 発注株数計算（等配分 / スコア / リスクベース）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- backtest/
  - engine.py — バックテスト全体フロー（run_backtest）
  - simulator.py — ポートフォリオシミュレータ（約定モデル）
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
  - clock.py — 模擬時計（将来拡張用）
- execution/ — 発注・kabuステーション連携等（現状空）
- monitoring/ — 監視用ロジック（別途実装想定）

各モジュールはソース内に詳細な docstring と使用上の注意が書かれているため、必要に応じて参照してください。

---

## 開発時の補助情報

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI/テストで環境変数を明示的に制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J‑Quants クライアントはページネーション・トークンキャッシュを内部で保持します。認証周りで問題があれば get_id_token を直接呼び出して確認してください。
- news_collector は defusedxml を利用した XML パース、URL スキーム/プライベートアドレス検査、サイズ上限チェックなどの安全対策を備えています。

---

## 注意事項（重要）

- 本コードベースは投資判断ツールの一部を構成します。実運用（特に live 環境）で使用する際は適切なリスク管理、検証、法令順守を行ってください。
- live 環境での自動売買は重大な資金損失を招く可能性があります。paper_trading モードや十分なバックテストで挙動を確認してください。

---

必要でしたら、README に含める例の .env.example、requirements.txt の候補、あるいは具体的な CLI 実行例やサンプルスクリプトを追加で作成します。どの情報を優先して追記しましょうか？