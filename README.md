# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）→ ETL → 特徴量作成 → シグナル生成 → 発注（実装層）までの基盤機能を提供します。  
（本リポジトリは戦略・研究・データ基盤の共通ユーティリティ群を含みます）

---

## 主な特徴

- データ取得
  - J-Quants API クライアント（差分取得・ページネーション・自動トークンリフレッシュ・レートリミット）
  - RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・重複排除）
- ETL / データ基盤
  - DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 日次 ETL（市場カレンダー・株価・財務データの差分更新、品質チェック連携）
  - マーケットカレンダー管理（営業日判定／次営業日／前営業日等ユーティリティ）
- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン / IC（Spearman）計算、ファクター統計サマリ
- 戦略
  - 特徴量合成（ユニバースフィルタ・Z スコアクリップ・features テーブルへの保存）
  - シグナル生成（複数コンポーネントの重み付け合成、Bear レジーム抑制、BUY/SELL の冪等な書き込み）
- 品質・安全性設計
  - 冪等な DB 操作（ON CONFLICT / transaction）
  - ネットワーク安全対策（SSRF ブロッキング、gzip 上限等）
  - ロギング・エラーハンドリング重視の設計

---

## 必要な環境変数

このプロジェクトは環境変数 / .env を参照します。必須・推奨キーの例：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テスト用）

（.env.example を作成してプロジェクトルートに置く運用を推奨）

---

## セットアップ手順

1. Python 環境を準備（仮想環境推奨）
   - 推奨: Python >= 3.9（型ヒントで union 型等を利用）
2. 依存パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - defusedxml
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements.txt / pyproject があればそちらを利用してください）
3. リポジトリをクローンして編集モードでインストール（任意）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```
4. 環境変数を用意
   - プロジェクトルートに `.env` / `.env.local` を作成するか、OS 環境変数を設定してください。
   - 上記の必要な環境変数を設定します。
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから実行:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を指定すればインメモリ DB になります（テスト用）。

---

## 使い方（主要 API と簡単な例）

以下の例は最小限の実行フローを示します。実運用ではログ設定や例外ハンドリングを追加してください。

- DB 初期化 + 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量のビルド
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  total_signals = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes: 銘柄抽出時に有効な銘柄コードの集合（例: set(['7203','6758',...])）
  results = run_news_collection(conn, known_codes=None)
  print(results)
  ```

- research 用ユーティリティ
  - ファクターの評価や IC 計算などは `kabusys.research` 下の関数を利用できます。
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  ```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとした概略）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 関数）
    - news_collector.py
      - RSS 収集・前処理・DB 保存ロジック
    - schema.py
      - DuckDB スキーマ定義と init_schema()
    - stats.py
      - zscore_normalize 等統計ユーティリティ
    - pipeline.py
      - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py
      - 営業日判定・calendar_update_job
    - audit.py
      - 発注/約定の監査ログスキーマ（監査テーブル DDL）
    - features.py
      - 公開インターフェース（zscore_normalize の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル作成ロジック（ユニバースフィルタ・正規化）
    - signal_generator.py
      - final_score 計算と BUY/SELL シグナル生成、signals テーブル書込
  - execution/
    - __init__.py
      - （発注・ブローカ連携層はこの下に実装を想定）
  - その他
    - monitoring の実装ファイル（別途配置想定）

（上のファイル群はそれぞれ詳細な docstring と設計原則を備えています）

---

## 運用上の注意 / 実装上の留意点

- 環境依存のシークレットは必ず環境変数または安全なシークレット管理に保管してください。
- J-Quants のレート制限（120 req/min）を遵守するロジックがありますが、高頻度で大量データを取る場合は注意してください。
- ETL / DB 操作はトランザクションで保護されていますが、バックアップやバージョン管理は運用側で用意してください。
- 本コードはルックアヘッドバイアスを回避する設計を重視しています（target_date 時点のデータのみ参照等）。
- production（live）環境に切り替える際は KABUSYS_ENV を `live` に設定し、発注部分（execution 層）実装と安全対策を十分に行ってください。

---

## 開発・貢献

- 新しい機能追加や修正は issue を作成してください。
- 大きな変更は設計ドキュメント（StrategyModel.md / DataPlatform.md 等）に合わせて行うことを推奨します。
- テストの追加（ETL モジュール、ニュース収集のネットワーク依存部分はモック化）をお願いします。

---

README は以上です。必要であれば以下を追記します：
- 各モジュールの API リファレンス抜粋
- よくあるエラーと対処法（例: トークン期限切れ、DuckDB パス権限等）
- CI / デプロイ手順（Docker イメージ例）