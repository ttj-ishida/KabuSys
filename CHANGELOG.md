# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
慣例: 変更は「Added / Changed / Fixed / Security / Removed / Deprecated」等のカテゴリで整理します。

最新リリース
------------

[0.1.0] - 2026-03-19
^^^^^^^^^^^^^^^^^^^^^^
初回公開リリース。以下の主要機能と設計方針を実装しました。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、主要モジュールを __all__ に公開）。
- 環境変数 / 設定管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 高度な .env パース:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートの有無での挙動差分）。
  - Settings クラス:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティ（必須値は _require で検証）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値を限定）。
    - デフォルトの DB パス（duckdb/sqlite）や環境判定ユーティリティ（is_live / is_paper / is_dev）。
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - 固定間隔の RateLimiter（120 req/min 想定）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）。
    - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - 冪等性を確保するため ON CONFLICT (upsert) を使用。
      - PK 欠損行のスキップとログ警告。
    - ユーティリティ関数: 安全な型変換 _to_float / _to_int（不正値を None に変換）。
  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィードの収集・正規化・保存処理。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリパラメータソート。
    - defusedxml による安全な XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）などの安全対策。
    - DB へバルク挿入のチャンク化（パフォーマンス・制約対策）。
    - デフォルト RSS ソースを一つ（Yahoo Finance business）に設定。
- 研究（research）モジュール
  - ファクター計算（research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials を参照して計算。
    - ウィンドウ長やスキャン範囲に関する定数を定義し、週末・祝日を吸収するスキャンバッファを採用。
    - 欠損やデータ不足時は None を返す設計。
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得、horizons の検証）。
    - スピアマンランク相関による IC（calc_ic）とランク変換ユーティリティ rank（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）の算出。
  - research パッケージの公開 API を整備（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。
- 特徴量エンジニアリング（strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装:
    - research モジュールから生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（削除→挿入、トランザクションで原子性保証）。
    - logger による処理件数ログ出力。
- シグナル生成（strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features / ai_scores / positions を参照して最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を算出するユーティリティを実装（_sigmoid, _avg_scores, _compute_*）。
    - 重みのマージ・検証（不正値をスキップし合計が 1.0 になるようにリスケール、デフォルト重みを定義）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負のとき。ただしサンプル数が閾値未満なら Bear と判定しない）。
    - BUY シグナルは閾値超過の銘柄に付与（Bear 時は抑制）。
    - SELL シグナル（エグジット）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満の場合。
      - SELL は BUY より優先し、signals テーブルへ日付単位で置換保存（トランザクション）。
    - logger による集計ログ出力。
- strategy パッケージの公開関数（build_features, generate_signals）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサに defusedxml を使用、URL 正規化・スキームチェック、受信サイズ上限などで潜在的な SSRF / XML Bomb / DoS に対処する設計を採用。

Notes / Implementation details
- DuckDB を中心に SQL ウィンドウ関数を多用した実装（速度と簡潔さを優先）。
- ルックアヘッドバイアスを避ける設計:
  - feature や signal の計算は target_date 時点の入手可能データのみを利用する。
  - J-Quants 取得時は fetched_at を UTC タイムスタンプで保存して「いつデータを知り得たか」を追跡可能にする。
- 冪等性を重視:
  - DB 保存は upsert（ON CONFLICT）や date 単位の置換を採用。
  - ニュース記事 ID は正規化 URL のハッシュ化で一意化。

既知の制限 / TODO（ドキュメント化されたもの）
- signal_generator のエグジット条件において、トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理で pandas 等の外部ライブラリ導入を検討する余地あり。

過去のリリース
----------------
- なし（初回リリース）

今後の予定（例）
- トレーリングストップ / 時間決済の実装（positions 拡張）。
- AI ニューススコアの取得パイプライン強化。
- モニタリング・実行層（execution / monitoring）の実装と統合テスト整備。