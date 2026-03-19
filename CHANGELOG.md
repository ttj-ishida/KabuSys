# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※この CHANGELOG はソースコードの内容から実装・仕様を推測して作成しています。

## [Unreleased]

- 今後のリリースで検討すべき項目（コード内コメントより推測）
  - positions テーブルに peak_price / entry_date を追加してトレーリングストップ等のエグジット条件を実装
  - news_collector の記事 ID 生成（URL 正規化後の SHA-256 ハッシュ）や記事→銘柄紐付け処理の実装完了
  - execution / monitoring パッケージの実装強化（現時点ではパッケージのプレースホルダのみ）

---

## [0.1.0] - 2026-03-19

Added
- パッケージ初期リリース（kabusys v0.1.0）
  - 全体構成: data, research, strategy, execution, monitoring を想定したモジュール構成を導入
  - __version__ を "0.1.0" に設定

- 設定管理 (.env / 環境変数)
  - プロジェクトルート自動検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索する実装を追加（CWD に依存しない挙動）
  - .env 及び .env.local 自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用想定）
  - .env パーサを強化:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの扱い（クォートなしでは '#' の直前が空白・タブのときコメント扱い）
  - Settings クラスで必須環境変数取得をラップ（未設定時は ValueError）
  - 各種プロパティを追加:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - duckdb/sqlite のデフォルトパス（Path 型で返す）
    - KABUSYS_ENV の検証（development/paper_trading/live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティ

- Data: J-Quants API クライアント
  - API 呼び出しユーティリティ (_request) を実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 受信時は ID トークン自動リフレッシュ（1 回のみ）して再試行
    - ページネーション対応（pagination_key）
    - JSON デコードエラー時の明示的なエラー報告
  - get_id_token 実装（リフレッシュトークン → ID トークン）
  - fetch_* 系のデータ取得関数を提供:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - DuckDB への保存関数を追加（冪等性を考慮した実装）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使用して保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE を使用して保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE を使用して保存
  - 保存時の fetched_at は UTC ISO8601 形式で記録
  - 型変換ユーティリティ: _to_float / _to_int（不正値や空文字列を None に変換、"1.0" 等の扱いを明示）

- Data: news_collector（ニュース収集）
  - RSS フィード収集基盤を追加（デフォルトソースに Yahoo Finance を設定）
  - URL 正規化 (_normalize_url):
    - スキーム/ホストの小文字化、トラッキングパラメータ削除（utm_ 等）、フラグメント除去、クエリパラメータをソート
  - セキュリティと堅牢性への配慮（モジュールコメントより実装方針を反映）:
    - defusedxml を用いた XML パース想定（XML Bomb 等の緩和）
    - 最大受信バイト数制限 (MAX_RESPONSE_BYTES = 10MB)
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE = 1000）で SQL/パラメータ数上限対策
    - PK 欠損行のスキップとログ出力

- Research: ファクター計算・探索
  - factor_research モジュールを実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均の存在チェック）
    - calc_volatility: 20 日 ATR（true range の NULL 伝播制御）、atr_pct / avg_turnover / volume_ratio
    - calc_value: raw_financials と prices_daily を組み合わせた per / roe（最新報告の取得）
    - 計算期間バッファと営業日→カレンダー日変換の考慮
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得、horizons の妥当性検証
    - calc_ic: Spearman の ρ（ランク相関）計算（ties は平均ランクで処理、有効レコード < 3 は None）
    - rank: 丸め (round(..., 12)) による tie 検出耐性を組み込んだランク変換
    - factor_summary: count/mean/std/min/max/median を計算（None 除外）

- Strategy: 特徴量作成・シグナル生成
  - feature_engineering.build_features:
    - research モジュールの calc_* を組み合わせて features テーブルを作成
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize の利用）、±3 でクリップ
    - 日付単位での置換（DELETE → INSERT をトランザクションで実施して冪等性保証）
  - signal_generator.generate_signals:
    - features テーブルと ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - 各コンポーネントにシグモイド変換を適用、None のコンポーネントは中立 0.5 で補完
    - weights の入力チェックとフォールバック／再スケール処理（未知キー・非数値・負値は無視）
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）
      - Bear レジーム時は BUY シグナルを抑制
    - BUY: threshold（デフォルト 0.60）超過銘柄を順位付けして生成
    - SELL: positions テーブル（最新ポジション）と最新価格を参照してストップロス（-8%）やスコア低下で判定
      - 価格欠損時は SELL 判定をスキップ（誤クローズ防止のため）
      - positions に該当するが features に存在しない銘柄は score=0.0 扱いで SELL の対象とする
    - SELL を優先して BUY から除外し、signals テーブルへ日付単位置換で保存（トランザクションで冪等性保証）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- news_collector 想定で defusedxml の利用や受信サイズ上限の設計が盛り込まれており、安全な RSS パースを考慮
- J-Quants クライアントでトークンリフレッシュ・再試行制御を実装し、不正片方のエラーで無限再帰しないよう設計

Performance
- J-Quants API クライアントに固定間隔レートリミットを導入（API レート制限順守）
- DB へのバルク挿入をチャンク化してオーバーヘッドを抑制

Notes
- 多くの DB 操作は DuckDB 接続を引数に受け取り SQL を直接実行する設計。tests／運用での DuckDB スキーマ整備が前提。
- execution / monitoring モジュールは名前空間のみ存在（実装の追加が今後の課題）。
- コメント・設計ノートにより、将来的に追加すべき機能（トレーリングストップ、時間決済、ニュース→銘柄紐付けの強化 等）が明示されている。

---

過去のバージョン履歴はありません（本 CHANGELOG は初回リリースに対応）。