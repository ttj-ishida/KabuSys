CHANGELOG
=========

すべての注目すべき変更履歴をこのファイルで記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-21
------------------

初回リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ初期化
  - kabusys パッケージのバージョン定義: __version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルの自動ロード機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出: .git または pyproject.toml を親ディレクトリから探索
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能
    - OS 環境変数を保護する protected ロジックを導入（.env.local の上書き制御）
  - .env 行パースの堅牢化
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの取り扱い、無効行のスキップ
  - Settings クラスを提供（環境変数から値を取得）
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）
    - Path を返す DB パス（expanduser 対応）
    - ユーティリティプロパティ: is_live / is_paper / is_dev
  - 未設定の必須変数取得時は ValueError を送出する _require を実装

- Data レイヤー (kabusys.data)
  - J-Quants クライアント (data.jquants_client)
    - API 呼び出しのレート制限 (120 req/min) を固定間隔スロットリングで実装（_RateLimiter）
    - 冪等なページネーション対応フェッチ実装 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar)
    - 再試行ロジック（指数バックオフ、最大 3 回）
      - 再試行対象: ネットワークエラー・408/429/5xx
      - 401 受信時はトークン自動リフレッシュ（1 回のみ）して再試行
    - id_token キャッシュ共有（モジュールレベル）と get_id_token 実装
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
      - ON CONFLICT DO UPDATE を用いた冪等保存
      - fetched_at の UTC 記録（Z 表記）
      - PK 欠損行のスキップと警告ログ
    - HTTP レスポンス JSON パースエラーやネットワークエラーの明確なエラーメッセージ
    - 値変換ユーティリティ: _to_float / _to_int（安全変換、空値・不正値は None）

  - ニュース収集モジュール (data.news_collector)
    - RSS フィードから記事収集し raw_news へ保存するための基盤を実装
    - URL 正規化(_normalize_url): トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 対策）
      - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）
      - トラッキングパラメータの除去定義（utm_ 等）
    - バルク INSERT のチャンク処理、挿入レコード数を正確に返す設計
    - （仕様記述）記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を担保

- Strategy 層 (kabusys.strategy)
  - 特徴量作成 (strategy.feature_engineering)
    - 研究環境で計算した生ファクターを統合し features テーブルへ保存する build_features 実装
    - 処理フロー:
      1. research モジュールの calc_momentum / calc_volatility / calc_value を呼び出し生ファクターを取得
      2. ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
      3. 数値ファクターを zscore 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ
      4. 日付単位の置換（DELETE + バルク INSERT）で冪等性・原子性を確保（BEGIN/COMMIT/ROLLBACK）
    - 入出力: DuckDB 接続を受け取り prices_daily / raw_financials を参照、処理件数を返す
    - ロギングとトランザクションでの失敗時のロールバック/警告対応

  - シグナル生成 (strategy.signal_generator)
    - features と ai_scores を統合して final_score を計算し signals テーブルに出力する generate_signals 実装
    - 計算ロジック:
      - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）
      - コンポーネント内部での処理:
        - Z スコアをシグモイド変換（_sigmoid）
        - PER ベースの value スコア (_compute_value_score)
        - atr_pct を反転して volatility スコア化
        - volume_ratio を流動性スコアへ
      - 欠損コンポーネントは中立値 0.5 で補完
      - デフォルト重みを持ち、外部から weights を与えた際は検証・補完・再スケールを行う
      - BUY 閾値デフォルト: 0.60（_DEFAULT_THRESHOLD）
      - Bear レジーム検出: ai_scores の regime_score 平均が負かつサンプル数が閾値以上の場合、BUY を抑制
    - エグジット判定（SELL シグナル）:
      - 実装済み条件:
        1. ストップロス（終値 / avg_price - 1 < -8%）
        2. final_score が threshold 未満（score_drop）
      - 未実装（要データ）: トレーリングストップ、時間決済（コメントで明記）
    - signals テーブルへの日付単位置換で冪等性を確保
    - 保有銘柄の SELL は BUY 優先度から除外し、BUY のランクは再付与

- Research 層 (kabusys.research)
  - ファクター算出 (research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）を計算する関数を実装
    - DuckDB のウィンドウ関数と集約で実装。データ不足時は None を返す挙動
  - 特徴量探索ユーティリティ (research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 複数ホライズンをまとめて取得可能（ページング・スキャン範囲制限）
    - IC（Information Coefficient）計算 (calc_ic): スピアマンの rho をランク換算して計算（同順位は平均ランク）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算
    - rank ユーティリティ: 同順位の平均ランク計算、round(...,12) による数値丸めで ties 対応

- 共通 / 実装上の注意点
  - DuckDB への書き込みはトランザクション＋バルク挿入で原子性を担保
  - 多くの処理で欠損値や非有限値（NaN/Inf）を明示的に扱い、安全性を高める実装
  - ロギングが各ステップに追加され、警告・情報出力を通じて状況把握が可能
  - 外部への直接発注・execution 層への依存は持たない（戦略層は signals テーブル書込まで）

Fixed
- 初回リリースのため該当なし（実装時に意識した不安定要素はコード内で防御的に扱われている）

Security
- ニュース収集で defusedxml を利用した XML パース（XML Attack 緩和）
- RSS フィード受信サイズ制限、URL 正規化でトラッキングパラメータ除去・SSRF を抑制する設計方針

Known issues / TODO
- signal_generator の一部エグジットルール（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要で未実装
- data.news_collector の記事パース/保存フローは仕様の記述があるが一部実装が断片的（_normalize_url などは実装済だが、完全な取得処理は継続実装が必要）
- zscore_normalize 実装は kabusys.data.stats に依存（別モジュールで提供）
- テスト・CI に関する記載やユニットテストはこのリリースコードベースに含まれていない（別途追加推奨）

Breaking Changes
- 初回リリースのため該当なし

以上。