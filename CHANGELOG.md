# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- 特になし

## [0.1.0] - 2026-03-20

Added
- パッケージ基盤
  - パッケージ `kabusys` を公開。トップレベルで `data`, `strategy`, `execution`, `monitoring` をエクスポート。
  - バージョン定義: `__version__ = "0.1.0"`。

- 環境設定（kabusys.config）
  - `.env` ファイルおよび環境変数から設定を自動ロードする仕組みを追加。
    - 自動ロードの対象ルートは `.git` または `pyproject.toml` を親ディレクトリから探索して特定（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - OS の既存環境変数を保護するための `protected` キーセットをサポート（上書き禁止）。
  - `.env` パーサを実装（`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - `Settings` クラスでアプリケーション設定を提供:
    - 必須設定の取得と未設定時の `ValueError` を実装（例: `JQUANTS_REFRESH_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `KABU_API_PASSWORD`）。
    - デフォルト値の提供: `KABUS_API_BASE_URL`, `DUCKDB_PATH`, `SQLITE_PATH`。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効な列挙値のみ許容）、`is_live` / `is_paper` / `is_dev` プロパティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
    - レート制限（120 req/min）を守る固定間隔のスロットリング実装（内部 `_RateLimiter`）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は `Retry-After` を尊重。
    - 401 受信時は自動でリフレッシュトークンを用いて `id_token` を更新して 1 回リトライ（無限再帰防止のフラグ制御）。
    - ページネーション対応（`pagination_key` を用いたループ）を実装。
    - 取得時刻（`fetched_at`）は UTC 形式で記録し、Look-ahead bias のトレースを容易に。
  - DuckDB への保存関数:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を提供。いずれも冪等な insert/update（`ON CONFLICT DO UPDATE`）を使用。
    - PK 欠損レコードはスキップして警告ログを出力。
    - 型変換ユーティリティ `_to_float`, `_to_int` を用いて堅牢に変換。小数がある数値文字列は誤って切り捨てない挙動を確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集用モジュール実装（既定ソースに Yahoo Finance のカテゴリ RSS を含む）。
  - セキュリティ対策:
    - XML 解析に `defusedxml` を使用し XML Bomb 等を防御。
    - URL 正規化時にトラッキングパラメータ（`utm_*`, `fbclid` など）を除去。
    - URL スキームの検証（HTTP/HTTPS のみ）や受信サイズ上限（10MB）を設けて SSRF / メモリ DoS を緩和。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - DB 保存時の性能対策としてバルク INSERT のチャンク化を実施。1 トランザクションにまとめることでオーバーヘッド低減。挿入件数は正確に返却。

- リサーチ系（kabusys.research）
  - ファクター計算（`research.factor_research`）:
    - `calc_momentum`：1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は `None` を返す。
    - `calc_volatility`：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。`true_range` の NULL 伝播を正確に制御。
    - `calc_value`：`raw_financials` から最新財務データを取得し PER/ROE を計算（EPS 無効時は `None`）。
    - いずれも DuckDB の SQL ウィンドウ関数を活用し、高速でトレース可能な実装。
  - 特徴量探索（`research.feature_exploration`）:
    - `calc_forward_returns`：指定ホライズンにおける将来リターン（デフォルト [1,5,21] 営業日）を計算。ホライズンの妥当性検査あり。
    - `calc_ic`：スピアマンのランク相関（Information Coefficient）を実装。サンプル不足時は `None`。
    - `factor_summary`：指定カラムの count/mean/std/min/max/median を計算。
    - `rank`：同順位は平均ランクとするランク付けを提供。丸め誤差対策のため round(..., 12) を使用。
    - 研究用モジュールは外部ライブラリ依存を避け、標準ライブラリと DuckDB のみで実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - `build_features(conn, target_date)` を実装:
    - 研究モジュール（`calc_momentum`, `calc_volatility`, `calc_value`）から生ファクターを取得。
    - ユニバースフィルタを適用（最低株価 300 円、20 日平均売買代金 5 億円）。
    - 指定カラムを Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 にクリップして外れ値の影響を抑制。
    - 日付単位の置換（既存行削除→トランザクション→バルク挿入）により冪等性と原子性を担保。
    - 処理結果は `features` テーブルへ挿入。

- シグナル生成（kabusys.strategy.signal_generator）
  - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装:
    - `features` と `ai_scores` を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
    - スコア変換にはシグモイド関数を用い、欠損コンポーネントは中立値 0.5 で補完（欠損による不当な降格を防止）。
    - 重みはデフォルト値を用意し、ユーザ与件は検証のうえフォールバック／正規化（合計 1.0 になるよう再スケール）。
    - Bear レジーム判定: AI の `regime_score` 平均が負の場合（サンプル数閾値あり）に BUY シグナルを抑制。
    - BUY シグナル: final_score >= threshold の銘柄をランク順で選定（Bear レジーム時は抑制）。
    - SELL シグナル（エグジット）:
      - 実装済: ストップロス（終値が avg_price から -8% 以下）、スコア低下（final_score < threshold）。
      - 未実装（将来的な拡張可能性としてコメントあり）: トレーリングストップ、時間決済（保有 60 営業日超過）。
    - signals テーブルへの日付単位置換（DELETE→INSERT、トランザクションを用いて原子性を保証）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクは連番で再付与。

Security
- ニュース収集で defusedxml を採用、RSS/HTML 処理における安全性を確保。
- 外部 API 呼び出し時のトークン管理と再取得ロジックにより、認証失敗時の自動回復を実現。
- `.env` パーサと自動ロードはプロジェクトルート検出を行い、安全に環境を設定。

Performance
- DuckDB のウィンドウ関数・集約を活用したバルク計算により多数銘柄を効率的に処理。
- J-Quants クライアントは固定間隔レートリミッタを持ち、スロットリングで API 制限に従う。
- DB へのバルク挿入はチャンク化およびトランザクションでまとめて実行しオーバーヘッドを低減。

Notes / 今後の拡張候補
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに `peak_price` / `entry_date` 等が必要。
- news_collector の RSS ソースは拡張可能（デフォルトは Yahoo Finance のビジネスカテゴリ）。
- 外部依存を最小化する方針だが、将来的に統計処理やデータ処理での性能改善のため pandas 等を導入する余地あり。

----
作成元: ソースコード解析に基づく初回リリース記録（推定）