# Changelog

すべての非互換的な変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」ライブラリの基本機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として導入。
  - 主要サブパッケージを `__all__` で公開（data, strategy, execution, monitoring）。

- 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env / .env.local の読み込み順序と `.env.local` による上書きサポート。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化オプション。
  - export 形式やクォート、多様なコメント形式に対応した .env パーサー。
  - 必須環境変数取得のユーティリティ `_require` と `Settings` クラスを実装（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の入力バリデーション（許容値チェック）を実装。

- Data 層
  - J-Quants クライアント (`kabusys.data.jquants_client`)
    - レート制限 (120 req/min) を守る固定間隔スロットリング `_RateLimiter` を実装。
    - 冪等な HTTP リクエスト処理（リトライ、指数バックオフ、429 の Retry-After 考慮、401 時のトークン自動リフレッシュ）。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足、OHLCV）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
      - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
    - 取得時刻（fetched_at）を UTC ISO8601 形式で記録（Look-ahead バイアスのトレーサビリティ確保）。
    - 型変換ユーティリティ `_to_float` / `_to_int` を実装。

  - ニュース収集モジュール (`kabusys.data.news_collector`)
    - RSS フィードからの記事収集フローを実装指針として追加。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）機能 `_normalize_url` を実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）を考慮。
    - 応答バイト数上限（MAX_RESPONSE_BYTES）や SSRF 対策（スキーム制限 / ホストチェック等を意図）を想定した設計。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字など）で生成し冪等保存を想定。
    - raw_news / news_symbols などへのバルク保存を想定した仕様（チャンクサイズ制御）。

- Research 層
  - ファクター計算モジュール (`kabusys.research.factor_research`)
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）を計算する `calc_momentum` を実装。
    - ボラティリティ / 流動性指標（20日 ATR、相対 ATR、平均売買代金、出来高比率）を計算する `calc_volatility` を実装。
    - バリュー指標（PER, ROE）を raw_financials と prices_daily から組合せて計算する `calc_value` を実装。
    - DuckDB のウィンドウ関数・集約を活用した効率的な SQL 実装。
    - データ不足時の安全な None ハンドリングを実装。

  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns`（任意ホライズンの fwd リターンを一括取得）。
    - スピアマンのランク相関（IC）を計算する `calc_ic`（結合＆ランク化、最小サンプル数チェック）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。

  - 研究用共通インターフェースを `kabusys.research.__init__` でまとめて公開。

- Strategy 層
  - 特徴量作成 (`kabusys.strategy.feature_engineering`)
    - 研究で算出した生ファクターを統合・正規化して `features` テーブルへ保存する `build_features` を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（外部ユーティリティ zscore_normalize を利用）、±3 でクリッピングして外れ値影響を低減。
    - 日付単位での置換（DELETE + bulk INSERT）で冪等・原子性を保証。

  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - `features` と `ai_scores` を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成する `generate_signals` を実装。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算するユーティリティを実装（シグモイド変換、平均化、欠損補完は中立 0.5）。
    - デフォルト重みとユーザ入力重みのマージ・正規化処理（不正値除外、合計が 1.0 になるよう再スケール）。
    - Bear レジーム検出（AI の regime_score の平均が負のとき BUY を抑制、最小サンプル数チェックあり）。
    - エグジット判定（ストップロス: -8% 、スコア低下によるクローズ等）を実装（positions / prices_daily を参照）。
    - signals テーブルへ日付単位の置換で保存（冪等・原子性）。

- パッケージ公開インターフェース
  - `kabusys.strategy` にて `build_features`, `generate_signals` を公開。
  - `kabusys.research` に主要関数をまとめて公開。

### Fixed
- エラーや例外に対する堅牢化
  - DuckDB 書き込み時のトランザクションで例外発生時にロールバックを試み、ロールバック失敗時は警告ログを出すように変更（feature_engineering / signal_generator）。
  - J-Quants クライアントで JSON デコード失敗時に詳細なエラーを出力するよう改善。
  - .env ファイル読み込み失敗時に警告を出して処理継続するよう変更（IO エラーの安全な扱い）。

### Security
- news_collector で defusedxml を利用し XML パースの安全性を確保（XML Bomb 等の攻撃対策）。
- ニュース URL 正規化時にトラッキングパラメータを除去し、同一記事の重複挿入を抑制。
- J-Quants クライアントでトークン自動リフレッシュの実装により、認証失敗時の安全な再試行を実現。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、feature/signal の計算は target_date 時点で入手可能なデータのみを使用する方針を明確に保持。
- DuckDB を中心にしたデータフロー設計（prices_daily / raw_financials / raw_prices / raw_news / features / ai_scores / positions / signals 等のテーブル構成を想定）。
- 外部依存を最小化（research の統計処理は標準ライブラリのみ）し、ライブラリの移植性を重視。
- 各保存関数は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を重視して実装。

### Breaking Changes
- 初回リリースのため既存利用者向けの破壊的変更はありません。

---

開発に関する詳細（仕様参照ファイル: StrategyModel.md, DataPlatform.md など）や実行時のログ出力を確認してください。将来のリリースでは execution（発注実装）や monitoring（運用・アラート）周りの実装拡張を予定しています。