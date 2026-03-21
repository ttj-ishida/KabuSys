CHANGELOG
=========

すべての注目すべき変更は Keep a Changelog の形式に従って記載しています。  
このファイルは日本語での説明を目的としています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-21
--------------------

Added (追加)
- 初回リリース: パッケージ kabusys を追加。__version__ = "0.1.0" を設定。
- パッケージ構成: data (J-Quants / news), research (factor 計算・探索), strategy (feature engineering / signal generation)、execution、monitoring などのモジュールを含む。
- 環境設定:
  - .env / .env.local を自動ロードする設定ローダを追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パース機能を実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - Settings クラスを提供。J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境（development/paper_trading/live）やログレベル検証、便宜判定プロパティ（is_live/is_paper/is_dev）を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）:
  - 固定間隔スロットリングによるレート制限管理（120 req/min）。
  - リトライ（指数バックオフ、最大 3 回）と再試行対象ステータスの管理（408/429/5xx）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar）：ON CONFLICT DO UPDATE を使用。
  - 取得時刻を UTC で記録（fetched_at）。
  - ネットワーク/HTTP エラー時の詳細ログと警告。
- ニュース収集モジュール（kabusys.data.news_collector）:
  - RSS フィードから記事収集し raw_news へ冪等保存する実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を利用した XML パース（XML Bomb 対策）、受信サイズ上限（MAX_RESPONSE_BYTES）などの安全対策。
  - HTTP スキーム検証や SSRF を意識した設計、バルク挿入チャンク処理、挿入数の正確な返却。
- 研究（research）モジュール:
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials のみを参照してファクター（モメンタム/ボラティリティ/バリュー等）を計算。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関＝IC）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せず標準ライブラリで実装。
  - パフォーマンス配慮（スキャンレンジのバッファ、1 クエリで複数ホライズン取得 等）。
- 戦略（strategy）モジュール:
  - feature_engineering.build_features:
    - research 側で計算した生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）適用。
    - 指定カラムを Z スコア正規化（zscore_normalize）し ±3 でクリップ。
    - 日付単位での置換（DELETE + INSERT）をトランザクションで実行し冪等性・原子性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネント（momentum/value/volatility/liquidity/news）ごとにスコアを計算して final_score を生成。
    - デフォルト重みと閾値（デフォルト BUY 閾値 0.60）を実装。ユーザー重みの検証・補完・再スケーリング機能を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）で BUY を抑制するロジック。
    - エグジット判定（ストップロス -8% / final_score の閾値割れ）に基づく SELL シグナル生成。
    - SELL 優先ポリシー（SELL 対象を BUY から除外）と日付単位のトランザクション置換で signals テーブルを更新。
    - 欠損や異常値に対する安全措置（None の補完、中立値補完、ログ警告）。
- DB / トランザクション設計:
  - 各書き込み処理はトランザクションでバルク挿入・DELETE を行い原子性を確保。ROLLBACK 失敗時に警告出力。
- ユーティリティ:
  - z-score 正規化は kabusys.data.stats として統一（research/__init__ で再エクスポート）。
  - 型変換ユーティリティ（_to_float / _to_int）の堅牢化（空文字/None の扱い、"1.0" 形式数値の扱い等）。

Changed (変更)
- 設計上の方針を明文化:
  - ルックアヘッドバイアス防止のため、target_date 時点のデータのみを使用する方針を各モジュールで採用。
  - 発注/実行層（execution）への直接依存を持たない層分離（strategy/research/data を分離）。
  - DuckDB を用いたローカルデータベース中心の処理フローを確立。

Fixed (修正)
- .env パーサ: export プレフィックス対応、クォート内エスケープ対応、インラインコメント判定ルールの改善により .env の誤解析を低減。
- _to_int: "1.0" のような float 文字列を float 経由で整数化する際、小数部が 0 以外なら None を返すようにし、不正な丸めを回避。

Security (セキュリティ)
- news_collector は defusedxml を使用し XML の危険な入力から保護。
- ニュース取得時の受信サイズ上限設定（メモリ DoS 対策）。
- URL 正規化およびスキーム検証により SSRF リスクを低減する設計注記。
- J-Quants クライアントはトークンリフレッシュとキャッシュ、リトライポリシーを明示し、Retry-After ヘッダ優先処理等で API 過負荷への耐性を強化。

Notes / Known limitations (注意・未実装)
- signal_generator のエグジット条件:
  - トレーリングストップ（peak_price に対する -10%）や保有日数による時間決済（60 営業日超）等は未実装（positions テーブルに peak_price / entry_date が必要）。
- 一部の機能は research 環境（外部データ前提）の補助を想定しており、本番発注ロジック（execution 層）とは分離されている。
- news_collector の SSRF 完全防御や外部 URL の厳格検査は実装方針に沿った注記があるが、実稼働では追加のネットワーク制御（プロキシ・IP 拒否等）を推奨。

作者情報
- 内部コードコメントに各関数の設計目的と副作用が記載されています。詳細は各モジュールの docstring を参照してください。