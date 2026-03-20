# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

- 今後の予定（例）
  - ポジション管理テーブルへの peak_price / entry_date の保存を追加してトレーリングストップ等を実装
  - signals / features 周りの追加バリデーションとモニタリング強化
  - News 集約 -> 銘柄紐付け処理の強化（NLP/エンティティ抽出）

---

## [0.1.0] - 2026-03-20

初期リリース。以下の主要機能・実装方針を含みます。

### Added
- 基本パッケージ構成
  - パッケージルート: kabusys（バージョン: 0.1.0）
  - エクスポート済みモジュール: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）
  - .env パーサ実装（export 構文、クォート・エスケープ、インラインコメント処理対応）
  - Settings クラスによるアプリ設定取得（必須環境変数チェック、デフォルト値、検証）
  - 環境・ログレベルの検証（KABUSYS_ENV, LOG_LEVEL）
  - DB パス設定（duckdb / sqlite のデフォルトパス）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装
    - 固定間隔スロットリングによるレート制限（120 req/min）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）
    - 401 発生時にリフレッシュトークンで id_token を自動更新して再試行
    - ページネーション対応（pagination_key）
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（冪等）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による重複排除
    - fetched_at を UTC で記録（look-ahead bias 対策）
    - 入力値パースユーティリティ（_to_float/_to_int）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集基盤（デフォルトソースに Yahoo Finance を設定）
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、ソート）
  - セキュアな XML パース（defusedxml を利用）
  - SSRF/不正スキーム対策や受信サイズ制限（MAX_RESPONSE_BYTES）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
  - バルク INSERT のチャンク処理とトランザクションまとめ挿入

- 研究モジュール（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
    - momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）
    - volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio
    - value: PER / ROE（raw_financials と prices_daily を結合）
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
    - forward returns の一括取得（LEAD を利用した効率的クエリ）
    - Spearman ランク相関（IC）計算（同順位は平均ランク処理）
    - 基本統計量（count/mean/std/min/max/median）
  - z-score 正規化ユーティリティ（kabusys.data.stats からエクスポート）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを結合・フィルタ・正規化して features テーブルへ保存
  - ユニバースフィルタ実装（最低株価 300 円、20日平均売買代金 >= 5 億円）
  - Z スコア正規化・±3 でクリップ、日付単位での置換（削除→挿入、トランザクションで原子性確保）
  - build_features(conn, target_date) を公開 API として提供

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコアを計算、BUY/SELL シグナルを生成
  - デフォルト重みと閾値を実装（momentum/value/volatility/liquidity/news）
  - シグナル生成フロー実装:
    - コンポーネントスコア計算（シグモイド変換、欠損は中立値 0.5 補完）
    - Bear レジーム判定（AI の regime_score 平均が負で sample 数閾値以上）
    - BUY は閾値超えかつ Bear でない場合、SELL はストップロス（-8%）またはスコア低下
    - SELL 優先ポリシー（SELL の銘柄は BUY から除外）
    - signals テーブルへ日付単位置換（トランザクションで原子性）
  - generate_signals(conn, target_date, threshold, weights) を公開 API として提供

- トランザクション安全性・ログ
  - DB 書き込みは明示的な BEGIN/COMMIT/ROLLBACK で原子性を保護
  - 失敗時の ROLLBACK の失敗を警告ログに出力
  - 多数の箇所で詳細な logging（info/debug/warning）

### Changed
- 初期リリースのため該当なし（以降のリリースで差分を記載）

### Fixed
- 初期リリースのため該当なし

### Security
- news_collector で defusedxml を利用することで XML 関連の攻撃（XML Bomb 等）を緩和
- ニュース URL 正規化とトラッキングパラメータ削除により、追跡パラメータによる差異や DoS を軽減
- J-Quants クライアントでタイムアウト・リトライ制御を導入し、過剰リトライやレート超過のリスクを低減

---

開発メモ / 設計上の注意点
- ルックアヘッドバイアス対策のため、各処理は target_date 時点で利用可能なデータのみを参照する設計を採用
- 外部依存は最小化（DuckDB と defusedxml 等必要最小限）し、research モジュールは本番の発注ロジックへ依存しない
- 将来的には positions テーブルの拡張（peak_price / entry_date）やニュースの銘柄紐付け精度向上を計画

もし追加で「各関数の引数/戻り値の詳細」や「想定される DB スキーマ（tables）一覧」を CHANGELOG に追記したい場合は、その旨を教えてください。