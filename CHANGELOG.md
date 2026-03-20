CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマットの詳細: https://keepachangelog.com/（英語）

Unreleased
----------

なし

[0.1.0] - 2026-03-20
--------------------

Initial release — 日本株自動売買システム "KabuSys" の初期公開リリース。

Added
- パッケージ構成
  - kabusys パッケージの初期モジュールを追加。
  - エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 環境変数取得ユーティリティ _require と Settings クラスを実装。J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル等のプロパティを提供。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）。
  - リトライロジック: 指数バックオフ、最大 3 回（408/429/5xx 対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 対応: id_token を自動リフレッシュして 1 回リトライ。
  - ページネーション対応の取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を利用）。
  - データ変換ユーティリティ: _to_float / _to_int（安全な変換と欠損ハンドリング）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを追加（デフォルトで Yahoo Finance のビジネス RSS を参照）。
  - セキュリティ対策: defusedxml による XML パース、HTTP スキームの検証、受信サイズ上限（10MB）などを実装。
  - URL 正規化: トラッキングパラメータの除去、クエリソート、フラグメント削除。記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を担保。
  - DB へのバルク挿入を想定したチャンク処理とトランザクション設計。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム / ボラティリティ / バリュー系のファクター計算を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日窓）。
    - calc_value: per, roe（raw_financials から最新財務を取得して株価と組合せ）。
  - 取扱い: データ不足時は None を返す、DuckDB の SQL ウィンドウ関数を活用。

- 研究用探索ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算: calc_forward_returns（複数ホライズンに対応、入力検証あり）。
  - IC（Information Coefficient）計算: calc_ic（スピアマン ρ をランク計算で実装、サンプル数 3 未満は None）。
  - ランク関数: rank（同順位は平均ランク、丸め処理で ties の誤検出を抑制）。
  - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールの生ファクターを取得しマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみ使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き合算（デフォルト重みを定義）し閾値（デフォルト 0.60）超過で BUY シグナルを生成。
    - Bear レジーム検知（AI の regime_score 平均が負かつサンプル数閾値以上で BUY を抑制）。
    - 保有ポジションに対するエグジット判定（ストップロス -8% およびスコア低下）で SELL シグナルを生成。
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換で保存。
    - weights の受け取り時は検証（未知キー無視、負値/非数を除外）、合計が 1.0 でない場合はスケーリング。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- news_collector で defusedxml を使用し XML 関連攻撃に対処。
- ニュースの受信時に最大受信バイト数を設定してメモリDoSを軽減。
- J-Quants クライアントは認証トークンを安全に扱い、401 発生時にのみトークン更新を行うことで無限再帰を回避。

Notes / Implementation details
- DuckDB を主要なデータストアとして設計（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等を想定）。
- 研究モジュールは外部 API に依存せず、DuckDB のテーブルのみを参照する方針。
- 一部ユーティリティ（zscore_normalize 等）は kabusys.data.stats に委譲しており、当リリースではそれらと連携することを前提としている。
- 自動環境読み込みはプロジェクトルート探索に基づくため、パッケージ配布後も CWD に依存せず動作する設計。

Compatibility / Breaking changes
- 初期リリースのため適用対象なし。

Acknowledgements
- このリリースはデータ収集・前処理・研究・シグナル生成の基本機能を含む最小実装として提供します。今後、execution（発注）や監視／運用に関する追加実装・テスト・改善を予定しています。