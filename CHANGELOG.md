CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
このファイルではリリースごとの重要な追加・変更・修正点を日本語でまとめています。

Unreleased
----------

- （次回リリース用の未確定変更はここに記載します）

0.1.0 - 2026-03-20
------------------

初回公開リリース。主要機能、設計方針、及び各モジュールで実装された振る舞いをまとめます。

Added
- パッケージの基本構成を追加
  - kabusys パッケージ初期バージョン（__version__ = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring が __all__ に登録。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 無効行のスキップ、読み込み失敗時の警告出力。
    - override / protected オプションで既存OS環境変数の保護が可能。
  - Settings クラス:
    - 必須設定の検査（_require）とプロパティ提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
    - 型変換（Path）や値検証（KABUSYS_ENV の許容値、LOG_LEVEL 検査）を実装。
    - is_live / is_paper / is_dev の便宜プロパティあり。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔レートリミッタ（120 req/min）を実装(_RateLimiter)。
    - 汎用リクエスト処理: ページネーション対応、JSON デコード、タイムアウト、リトライ（指数バックオフ、最大 3 回）。
    - レスポンスで 401 を受けた場合は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止ロジックあり）。
    - 408/429/5xx に対するリトライ、429 の Retry-After を尊重。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供（ページネーション対応）。
    - save_* 系関数: raw_prices/raw_financials/market_calendar へ冪等保存（DuckDB に対して ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ: _to_float, _to_int（文字列や不正値に耐性を持たせる実装）。
    - ページネーション中に共有するためのモジュールレベルの ID トークンキャッシュ。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news へ保存する仕組みの基礎を実装（設計・ユーティリティ）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）を実装。
    - defusedxml を使った安全な XML パースを想定し、XML Bomb 等の対策を考慮。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、チャンク挿入サイズ、記事ID のハッシュ化等の設計方針を明示。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を指定。

- リサーチ / ファクター計算（kabusys.research.*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR, atr_pct, 20日平均売買代金, 出来高比率を計算。true_range の NULL 伝播制御を含む。
    - calc_value: raw_financials と当日株価から PER/ROE を算出（最新財務レコードを report_date <= target_date から拾う）。
    - 各関数は prices_daily/raw_financials のみ参照し、結果を (date, code) ベースの dict リストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する高速 SQL 実装。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）計算。サンプル不足時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）計算を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）等のユーティリティも再公開。

- 戦略（kabusys.strategy.*）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum/volatility/value）を取得・マージし、
      ユニバースフィルタ（最小株価・最小売買代金）を適用。
    - 数値ファクターを Z スコア正規化（zscore_normalize）、±3 でクリップし、features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 休場日や当日欠損に対応するため、target_date 以前の最新価格を参照する実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して最終スコア（final_score）を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティを実装（シグモイド変換、欠損は中立 0.5 補完）。
    - 重みの受け入れと正規化ロジック（未知キー/無効値の無視、合計が 1.0 でない場合のリスケーリング）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル十分時に BUY を抑制）。
    - BUY シグナルは閾値（デフォルト 0.60）以上で生成、SELL はストップロス（-8%）およびスコア低下で判定。
    - positions/prices_daily/features/ai_scores を参照し、SELL 対象は BUY から除外。signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ROLLBACK 失敗時には警告ログを出力する防御的実装。

Changed
- n/a（初回リリースのため履歴なし）

Fixed
- n/a（初回リリースのため履歴なし）

Security
- ニュース収集で defusedxml を利用する方針を明記し、RSS/XML の安全な取り扱いを意識（XML Bomb 等の対策）。
- ニュース URL の正規化によりトラッキングパラメータを除去し、一貫した記事 ID を生成（冪等性の向上）。
- J-Quants クライアントのネットワークエラー・HTTP エラーに対する堅牢なリトライ・トークンリフレッシュ実装により失敗時の情報漏洩や不整合を低減。

Notes / Implementation details
- Look-ahead bias の防止:
  - research/strategy レイヤーは target_date 時点のデータのみを使用する設計。
  - J-Quants クライアントは fetched_at を UTC で記録し、データ取得時刻をトレース可能にする。
- 冪等性:
  - DuckDB への保存処理は ON CONFLICT DO UPDATE や日付単位の DELETE→INSERT トランザクションで置換するなど、再実行可能な操作を心がけている。
- ロギング:
  - 主要処理は logger を通じて情報・警告・デバッグを出力。トランザクション失敗時には ROLLBACK の失敗を警告。

Acknowledgements / References
- 各モジュール内の docstring に設計方針や StrategyModel.md / DataPlatform.md 等の参照を記載（実装仕様の根拠）。

今後の予定（例）
- ニュース抽出のパーシング部分（HTML→テキスト変換）・銘柄マッチングロジックの実装。
- 実運用用 execution 層（kabu ステーション連携）やモニタリング機能の実装強化。
- 単体テスト・統合テストの追加、およびドキュメント整備。

---
この CHANGELOG はコード内容（docstring と実装）に基づいて作成しています。記載内容で不明点や詳細化したい箇所があれば教えてください。