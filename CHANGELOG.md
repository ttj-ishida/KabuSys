# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
公開バージョンはセマンティックバージョニングに従います。

※ 以下の変更点は、提供されたソースコードの内容から機能追加・設計方針を推測してまとめたものです。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装したベースラインです。

### Added
- 基本パッケージ/エントリポイント
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`
  - export: `__all__ = ["data", "strategy", "execution", "monitoring"]`

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索し、CWD に依存しない実装
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供
  - .env パーサーの実装（コメント、export プレフィックス、クォートやバックスラッシュエスケープ対応）
  - 必須環境変数取得ユーティリティ `_require` と `Settings` クラスを提供
    - 必須項目の例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス設定: `DUCKDB_PATH`・`SQLITE_PATH`（既定値あり）
    - 実行環境判定: `KABUSYS_ENV`（`development` / `paper_trading` / `live`）、`LOG_LEVEL` の検証

- データ取得・保存機能 (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装
    - レートリミット制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大 3 回）および 408/429/5xx に対するリトライ
    - 401 応答時はリフレッシュトークンを用いた id_token 再取得を 1 回自動で実行
    - ページネーション対応の取得関数を提供:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (四半期財務データ)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - DuckDB へ冪等保存する関数:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - データ型安全化ユーティリティ `_to_float`, `_to_int`
    - 取得時の fetched_at を UTC ISO8601 で保存（Look-ahead バイアス対策）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を収集し raw_news に保存するための実装（research / DataPlatform 設計に準拠）
    - デフォルト RSS ソース定義
    - 受信サイズ上限（10 MB）や XML 攻撃対策（defusedxml）を考慮
    - URL 正規化（トラッキングパラメータ除去・ソート・スキーム/ホスト小文字化・フラグメント削除）
    - 記事 ID は正規化した URL の SHA-256（先頭 32 文字）で生成して冪等性を担保
    - DB バルク挿入のチャンク化、トランザクションでの一括保存、ON CONFLICT 処理方針

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算と特徴量探索のための関数群を実装
    - calc_momentum / calc_volatility / calc_value:
      - prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、PER/ROE、出来高指標等）を計算
      - 移動平均、ATR、各種ウィンドウ処理は DuckDB のウィンドウ関数で実装
      - データ不足時の None 処理など堅牢化
    - calc_forward_returns: 将来リターン（1/5/21 営業日等）を計算（LEAD を利用）
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
    - rank: 同順位に対する平均ランク計算（丸めで ties の判定を安定化）
  - zscore_normalize は `kabusys.data.stats` から利用する想定（公開 API として再エクスポート）

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究で生成した raw ファクターを統合して `features` テーブルへ保存する処理を実装
    - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5 億円）
    - Z スコア正規化（対象カラム指定）＋ ±3 でクリップ（外れ値抑制）
    - features テーブルへ日付単位で置換（DELETE + INSERT のトランザクション処理で原子性確保）
    - ルックアヘッドバイアス回避の方針を明示（target_date 時点のデータのみ使用）

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - `features` と `ai_scores` を統合して最終スコア（final_score）を計算し `signals` テーブルへ保存
    - コンポーネントスコア: momentum / value / volatility / liquidity / news
    - 重み付けのデフォルト実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）
    - final_score による BUY シグナル閾値デフォルト 0.60
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら BUY を抑制、サンプル不足時は抑制しない）
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score が閾値未満
      - 保有銘柄価格欠損時の判定スキップとログ出力
    - weights の入力検証・補完・リスケーリング処理
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）

- モジュール再エクスポート
  - `kabusys.strategy.__init__` で `build_features` / `generate_signals` を公開
  - `kabusys.research.__init__` で主要な研究用 API を公開

### Design / Documentation (設計方針・注意点)
- Look-ahead Bias 回避:
  - すべての戦略・研究・保存処理で target_date 時点のデータのみを使用する方針を明示
  - データ取得時の fetched_at を UTC で記録
- 冪等性:
  - DuckDB への保存は ON CONFLICT/DELETE+INSERT を用いて日付単位/PK 単位で冪等化
- 耐障害性:
  - 外部 API 呼び出し: リトライ・指数バックオフ・HTTP ステータス別の挙動
  - ニュースパーシング: defusedxml を利用して XML 攻撃対策
  - .env 読み込みの失敗は警告で済ませ安全に動作継続
- DB 前提:
  - 各モジュールは DuckDB の特定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）の存在を前提とする
  - 一部の機能（例: トレーリングストップ、時間決済）は positions テーブルに追加カラム（peak_price / entry_date 等）が必要で未実装

### Fixed
- 初回リリースにつき該当なし（初期実装）

### Known limitations / TODO
- トレーリングストップや時間決済など、StrategyModel に記載されている一部のエグジット条件は未実装（注記あり）
- ニュースの銘柄マッチング（news_symbols への紐付け）実装概要はあるが、詳細な実装（エンティティ抽出等）は拡張余地あり
- 外部依存（DuckDB テーブル定義、Slack 通知、kabu API の execution 層など）は別モジュール/設定が必要
- 単体テストや統合テストの補足が必要（KABUSYS_DISABLE_AUTO_ENV_LOAD によるテスト時の環境制御をサポート）

---

（注）上記は提供されたソースコードから機能と設計方針を推測して作成した CHANGELOG です。実際の変更履歴やリリース日・パッチ情報はリポジトリのコミット履歴やリリースノートを参照してください。必要であれば、コミットログに基づくより詳細な CHANGELOG の生成を支援します。