# KabuSys

日本株向けの自動売買システム用ライブラリ群（データ収集・前処理・特徴量生成・シグナル生成・バックテスト・ニュース収集 等）

このリポジトリは、J-Quants API などからデータを取得して DuckDB に格納し、特徴量の合成 → シグナル生成 → バックテストを行うためのモジュール群を提供します。設計上、本番の発注 API への直接依存は最小限に抑え、研究 / バックテスト用途に適した純粋な計算・ETL レイヤを中心に実装しています。

## 主な機能
- データ取得 / 保存
  - J-Quants からの株価（日足）・財務データ・市場カレンダーの取得（jquants_client）
  - RSS ベースのニュース収集（news_collector）
  - DuckDB スキーマ定義と初期化（data.schema）
- ETL パイプライン
  - 差分取得・保存・品質チェック（data.pipeline）
- 研究用 / 特徴量計算
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン / IC / 統計サマリー（research.feature_exploration）
  - クロスセクション Z スコア正規化（data.stats）
- 戦略
  - 特徴量の正規化・フィルタ適用 → features テーブルへ保存（strategy.feature_engineering）
  - features と AI スコアを統合して final_score を計算し、BUY/SELL シグナルを生成（strategy.signal_generator）
- バックテスト
  - 日次ベースのシミュレータ（スリッページ・手数料を考慮）（backtest.simulator）
  - バックテストループ（signals を用いた日次シミュレーション）（backtest.engine）
  - パフォーマンス指標計算（backtest.metrics）
  - CLI エントリ（python -m kabusys.backtest.run）
- 設定管理
  - .env / 環境変数から設定を読み込むユーティリティ（config.py）。自動ロードはプロジェクトルート（.git または pyproject.toml）基準。

---

## 動作環境（推奨）
- Python 3.10 以上（| 型ヒントなどの構文を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ほか標準ライブラリのみで実装されている箇所が多いですが、実行環境に応じて追加パッケージが必要になる場合があります。

インストール例（仮想環境を使用することを推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時は pip install -e . などでパッケージ化しておくと便利です
```

---

## 環境変数 / 設定
このプロジェクトは環境変数から設定を取得します（kabusys.config.Settings）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で自動的に読み込みます（.env.local が上書き）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

設定取得例（Python）:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（簡易）
1. Python と必要パッケージをインストール（上記参照）
2. DuckDB ファイルの初期化（スキーマ作成）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: でも可
     conn.close()
     ```
   - これにより必要なテーブルが作成されます（冪等）。
3. 環境変数 / .env を用意
   - .env.example（任意）を作り、必須の API トークン等を設定します。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```
4.（任意）J-Quants トークンがあればデータ取得・保存ジョブを実行

---

## 使い方（代表的な例）

1. バックテスト（CLI）
   DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が事前に用意されている必要があります。
   ```bash
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 --db data/kabusys.duckdb
   ```
   出力に CAGR / Sharpe / MaxDrawdown / Win Rate / Payoff Ratio 等が表示されます。

2. DuckDB スキーマ初期化（プログラム）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn を渡して ETL / feature / backtest 関数を呼び出す
   ```

3. ETL（株価差分取得）の実行（プログラム）
   data.pipeline の関数群を使用します。
   例（疑似コード）:
   ```python
   from kabusys.data.pipeline import run_prices_etl
   # conn: DuckDB 接続、target_date: datetime.date
   fetched, saved = run_prices_etl(conn, target_date)
   ```

4. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes: 銘柄コード集合（抽出に使用）
   results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
   ```

5. 特徴量作成・シグナル生成（戦略）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features, generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   target = date(2024, 2, 1)
   n_features = build_features(conn, target)
   n_signals = generate_signals(conn, target)
   conn.close()
   ```

6. バックテストをプログラムで呼ぶ
   ```python
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.backtest.engine import run_backtest
   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date, end_date)
   # result.history / result.trades / result.metrics を参照
   conn.close()
   ```

---

## ログ設定と実行モード
- 環境変数 KABUSYS_ENV は次のいずれか:
  - development, paper_trading, live
- LOG_LEVEL は DEBUG / INFO / WARNING / ERROR / CRITICAL
- logging は各スクリプト内で基本設定を行っているため、必要に応じて logging.basicConfig を上書きしてください。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 内の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env ロード / settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制限・リトライ・保存ユーティリティ）
    - news_collector.py
      - RSS 取得・記事整形・DB 保存・銘柄抽出
    - schema.py
      - DuckDB のスキーマ定義 & init_schema()
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（差分取得・保存・品質チェック）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル用の正規化・フィルタ処理
    - signal_generator.py
      - final_score 計算と signals テーブルへの書き込み
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（バックテストループ）
    - simulator.py
      - PortfolioSimulator（擬似約定ロジック・日次スナップショット）
    - metrics.py
      - バックテスト評価指標計算
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - 将来拡張用の模擬時計
  - execution/
    - __init__.py
    - （発注・実行層の実装エリア）
  - monitoring/
    - （監視・アラート用モジュール格納エリア）

---

## 注意事項 / 設計上のポイント
- ルックアヘッドバイアスへの配慮:
  - 戦略・研究モジュールは target_date 時点で利用可能なデータのみ参照する設計になっています。
  - データ取得の fetched_at（UTC）は、いつその情報が利用可能になったかをトレースする目的で記録されます。
- 冪等性:
  - DuckDB への保存処理は ON CONFLICT / トランザクションを用いた冪等設計になっています。
- 安全対策:
  - news_collector は SSRF 対策・受信サイズ上限・defusedxml を用いた XML パース防御等を実施しています。
- 設定の自動ロードはプロジェクトルート検出に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を検討してください。

---

## 参考 / 今後の拡張案
- execution 層の実装強化（実際の発注 API 連携）
- マルチ期間・分足バックテストのサポート
- AI スコア生成パイプラインの追加
- Kubernetes / Airflow 等での ETL スケジューリング向けの CLI / サービス化

---

不明点や README に追記してほしい具体的な利用例（例: ETL の CLI、CI 設定、.env の雛形など）があれば教えてください。必要に応じて README を拡張します。