# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ取得（J-Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（リサーチ向け）、品質チェック、監査ログ等のユーティリティを提供します。

主な設計方針：
- DuckDB を中心としたローカルデータレイク（Raw / Processed / Feature / Execution 層）
- J-Quants API の取得処理はレートリミット・リトライ・トークン自動更新対応
- ETL は差分更新（バックフィル）かつ冪等（ON CONFLICT）で安全に保存
- ニュース収集は RSS を安全に取得（SSRF / XML Bomb 対策）し、記事→銘柄紐付けまで実施
- 研究（research）モジュールは外部 API にアクセスせず DuckDB のテーブルのみ参照して解析を行う

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local または OS 環境変数から自動読み込み（プロジェクトルート検出）
  - 必須設定は取得時にバリデーション
- データ取得 / 保存
  - J-Quants から日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE / DO NOTHING）
  - レートリミット（120 req/min）、リトライ、ID トークン自動更新を内蔵
- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 市場カレンダー先読み、株価・財務の差分取得、品質チェック実行
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合（未来日／非営業日）を検出
- ニュース収集
  - RSS フィード取得、前処理（URL除去・空白正規化）、記事ID生成（URL 正規化＋SHA-256）
  - SSRF・XML攻撃対策、レスポンスサイズ制限、銘柄抽出（4桁コード）
  - raw_news / news_symbols への冪等保存
- リサーチ（特徴量 / ファクター）
  - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、バリュー（PER/ROE）等を DuckDB 上で計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- スキーマ管理 / 監査ログ
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ用のテーブル群（signal_events / order_requests / executions 等）

---

## 要件

- Python >= 3.10（型ヒントに | を使用）
- 必須 Python パッケージ:
  - duckdb
  - defusedxml

（ネットワーク取得は標準ライブラリ urllib を使用しているため追加の HTTP ライブラリは不要）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# またはプロジェクトをパッケージとしてインストールする場合:
# pip install -e .
```

---

## 環境変数 / .env

自動的にプロジェクトルート（.git または pyproject.toml の場所）を探索して `.env` / `.env.local` をロードします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（README 用の参考一覧）:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行モード / ロギング
  - KABUSYS_ENV (development | paper_trading | live, デフォルト development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO)

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに setup/pyproject があれば `pip install -e .` を使って開発インストールできます）

4. 環境変数を設定（.env を作成）
   - プロジェクトルートに `.env` を作成し、必要な値を記載します（上記参照）。

5. DuckDB スキーマ初期化
   - デフォルトパスは `.env` の DUCKDB_PATH（未設定時は data/kabusys.duckdb）
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（簡易サンプル）

以下は代表的な利用シーンの使い方です。実運用ではログ設定・エラーハンドリング・ジョブスケジューリング等を追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た接続、target_date は省略で今日
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブの実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は文字列の set（例: {"7203","6758"}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

4) リサーチ：ファクター計算・IC 計算の利用例
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize
from datetime import date

# conn: DuckDB 接続
target = date(2024, 1, 15)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# 例: mom の mom_1m と fwd の fwd_1d を使って IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) 監査ログスキーマの初期化（監査専用 DB を用いる場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 推奨運用フロー（例）

- 夜間バッチ（cron / Airflow など）
  1. カレンダー更新ジョブ（calendar_update_job）
  2. 日次 ETL（run_daily_etl）
  3. 品質チェック結果の集約とアラート（Slack 通知等）
  4. 特徴量作成 → 戦略実行 → シグナル保存 → 発注ワークフロー（監査ログでトレース）

- リサーチ環境は DuckDB をそのまま参照してオフライン解析を実行

---

## ディレクトリ構成

以下は主要ファイル／モジュールの概要です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・保存関数）
    - news_collector.py
      - RSS 収集・記事正規化・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 他）
    - features.py
      - 特徴量ユーティリティ（zscore 正規化の再公開）
    - calendar_management.py
      - market_calendar 関連ユーティリティ（is_trading_day / next_trading_day 等）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）
    - etl.py
      - ETL の公開インターフェース（ETLResult など）
    - quality.py
      - データ品質チェック
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
      - research の公開 API（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー
    - factor_research.py
      - Momentum/Volatility/Value ファクター計算
  - strategy/
    - __init__.py
    - （戦略実装・ポートフォリオ最適化等を配置）
  - execution/
    - __init__.py
    - （発注・ブローカー連携・オーダー管理を配置）
  - monitoring/
    - __init__.py
    - （モニタリング関連コードを配置、例: メトリクス、Slack 通知等）

---

## 注意事項 / 実装上のポイント

- J-Quants API の呼び出しにはレート制限（120 req/min）があります。モジュールは内部で固定間隔スロットリングとリトライを行います。
- ETL は冪等設計（INSERT ... ON CONFLICT ...）のため、再実行や一部再取得を許容します。バックフィル日数を調整して API の後出し修正を吸収できます。
- ニュース収集はセキュリティを重視（SSRF 対策、XML の安全パーサー、最大受信サイズ制限など）。
- DuckDB のバージョンによりサポートされる機能や制約が変わる場合があります（README 内の注意書きや実行環境での検証を推奨）。
- 本リポジトリのコードは本番口座への直接注文を行うモジュール（execution 層等）を含む可能性があるため、本番運用時は慎重なテストと監査ログの整備を行ってください。

---

必要であれば、README に実際の .env.example ファイル内容、CI のセットアップ手順、Airflow/cron のワークフロー例、Slack 通知サンプルコード、あるいは戦略層のインタフェース設計（StrategyModel.md 相当）のセクションを追加できます。どの部分を詳細化したいか教えてください。