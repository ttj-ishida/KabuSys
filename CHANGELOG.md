Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の規約に概ね準拠しています。

フォーマット
-----------
- バージョン順（最新 → 古い）
- セクション: Added / Changed / Deprecated / Removed / Fixed / Security

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
- パッケージ構成:
  - kabusys.config: 環境変数・設定管理（.env 自動ロード、プロジェクトルート検出、必須キー検査）。
    - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式、クォート、インラインコメント等に対応する堅牢なパース実装。
    - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベル検証プロパティを提供。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - kabusys.data.jquants_client: J-Quants API クライアント。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 応答時はリフレッシュトークンを用いた自動トークン更新を 1 回実行して再試行。
    - ページネーション対応（pagination_key を使用して全件取得）。
    - データ保存関数（save_daily_quotes/save_financial_statements/save_market_calendar）: DuckDB への冪等保存（ON CONFLICT / DO UPDATE）を実装。
    - 型変換ユーティリティ (_to_float/_to_int) を実装。
  - kabusys.data.news_collector: RSS ニュース収集。
    - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）、URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
    - データ保存はバルクチャンク（デフォルト 1000 件）で処理し、冪等性・効率を確保。
  - kabusys.research: 研究用ファクター計算・解析モジュール。
    - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials に依存）。
      - Momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
      - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
      - Value: PER / ROE（target_date 以前の最新財務データを使用）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary、rank（同順位の平均ランク）。
    - research パッケージから主要ユーティリティを再エクスポート。
  - kabusys.strategy:
    - feature_engineering.build_features: research モジュールで作成した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）、Z スコア正規化、±3 クリップ、features テーブルへ日付単位の置換（トランザクションで原子性保証）。
    - signal_generator.generate_signals: features と ai_scores を統合して final_score を計算、Bear レジーム判定による BUY 抑制、BUY/SELL シグナル生成、signals テーブルへ日付単位の置換（冪等）。
      - デフォルト重み・閾値を提供（momentum/value/volatility/liquidity/news、閾値 0.60）。
      - スコア計算時の不正入力（NaN/Inf/負値等）やユーザー指定重みの検証・正規化を実装。
      - SELL 条件にストップロス（-8%）とスコア低下を実装。SELL 優先で BUY から除外。
- パッケージ初期化とエクスポート（kabusys.__init__）: バージョン文字列と公開モジュール一覧。

Changed
- n/a（初回リリースのため既存変更なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Deprecated
- n/a

Removed
- n/a

Security
- news_collector で defusedxml を使用し XML ボム等を防止。
- URL 検証（HTTP/HTTPS 限定）と受信サイズ制限により SSRF / メモリ DoS のリスク低減。
- jquants_client のトークン/リトライ処理で認証失敗や異常レスポンスに対する堅牢化。

Notes / Implementation details
- DuckDB を中心に設計されており、全ての「研究 / データ処理 / シグナル生成」ロジックは prices_daily / raw_* テーブルに対して完結する（発注 API への直接依存を回避）。
- ルックアヘッドバイアス対策として、各処理は target_date 時点で利用可能なデータのみを参照する設計方針を採用。
- トランザクション + バルク挿入により、features/signals 等のテーブル更新は日付単位で置換（冪等性・原子性）を確保。

開発者向け
- 自動環境ロードはプロジェクトルート検出（.git または pyproject.toml）が前提。配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- 設定値に不足がある場合は Settings のプロパティが ValueError を投げるため、CI/運用時に環境変数のチェックを推奨。

今後の予定（例）
- PBR や配当利回りなどのバリューファクター拡張。
- トレーリングストップや時間決済などの追加のエグジット条件実装（signal_generator の未実装項目に言及）。
- ニュースと銘柄の自動紐付け（news_symbols）および AI スコアとの統合強化。

-----