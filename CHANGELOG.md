Keep a Changelog に準拠した形式で、このコードベースの初期リリース（v0.1.0）相当の変更履歴を推測して作成しました。各モジュールの実装方針や重要な挙動、既知の制限も併記しています。

CHANGELOG.md

All notable changes to this project will be documented in this file.

格式: https://keepachangelog.com/ja/1.0.0/

Unreleased
- （なし）

[0.1.0] - 2026-03-19
Added
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
    - パブリック API: data, strategy, execution, monitoring（execution/monitoring は名前空間のみ）
- 環境設定 / 設定読み込み (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により、CWD に依存しない読み込みを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト時の制御向け）。
  - .env パーサ実装:
    - コメント行・空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ '#' をコメントとして扱う）。
  - Settings クラスを実装。J-Quants トークン、kabu API 設定、Slack 設定、データベースパス、環境名（development/paper_trading/live）やログレベルの検証を提供。
  - 必須環境変数未設定時は ValueError を送出する _require 実装。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とキャッシュ化（モジュールレベルの ID トークンキャッシュ）。
    - ページネーション対応 fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - JSON デコード失敗やネットワークエラーに対する例外ハンドリング。
  - DuckDB への保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等保存。
    - 値の安全な変換ユーティリティ (_to_float, _to_int) を提供。PK 欠損行はスキップしログ警告。
    - fetched_at を UTC ISO8601 で記録して取得時点をトレース可能に。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集基盤を実装（デフォルトに Yahoo Finance のカテゴリ RSS を登録）。
  - 記事の URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリをソート）を実装。
  - セキュリティ対策:
    - defusedxml による XML の安全パース（XML Bomb 等を防止）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - トラッキングパラメータ除去や ID（URL 正規化後の SHA-256 の先頭 32 文字）による冪等性確保。
    - SSRF 対策や不正スキームの拒否などを設計方針に記載（実装方針の反映）。
  - バルク INSERT のチャンク化とトランザクション最適化を想定。
- 研究用ファクター計算 (kabusys.research.factor_research)
  - Momentum / Volatility / Value ファクター計算を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日のカウント不足は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播を制御）。
    - calc_value: target_date 以前の最新 raw_financials と当日の価格を組み合わせて per, roe を算出。
  - 祝日や営業日欠損に対応するためスキャン範囲にバッファを付与（calendar 日での余裕）。
- 研究支援・統計 (kabusys.research.feature_exploration)
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
  - calc_ic: Spearman のランク相関（Information Coefficient）を実装。サンプル数 3 未満では None を返す。
  - rank / factor_summary: 同順位は平均ランクとして扱うランク実装、基本統計量（count/mean/std/min/max/median）算出を実装。
  - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールの生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップして外れ値影響を抑制。
  - features テーブルへの日付単位の置換（DELETE → INSERT のトランザクション）で原子性を確保。冪等設計。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用する方針を明記。
- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し、最終スコア（final_score）を計算して BUY/SELL シグナルを生成。
    - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重みを実装）。
    - sigmoid による Z スコア → [0,1] 変換、欠損コンポーネントは中立 0.5 で補完。
    - ユーザー指定 weights の検証・補完（未知キーや非数値・負値を無視、合計が 1 でない場合は再スケール）。
  - Bear レジーム判定: ai_scores の regime_score 平均が負 → Bear（サンプル数閾値あり）。
    - Bear 相場では BUY シグナルを抑制。
  - SELL（エグジット）判定:
    - 実装済み: ストップロス（終値 / avg_price - 1 < -8%）、final_score が閾値未満 → SELL。
    - 未実装（将来的な実装候補）: トレーリングストップ、保有日数による時間決済（positions テーブルに peak_price / entry_date が必要）。
  - signals テーブルへの日付単位の置換（トランザクション + バルク挿入）で原子性を保証。
- API/設計上の注記
  - 研究・戦略モジュールは発注 API / execution 層に依存しない（検証容易性、分離設計）。
  - ルックアヘッドバイアスを防ぐ設計が全体方針として徹底されている（target_date のみ参照、fetched_at 記録など）。
  - ログ出力が各主要処理に追加されている（info/warning/debug）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- news_collector で defusedxml を使用して XML パースの脆弱性（XML Bomb 等）に対処。
- ニュース/HTTP 処理で受信サイズ制限や URL 正規化を設け、メモリ DoS やトラッキングパラメータによる混乱を低減。
- J-Quants クライアントでのトークン自動リフレッシュやリトライ処理により認証失敗時の不安定動作を軽減。

Removed
- 初回リリースのため該当なし。

Notes / Known limitations
- positions テーブルに peak_price / entry_date 等の情報がないため、トレーリングストップや時間決済ロジックは未実装。
- news_collector の SSRF 完全防御や外部 URL バリデーションの詳細実装（IP ブロックリストやホスト許可リストなど）は方針に記載されているが、実装の適用範囲は確認が必要。
- execution / monitoring 名前空間はエクスポートされているが、実装は含まれていない（プレースホルダ）。
- zscore_normalize 等の関数は kabusys.data.stats 側に依存しているため、その挙動（欠損処理、安定性）に注意。

参考（実装上の主要仕様）
- データベース: DuckDB を利用。raw_prices/raw_financials/market_calendar/features/ai_scores/positions/signals などを前提とした SQL を使用。
- API 安定性: 各保存処理は冪等（ON CONFLICT）・トランザクションで安全化。
- 設計思想: 研究/戦略/データ収集を明確に分離し、発注層との責務分離を実現。

-----------------------------------------------------------------------------
（注）この CHANGELOG は与えられたコードスニペットの実装内容から推測して作成したものです。実際のリリース履歴や日付、追加の変更点がある場合は適宜修正してください。