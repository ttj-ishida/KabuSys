Changelog
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

  - 設定・環境変数管理 (src/kabusys/config.py)
    - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パース処理の強化（export プレフィックス対応、クォートとエスケープ処理、行内コメントの扱い）。
    - OS 側の既存環境変数を保護する protected 機能。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / システム設定（env, log_level）などをプロパティで取得。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値チェック）。

  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - RateLimiter による固定間隔スロットリング実装（120 req/min を想定）。
    - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx のリトライ）を追加。
    - 401 受信時の ID トークン自動リフレッシュ（1回のみ）を実装。
    - ページネーション対応の fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
    - DuckDB への冪等保存ユーティリティを実装（ON CONFLICT DO UPDATE を用いた save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 取得時刻を UTC で記録（fetched_at）して look-ahead バイアスのトレーサビリティを確保。
    - 数値変換ユーティリティ _to_float / _to_int を実装（安全なパースと不正値の None 化）。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードから記事を収集し raw_news へ冪等保存する基盤を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成する方針を採用。
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃を緩和。
    - HTTP レスポンスの最大受信バイト数制限（MAX_RESPONSE_BYTES, 10MB）を実装してメモリ DoS を軽減。
    - URL 正規化機能（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - SSRF 等軽減のため不正なスキームや受信先 IP の制限を意識した実装設計（コード内に該当チェックあり）。
    - バルク INSERT のチャンク処理、および INSERT RETURNING を想定した設計。

  - 研究系モジュール (src/kabusys/research/)
    - ファクター計算: calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）
      - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離率）
      - Volatility: 20日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio
      - Value: per, roe（raw_financials から target_date 以前の最新財務データを参照）
      - DuckDB のウィンドウ関数を利用した効率的な集計。
    - 特徴量探索ツール (src/kabusys/research/feature_exploration.py)
      - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターン計算（LEAD を利用）。
      - calc_ic: スピアマン順位相関 (Information Coefficient) の計算（欠損・サンプル数チェックを含む）。
      - factor_summary: 複数ファクター列の基本統計量（count/mean/std/min/max/median）。
      - rank: 同順位は平均ランクを返すランク関数（丸め処理で ties の誤検出を防止）。
    - research パッケージの __init__ で主要関数をエクスポート。

  - 特徴量生成 / 戦略 (src/kabusys/strategy/)
    - feature_engineering.build_features
      - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
      - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
      - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
      - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。
    - signal_generator.generate_signals
      - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - final_score を重み付け合算（デフォルト重みを定義、ユーザー指定 weights は検証・正規化）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
      - BUY シグナル閾値（デフォルト 0.60）。SELL 判定はストップロス（-8%）とスコア低下を実装。
      - 保有ポジションに対するエグジット判定は positions / prices_daily を参照し、SELL を生成。
      - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
      - 無効な weights 指定や欠損データに対する安全策（警告ログ、欠損項目は中立 0.5 で補完）を実装。

  - モジュール構成
    - strategy/__init__.py で build_features, generate_signals を公開。
    - research/__init__.py で主要研究関数を公開。
    - execution パッケージ（src/kabusys/execution）は空のプレースホルダとして存在。

Changed
- 設計方針に関する注記（コード内ドキュメント）
  - ルックアヘッドバイアス防止、冪等性の確保、DuckDB を前提とした SQL + Python 実装方針を明確化。
  - DB 書き込みは日付単位で置換することで冪等性と原子性を担保（トランザクション + bulk insert）。
  - 外部 API 呼び出しコードはレート制御・リトライ・トークン管理を内包。

Security
- news_collector で defusedxml を使用し XML パースの安全性を向上。
- news_collector にて受信サイズ制限（MAX_RESPONSE_BYTES）を実装しメモリ DoS を軽減。
- URL 正規化とトラッキングパラメータ削除により記事同一性の判定を安定化。
- J-Quants クライアントでのタイムアウト/例外処理・再試行により予期せぬ外部エラー耐性を向上。

Known issues / Notes
- signal_generator の SELL 判定における「トレーリングストップ（peak_price に基づく）」および「時間決済（保有日数ベース）」は未実装。positions テーブルに peak_price / entry_date が必要であり将来の拡張課題として記載。
- news_collector のソース一覧は DEFAULT_RSS_SOURCES にデフォルトを持つが、外部設定や拡張は今後強化可能。
- execution / monitoring パッケージは公開 API に含まれているが、本バージョンでは実装が薄い／プレースホルダ。
- 一部関数・処理は設計文書（StrategyModel.md, DataPlatform.md 等）に依存した仕様に基づく実装。仕様変更は互換性に影響を与える可能性あり。

--------------------------------
参考: バージョニングはセマンティックバージョン（SemVer）に準拠。