KEEP A CHANGELOG
=================

このファイルは「Keep a Changelog」仕様に準拠して作成されています。
バージョン履歴は主にソースコード（src/ 以下）の実装内容から推測して記載しています。

0.1.0 - 2026-03-19
------------------

Added
- 初回公開: kabusys パッケージの基本モジュールを追加。
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
- 環境設定/ロード
  - src/kabusys/config.py
    - プロジェクトルートを .git または pyproject.toml で自動検出する _find_project_root を実装。
    - .env/.env.local の自動読み込み機能を追加（OS 環境変数を保護する protected 機構、.env.local は上書きする）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - .env ファイルの高度なパーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
    - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル検証などのプロパティを提供。
    - 必須環境変数未設定時は明示的に ValueError を送出する _require を実装。
- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
    - 固定間隔レートリミッタ（_RateLimiter）で 120 req/min 制限を守る実装。
    - HTTP リトライ（指数バックオフ・最大3回）、408/429/5xx の再試行、429 の Retry-After 読み取りを実装。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して1回リトライするロジックを実装（get_id_token を経由）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による upsert を利用。
    - データ変換ユーティリティ _to_float / _to_int を実装し、堅牢な型変換を提供。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead bias のトレースを可能に。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集モジュールを実装（デフォルトで Yahoo Finance のビジネス RSS を登録）。
    - defusedxml を使った安全な XML パース、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、SSRF・攻撃対策を考慮した URL 正規化を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保する設計。
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去して正規化。クエリをソート、フラグメント除去等に対応。
    - DB へのバルク INSERT をチャンク化して保存計算コストを抑える（_INSERT_CHUNK_SIZE）。
- リサーチ（研究）関連
  - src/kabusys/research/*
    - factor_research.py: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）計算を実装。prices_daily / raw_financials を参照。
    - feature_exploration.py: 将来リターン計算（calc_forward_returns、可変ホライズン対応）、IC（calc_ic: スピアマンのランク相関）、統計サマリー（factor_summary）、ランク関数（rank）を実装。外部ライブラリに依存しない純粋実装。
    - research パッケージの __init__ で公開 API を整備。
- 戦略（Strategy）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境の生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化（zscore_normalize を利用）、±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位の置換）する build_features を実装。
    - lookup 用に target_date 以前の最新の価格を参照する実装で休場日対応。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、複合的な final_score を計算して BUY/SELL シグナルを生成する generate_signals を実装。
    - スコアのコンポーネント: momentum / value / volatility / liquidity / news（デフォルト重みは StrategyModel.md に準拠）。
    - 重みの入力検証・フォールバック・再スケール処理を実装（不正な重みは警告して無視）。
    - Z スコアを sigmoid に変換するユーティリティ、欠損コンポーネントは中立 0.5 で補完するロジックを導入（欠損銘柄の不当な不利化を防止）。
    - Bear レジーム判定（AI レジームスコアの平均が負かつサンプル数閾値以上）により BUY を抑制する機能を実装。
    - エグジット条件（STOP_LOSS -8%、final_score が閾値未満）に基づく SELL シグナル生成を実装。保有銘柄リストを参照し、価格欠損時は判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換をトランザクションで実行（BUY/SELL を同一トランザクションで更新）。
- 実装品質・堅牢化
  - 各種 SQL クエリで日付フィルタや最新レコード抽出（MAX(date) 等）を慎重に使用し、休場日やデータ欠損を考慮。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）と例外処理で原子性を担保。
  - 詳細なログ出力（info/warning/debug）を複数箇所に追加して挙動追跡を容易に。

Changed
- 初版リリースとして、設計方針に沿ったモジュール分割と公開 API（build_features, generate_signals, research 関数群, data clients）を確立。

Fixed
- .env パーサの弱点を改善（引用符とバックスラッシュのエスケープ処理、インラインコメント処理、export プレフィックス対応）。
- ネットワーク/API 呼び出しの失敗に対する再試行ロジックと Token 自動リフレッシュを追加し、安定性を向上。

Security
- news_collector で defusedxml を利用して XML 外部攻撃（XML Bomb 等）への耐性を強化。
- URL 正規化でスキーム検証やトラッキングパラメータ除去、受信サイズ制限を行い、SSRF やメモリ DoS のリスクを低減。
- J-Quants クライアントのトークン管理と自動リフレッシュ実装により認証エラーを安全に処理。

Known issues / TODO
- signal_generator のエグジット条件に関する未実装項目:
  - トレーリングストップ（peak_price の追跡が positions テーブルで未実装）
  - 時間決済（保有 60 営業日超過など） — positions に entry_date 等の追加情報が必要
- AI スコア（ai_scores）が無い場合はニューススコアを中立 0.5 として扱うため、将来的に AI モデル出力の取り込み方法や欠損ハンドリングを改善する余地あり。
- 外部 API（J-Quants）や RSS 取得処理のユニットテスト用モックは現在の実装に依存しておらず、テストの整備が必要。
- DuckDB スキーマの初期化・マイグレーション管理についてはこのリリースでは実装が想定されていない（運用ドキュメントにて対応予定）。

Notes
- 本 CHANGELOG はソースから推測した初期リリースの要約です。実際のリリースノート作成時は運用上の変更点（API 仕様、DB スキーマ、既知の互換性問題、マイグレーション手順等）を併せて記載してください。