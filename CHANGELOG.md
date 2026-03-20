CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティック・バージョニングを想定しています。

v0.1.0 - 2026-03-20
-------------------

初回リリース。以下の主要機能と実装方針を含みます。

Added
- パッケージ初期化
  - kabusys パッケージを導入。__version__ = "0.1.0"、公開 API として data/strategy/execution/monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に検索（パッケージ配布後も動作するように __file__ を起点に探索）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト時に便利）。
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - コメント処理（クォート外の # を考慮）など。
  - Settings クラスを提供し、必須値取得時に未設定であれば ValueError を送出する _require を実装。
  - デフォルト値や検証を持つプロパティ:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）など
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- Data クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter。
    - 冪等性のため DuckDB への保存関数で ON CONFLICT DO UPDATE を使用（raw_prices / raw_financials / market_calendar）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象に 408/429/5xx を含める。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
    - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間で共有。
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（欠損 PK 行のスキップとログ出力、保存件数のログ）。
    - JSON レスポンスのデコードエラーやネットワークエラーに対する明示的なエラー処理。
    - 入力変換ユーティリティ: _to_float / _to_int（エッジケースを考慮）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集の基盤を実装。
    - デフォルト RSS ソース定義（例: Yahoo Finance）。
    - URL 正規化とトラッキングパラメータ除去機能（utm_*, fbclid 等の除去、クエリソート、フラグメント削除）。
    - defusedxml を使った安全な XML パース（XML Bomb 対策など）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - 記事 ID として正規化後の SHA-256 ハッシュ等を想定（設計方針に記載）。
    - DB への冪等保存設計（ON CONFLICT DO NOTHING）やバルク挿入チャンク制御。

- 研究ユーティリティ (kabusys.research)
  - ファクター計算・探索用モジュール一式を実装。
    - factor_research: calc_momentum / calc_volatility / calc_value
      - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA を使用、データ不足時は None）
      - Volatility: 20 日 ATR（true_range の計算で high/low/prev_close の NULL 伝播を適切に制御）、atr_pct、avg_turnover、volume_ratio
      - Value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials の最新レコードを採用）
      - 各関数は prices_daily / raw_financials のデータのみを参照し、結果は (date, code) キーの dict リストで返す。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。ホライズン検証（正の整数かつ <= 252）。
      - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランク、有効レコードが 3 未満なら None）。
      - factor_summary: 各カラムに対する count/mean/std/min/max/median の計算。
      - rank: 丸めによる ties の扱い（round(v, 12)）を含む平均ランク化の実装。
  - 研究モジュールは pandas 等外部ライブラリに依存せず、標準ライブラリ＋DuckDB SQL で実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで計算した生ファクターを取り込み、features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円（_MIN_PRICE/_MIN_TURNOVER）。
    - 正規化: zscore_normalize を利用して指定カラムを Z スコア正規化（対象カラム mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。
    - クリップ: Z スコアを ±3 でクリップして外れ値影響を抑制。
    - 原子性: 対象日を DELETE してから INSERT（トランザクション + バルク挿入）することで日付単位での置換（冪等性）。
    - ルックアヘッドバイアス回避の方針をコメントに明記（target_date 時点のデータのみ使用）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を計算し、signals テーブルへ書き込む generate_signals を実装。
    - デフォルト重みと閾値:
      - デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - デフォルト BUY 閾値 = 0.60
    - コンポーネントスコア算出:
      - momentum: momentum_20/60 と ma200_dev をシグモイドで変換して平均
      - value: PER を 1/(1 + per/20) でスケール（per が無効なら None）
      - volatility: atr_pct の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio をシグモイド変換
      - news: ai_score をシグモイド変換（未登録は中立）
    - 欠損値の扱い: コンポーネントが None の場合は中立値 0.5 で補完（欠損銘柄の不当な降格を防ぐ）
    - Bear レジーム検出: ai_scores の regime_score の平均が負なら Bear（ただしサンプル数が最小値未満なら判定しない）
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score が threshold 未満
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - 最終的に signals テーブルへ日付単位の置換で書き込み（トランザクション + バルク挿入、SELL 優先ポリシーで BUY から除外）
    - ユーザ渡しの weights は妥当性検証（未知キー/非数値/負値/NaN/Inf を除外）して合計を 1 に正規化、異常値時はデフォルトにフォールバック。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を採用し XML 関連の脆弱性を軽減。
- news_collector で受信サイズ制限を導入（MAX_RESPONSE_BYTES）。
- jquants_client の URL 呼び出し・JSON 処理で例外ハンドリングを強化。

Notes / Implementation details
- DuckDB を中心としたデータパイプライン設計（raw_* テーブル → features → signals）を前提とした実装。
- 多くの DB 書き込み処理はトランザクションで包み、日付単位での置換（冪等）を保証。
- 各モジュールに詳細な設計方針・コメントを付与し、ルックアヘッドバイアス回避や本番 API 依存排除等のガイドラインを明記。
- ロギングを随所に設置し、警告・情報を出力することで運用時の可観測性を高める。

Known limitations / TODO
- signal_generator の一部エグジット条件（例: トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の記事 ID 生成 / シンボル紐付け（news_symbols）等は設計方針がありつつ、詳細実装の完成度は今後の改善対象。
- 一部の入力検証やエッジケース（非常に少ないサンプル数や極端な外れ値）に対する追加テストが望ましい。

Breaking Changes
- なし（初回リリース）

Authors
- プロジェクト内の各モジュールに豊富な実装コメントと設計方針を含めています。今後の変更は本 CHANGELOG に追記します。